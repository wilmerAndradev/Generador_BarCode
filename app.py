# 1. Importaciones
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import black, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import zipfile
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 2. Configuración de constantes con sistema de compensación
class LabelConfig:
    """Configuración centralizada para etiquetas con compensación de márgenes"""
    
    # Dimensiones del papel
    PAGE_WIDTH = 21 * cm
    PAGE_HEIGHT = 27.9 * cm
    
    # Área de impresión real de tu impresora
    PRINTER_PRINTABLE_WIDTH = 20.5 * cm
    PRINTER_PRINTABLE_HEIGHT = 26.9 * cm
    
    # Márgenes físicos de la impresora (calculados automáticamente)
    PRINTER_MARGIN_LEFT = (PAGE_WIDTH - PRINTER_PRINTABLE_WIDTH) / 2
    PRINTER_MARGIN_RIGHT = (PAGE_WIDTH - PRINTER_PRINTABLE_WIDTH) / 2
    PRINTER_MARGIN_TOP = (PAGE_HEIGHT - PRINTER_PRINTABLE_HEIGHT) / 2
    PRINTER_MARGIN_BOTTOM = (PAGE_HEIGHT - PRINTER_PRINTABLE_HEIGHT) / 2
    
    # Dimensiones de las etiquetas
    LABEL_WIDTH = 35 * mm
    LABEL_HEIGHT = 25 * mm
    
    # Distribución de etiquetas
    LABELS_PER_ROW = 6
    LABELS_PER_COL = 11
    TOTAL_LABELS_PER_PAGE = LABELS_PER_ROW * LABELS_PER_COL
    
    # VARIABLES DE CALIBRACIÓN FINA
    FINE_TUNE_X = 0 * mm
    FINE_TUNE_Y = 0 * mm
    
    # Ajuste de espaciado entre etiquetas
    SPACING_ADJUSTMENT_X = 0 * mm
    SPACING_ADJUSTMENT_Y = 0 * mm
    
    # LÍMITES DE CARACTERES PARA VALIDACIÓN
    MAX_NOMBRE_PRODUCTO = 60
    MAX_VALOR = 10
    MAX_SKU = 15
    MAX_OTRO = 40
    
    BARCODE_CONFIG = {
        "write_text": True,
        "module_height": 8.5,
        "module_width": 0.30,
        "quiet_zone": 0.5,
        "font_size": 8,
        "text_distance": 4.0,
        "margin": 0
    }
    
    @classmethod
    def get_layout_info(cls):
        """Retorna información detallada del layout para debugging"""
        info = {
            "Página": f"{cls.PAGE_WIDTH/cm:.2f} × {cls.PAGE_HEIGHT/cm:.2f} cm",
            "Área imprimible": f"{cls.PRINTER_PRINTABLE_WIDTH/cm:.2f} × {cls.PRINTER_PRINTABLE_HEIGHT/cm:.2f} cm",
            "Márgenes impresora (L,R,T,B)": f"{cls.PRINTER_MARGIN_LEFT/mm:.1f}, {cls.PRINTER_MARGIN_RIGHT/mm:.1f}, {cls.PRINTER_MARGIN_TOP/mm:.1f}, {cls.PRINTER_MARGIN_BOTTOM/mm:.1f} mm",
            "Etiqueta": f"{cls.LABEL_WIDTH/mm:.1f} × {cls.LABEL_HEIGHT/mm:.1f} mm",
            "Grid": f"{cls.LABELS_PER_ROW} × {cls.LABELS_PER_COL}",
            "Ajuste fino (X,Y)": f"{cls.FINE_TUNE_X/mm:.1f}, {cls.FINE_TUNE_Y/mm:.1f} mm"
        }
        return info

def generar_barcode(codigo: str) -> BytesIO:
    """Genera código de barras optimizado"""
    try:
        barcode_class = barcode.get_barcode_class('code128')
        barcode_instance = barcode_class(codigo, writer=ImageWriter())
        
        buffer = BytesIO()
        barcode_instance.write(buffer, options=LabelConfig.BARCODE_CONFIG)
        buffer.seek(0)
        
        return buffer
    except Exception as e:
        raise ValueError(f"Error generando código de barras para '{codigo}': {str(e)}")

def calcular_layout() -> Tuple[float, float, float, float]:
    """
    Calcula las posiciones de layout con compensación de márgenes
    """
    total_labels_width = LabelConfig.LABELS_PER_ROW * LabelConfig.LABEL_WIDTH
    total_labels_height = LabelConfig.LABELS_PER_COL * LabelConfig.LABEL_HEIGHT
    
    available_width = LabelConfig.PRINTER_PRINTABLE_WIDTH
    available_height = LabelConfig.PRINTER_PRINTABLE_HEIGHT
    
    extra_margin_x = (available_width - total_labels_width) / 2
    extra_margin_y = (available_height - total_labels_height) / 2
    
    start_x = LabelConfig.PRINTER_MARGIN_LEFT + extra_margin_x + LabelConfig.FINE_TUNE_X
    start_y = LabelConfig.PAGE_HEIGHT - LabelConfig.PRINTER_MARGIN_TOP - extra_margin_y - LabelConfig.LABEL_HEIGHT + LabelConfig.FINE_TUNE_Y
    
    print(f"\n=== DEBUG LAYOUT ===")
    print(f"Área imprimible: {available_width/cm:.2f} × {available_height/cm:.2f} cm")
    print(f"Espacio etiquetas: {total_labels_width/cm:.2f} × {total_labels_height/cm:.2f} cm")
    print(f"Margen extra: X={extra_margin_x/mm:.1f}mm, Y={extra_margin_y/mm:.1f}mm")
    print(f"Inicio: X={start_x/cm:.2f}cm, Y={start_y/cm:.2f}cm")
    print(f"===================\n")
    
    return LabelConfig.PRINTER_MARGIN_LEFT, LabelConfig.PRINTER_MARGIN_TOP, start_x, start_y

def calcular_posicion_etiqueta(index: int, start_x: float, start_y: float) -> Tuple[float, float, int, int]:
    """Calcula posición exacta de una etiqueta"""
    fila = index // LabelConfig.LABELS_PER_ROW
    columna = index % LabelConfig.LABELS_PER_ROW
    
    x = start_x + columna * (LabelConfig.LABEL_WIDTH + LabelConfig.SPACING_ADJUSTMENT_X)
    y = start_y - fila * (LabelConfig.LABEL_HEIGHT + LabelConfig.SPACING_ADJUSTMENT_Y)
    
    return round(x, 1), round(y, 1), fila, columna

def dibujar_marco_completo(c: canvas.Canvas, start_x: float, start_y: float) -> None:
    """Dibuja el marco completo del área de etiquetas"""
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    
    ancho_total = LabelConfig.LABELS_PER_ROW * (LabelConfig.LABEL_WIDTH + LabelConfig.SPACING_ADJUSTMENT_X)
    alto_total = LabelConfig.LABELS_PER_COL * (LabelConfig.LABEL_HEIGHT + LabelConfig.SPACING_ADJUSTMENT_Y)
    y_superior = start_y + LabelConfig.LABEL_HEIGHT
    
    c.rect(start_x, start_y - alto_total + LabelConfig.LABEL_HEIGHT, 
           ancho_total, alto_total, stroke=1, fill=0)
    
    for col in range(1, LabelConfig.LABELS_PER_ROW):
        x = start_x + col * (LabelConfig.LABEL_WIDTH + LabelConfig.SPACING_ADJUSTMENT_X)
        c.line(x, y_superior, x, y_superior - alto_total)
    
    for row in range(1, LabelConfig.LABELS_PER_COL):
        y = y_superior - row * (LabelConfig.LABEL_HEIGHT + LabelConfig.SPACING_ADJUSTMENT_Y)
        c.line(start_x, y, start_x + ancho_total, y)

def dibujar_guias_calibracion(c: canvas.Canvas, start_x: float, start_y: float):
    """Dibuja guías de calibración en las esquinas (opcional, para pruebas)"""
    c.setStrokeColor(HexColor("#FF0000"))
    c.setLineWidth(0.3)
    
    marca = 5 * mm
    
    c.line(start_x, start_y + LabelConfig.LABEL_HEIGHT, 
           start_x + marca, start_y + LabelConfig.LABEL_HEIGHT)
    c.line(start_x, start_y + LabelConfig.LABEL_HEIGHT, 
           start_x, start_y + LabelConfig.LABEL_HEIGHT - marca)
    
    end_x = start_x + LabelConfig.LABELS_PER_ROW * LabelConfig.LABEL_WIDTH
    c.line(end_x - marca, start_y + LabelConfig.LABEL_HEIGHT, 
           end_x, start_y + LabelConfig.LABEL_HEIGHT)
    c.line(end_x, start_y + LabelConfig.LABEL_HEIGHT, 
           end_x, start_y + LabelConfig.LABEL_HEIGHT - marca)

def generar_pdf_codigo_barras(codigo: str, cantidad: int, output_path: str) -> None:
    """Genera PDF con etiquetas de código de barras"""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    
    margin_x, margin_y, start_x, start_y = calcular_layout()
    
    try:
        c = canvas.Canvas(output_path, pagesize=(LabelConfig.PAGE_WIDTH, LabelConfig.PAGE_HEIGHT))
        
        barcode_buffer = generar_barcode(codigo)
        barcode_image = ImageReader(barcode_buffer)
        img_width, img_height = barcode_image.getSize()
        
        for i in range(cantidad):
            pos_in_page = i % LabelConfig.TOTAL_LABELS_PER_PAGE
            
            if pos_in_page == 0:
                if i > 0:
                    c.showPage()
                dibujar_marco_completo(c, start_x, start_y)
            
            x, y, fila, columna = calcular_posicion_etiqueta(pos_in_page, start_x, start_y)
            colocar_codigo_barras(c, barcode_image, img_width, img_height, x, y)
        
        c.save()
        print(f"✓ PDF generado: {output_path}")
        
    except Exception as e:
        raise RuntimeError(f"Error generando PDF: {str(e)}")

def colocar_codigo_barras(c: canvas.Canvas, barcode_image: ImageReader, 
                         img_width: int, img_height: int, x: float, y: float) -> None:
    """Coloca el código de barras centrado en la etiqueta"""
    padding = 1.5 * mm
    available_width = LabelConfig.LABEL_WIDTH - 2 * padding
    available_height = LabelConfig.LABEL_HEIGHT - 2 * padding
    
    scale_x = available_width / img_width
    scale_y = available_height / img_height
    scale = min(scale_x, scale_y) * 0.95
    
    final_width = img_width * scale
    final_height = img_height * scale
    
    barcode_x = x + padding + (available_width - final_width) / 2
    barcode_y = y + padding + (available_height - final_height) / 2
    
    c.drawImage(barcode_image, barcode_x, barcode_y,
               width=final_width, height=final_height, 
               preserveAspectRatio=True)

def dividir_texto_por_ancho(c: canvas.Canvas, texto: str, fuente: str, tamaño: int, ancho_maximo: float) -> list:
    """Divide un texto en múltiples líneas según el ancho máximo disponible"""
    palabras = texto.split()
    lineas = []
    linea_actual = ""
    
    for palabra in palabras:
        if linea_actual:
            linea_prueba = linea_actual + " " + palabra
        else:
            linea_prueba = palabra
            
        ancho_prueba = c.stringWidth(linea_prueba, fuente, tamaño)
        
        if ancho_prueba <= ancho_maximo:
            linea_actual = linea_prueba
        else:
            if linea_actual:
                lineas.append(linea_actual)
            linea_actual = palabra
    
    if linea_actual:
        lineas.append(linea_actual)
    
    return lineas if lineas else [texto]

def generar_pdf_personalizado(datos: Dict, cantidad: int, output_path: str) -> None:
    """Genera PDF con etiquetas personalizadas"""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    
    margin_x, margin_y, start_x, start_y = calcular_layout()
    
    try:
        c = canvas.Canvas(output_path, pagesize=(LabelConfig.PAGE_WIDTH, LabelConfig.PAGE_HEIGHT))
        
        for i in range(cantidad):
            pos_in_page = i % LabelConfig.TOTAL_LABELS_PER_PAGE
            
            if pos_in_page == 0:
                if i > 0:
                    c.showPage()
                dibujar_marco_completo(c, start_x, start_y)
            
            x, y, fila, columna = calcular_posicion_etiqueta(pos_in_page, start_x, start_y)
            dibujar_etiqueta_personalizada(c, datos, x, y)
        
        c.save()
        print(f"✓ PDF generado: {output_path}")
        
    except Exception as e:
        raise RuntimeError(f"Error generando PDF: {str(e)}")

def dibujar_etiqueta_personalizada(c: canvas.Canvas, datos: Dict, x: float, y: float) -> None:
    """Dibuja una etiqueta personalizada con los datos centrados y saltos de línea automáticos"""
    padding = 1.5 * mm
    ancho_util = LabelConfig.LABEL_WIDTH - 2 * padding
    alto_util = LabelConfig.LABEL_HEIGHT - 2 * padding
    
    center_x = x + LabelConfig.LABEL_WIDTH / 2
    
    c.setFillColor(black)
    line_height = 2.8 * mm
    
    lineas = []
    
    # Nombre del producto CON SALTOS DE LÍNEA AUTOMÁTICOS
    if datos.get('nombre_producto'):
        nombre = datos['nombre_producto'].strip().upper()
        c.setFont('Helvetica-Bold', 7)
        lineas_nombre = dividir_texto_por_ancho(c, nombre, 'Helvetica-Bold', 7, ancho_util * 0.9)
        for linea in lineas_nombre:
            lineas.append(('Helvetica-Bold', 7, linea))
    
    # SKU
    if datos.get('sku'):
        sku = f"SKU: {datos['sku']}"
        lineas.append(('Helvetica', 6, sku))
    
    # Valor
    if datos.get('valor'):
        valor = f"${datos['valor']}"
        lineas.append(('Helvetica-Bold', 7, valor))
    
    # Otro CON SALTOS DE LÍNEA AUTOMÁTICOS
    if datos.get('otro'):
        otro = datos['otro'].strip()
        c.setFont('Helvetica', 6)
        lineas_otro = dividir_texto_por_ancho(c, otro, 'Helvetica', 6, ancho_util * 0.9)
        for linea in lineas_otro:
            lineas.append(('Helvetica', 6, linea))
    
    if not lineas:
        return
    
    altura_total = len(lineas) * line_height
    
    max_altura = alto_util * 0.8
    if altura_total > max_altura:
        line_height = max_altura / len(lineas)
    
    text_y = y + (alto_util + altura_total) / 2 - line_height / 2
    
    for fuente, tamaño, texto in lineas:
        c.setFont(fuente, tamaño)
        text_width = c.stringWidth(texto, fuente, tamaño)
        text_x = center_x - text_width / 2
        c.drawString(text_x, text_y, texto)
        text_y -= line_height

def crear_zip_pdfs(lista_pdfs: List[Dict], zip_filename: str) -> None:
    """Crea archivo ZIP con todos los PDFs generados"""
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pdf_info in lista_pdfs:
                if pdf_info.get('generado') and os.path.exists(pdf_info['archivo']):
                    zipf.write(pdf_info['archivo'], os.path.basename(pdf_info['archivo']))
    except Exception as e:
        raise RuntimeError(f"Error creando ZIP: {str(e)}")

def validar_producto_codigo_barras(sku: str, codigo: str, cantidad: str, numero: int) -> Dict:
    """Valida datos de un producto con código de barras"""
    sku = sku.strip()
    codigo = codigo.strip()
    
    if not sku:
        return {'error': f"El SKU del producto {numero} es obligatorio."}
    
    if len(sku) > LabelConfig.MAX_SKU:
        return {'error': f"El SKU del producto {numero} no puede exceder {LabelConfig.MAX_SKU} caracteres."}
    
    if not codigo:
        return {'error': f"El código de barras del producto {numero} es obligatorio."}
    
    try:
        cantidad_int = int(cantidad)
        if cantidad_int < 1:
            return {'error': f"La cantidad del producto {numero} debe ser 1 o superior."}
    except (ValueError, TypeError):
        return {'error': f"La cantidad del producto {numero} debe ser un número válido."}
    
    return {
        'sku': sku,
        'codigo': codigo,
        'cantidad': cantidad_int,
        'tipo': 'codigo_barras'
    }

def validar_producto_personalizado(cantidad: str, numero: int, **datos) -> Dict:
    """Valida datos de un producto personalizado con límites de caracteres"""
    try:
        cantidad_int = int(cantidad)
        if cantidad_int < 1:
            return {'error': f"La cantidad del producto {numero} debe ser 1 o superior."}
    except (ValueError, TypeError):
        return {'error': f"La cantidad del producto {numero} debe ser un número válido."}
    
    nombre_producto = datos.get('nombre_producto', '').strip()
    valor = datos.get('valor', '').strip()
    sku = datos.get('sku', '').strip()
    otro = datos.get('otro', '').strip()
    
    # Validar que al menos un campo tenga información
    if not any([nombre_producto, valor, sku, otro]):
        return {'error': f"El producto {numero} debe tener al menos un campo con información."}
    
    # Validar límites de caracteres
    if nombre_producto and len(nombre_producto) > LabelConfig.MAX_NOMBRE_PRODUCTO:
        return {'error': f"El nombre del producto {numero} no puede exceder {LabelConfig.MAX_NOMBRE_PRODUCTO} caracteres (actual: {len(nombre_producto)})."}
    
    if valor and len(valor) > LabelConfig.MAX_VALOR:
        return {'error': f"El valor del producto {numero} no puede exceder {LabelConfig.MAX_VALOR} caracteres."}
    
    if sku and len(sku) > LabelConfig.MAX_SKU:
        return {'error': f"El SKU del producto {numero} no puede exceder {LabelConfig.MAX_SKU} caracteres."}
    
    if otro and len(otro) > LabelConfig.MAX_OTRO:
        return {'error': f"El campo 'Otro' del producto {numero} no puede exceder {LabelConfig.MAX_OTRO} caracteres (actual: {len(otro)})."}
    
    return {
        'cantidad': cantidad_int,
        'nombre_producto': nombre_producto,
        'valor': valor,
        'sku': sku,
        'otro': otro,
        'tipo': 'personalizado'
    }

# 3. Aplicación Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_por_defecto_cambiar_en_produccion')

@app.route('/', methods=['GET', 'POST'])
def index():
    """Paso 1: Definir cantidad de productos"""
    if request.method == 'POST':
        try:
            num_productos = int(request.form.get('num_productos', 0))
        except (ValueError, TypeError):
            flash("Debe ingresar un número válido.")
            return redirect(url_for('index'))

        if not 1 <= num_productos <= 50:
            flash("El número de productos debe estar entre 1 y 50.")
            return redirect(url_for('index'))

        session.clear()
        session['num_productos'] = num_productos
        return redirect(url_for('elegir_tipo_etiqueta'))

    return render_template('index.html')

@app.route('/elegir-tipo', methods=['GET', 'POST'])
def elegir_tipo_etiqueta():
    """Paso 1.5: Elegir tipo de etiqueta"""
    if 'num_productos' not in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        tipo = request.form.get('tipo_etiqueta')
        
        if tipo not in ['codigo_barras', 'personalizado']:
            flash("Debe seleccionar un tipo de etiqueta válido.")
            return redirect(url_for('elegir_tipo_etiqueta'))
        
        session['tipo_etiqueta'] = tipo
        return redirect(url_for('ingresar_productos'))
    
    num_productos = session['num_productos']
    return render_template('elegir_tipo.html', num_productos=num_productos)

@app.route('/ingresar-productos', methods=['GET', 'POST'])
def ingresar_productos():
    """Paso 2: Ingresar datos de productos según tipo"""
    if 'num_productos' not in session or 'tipo_etiqueta' not in session:
        return redirect(url_for('index'))

    num_productos = session['num_productos']
    tipo_etiqueta = session['tipo_etiqueta']

    if request.method == 'POST':
        productos = []
        errores = []
        
        if tipo_etiqueta == 'codigo_barras':
            for i in range(num_productos):
                sku = request.form.get(f'sku_{i}', '')
                codigo = request.form.get(f'codigo_{i}', '')
                cantidad = request.form.get(f'cantidad_{i}', '')
                
                resultado = validar_producto_codigo_barras(sku, codigo, cantidad, i + 1)
                
                if 'error' in resultado:
                    errores.append(resultado['error'])
                else:
                    productos.append(resultado)
            
            if not errores:
                skus = [p['sku'] for p in productos]
                if len(skus) != len(set(skus)):
                    errores.append("Los SKUs deben ser únicos.")
        
        else:
            for i in range(num_productos):
                cantidad = request.form.get(f'cantidad_{i}', '')
                nombre_producto = request.form.get(f'nombre_producto_{i}', '')
                valor = request.form.get(f'valor_{i}', '')
                sku = request.form.get(f'sku_{i}', '')
                otro = request.form.get(f'otro_{i}', '')
                
                resultado = validar_producto_personalizado(
                    cantidad, i + 1,
                    nombre_producto=nombre_producto,
                    valor=valor,
                    sku=sku,
                    otro=otro
                )
                
                if 'error' in resultado:
                    errores.append(resultado['error'])
                else:
                    productos.append(resultado)
        
        if errores:
            for error in errores:
                flash(error)
            return render_template('ingresar_productos.html', 
                                 num_productos=num_productos,
                                 tipo_etiqueta=tipo_etiqueta,
                                 max_nombre=LabelConfig.MAX_NOMBRE_PRODUCTO,
                                 max_valor=LabelConfig.MAX_VALOR,
                                 max_sku=LabelConfig.MAX_SKU,
                                 max_otro=LabelConfig.MAX_OTRO)
        
        session['productos'] = productos
        return redirect(url_for('generar_etiquetas'))

    return render_template('ingresar_productos.html', 
                         num_productos=num_productos,
                         tipo_etiqueta=tipo_etiqueta,
                         max_nombre=LabelConfig.MAX_NOMBRE_PRODUCTO,
                         max_valor=LabelConfig.MAX_VALOR,
                         max_sku=LabelConfig.MAX_SKU,
                         max_otro=LabelConfig.MAX_OTRO)

def generar_pdf_personalizado_masivo(productos: List[Dict], output_path: str) -> None:
    """Genera un ÚNICO PDF con todas las etiquetas personalizadas de todos los productos"""
    if not productos:
        raise ValueError("No hay productos para generar")
    
    # Calcular cantidad total de etiquetas
    total_etiquetas = sum(p['cantidad'] for p in productos)
    
    margin_x, margin_y, start_x, start_y = calcular_layout()
    
    try:
        c = canvas.Canvas(output_path, pagesize=(LabelConfig.PAGE_WIDTH, LabelConfig.PAGE_HEIGHT))
        
        # Crear lista de todas las etiquetas con sus datos
        todas_etiquetas = []
        for producto in productos:
            for _ in range(producto['cantidad']):
                todas_etiquetas.append(producto)
        
        # Generar todas las etiquetas en un solo PDF
        for i, datos_etiqueta in enumerate(todas_etiquetas):
            pos_in_page = i % LabelConfig.TOTAL_LABELS_PER_PAGE
            
            if pos_in_page == 0:
                if i > 0:
                    c.showPage()
                dibujar_marco_completo(c, start_x, start_y)
            
            x, y, fila, columna = calcular_posicion_etiqueta(pos_in_page, start_x, start_y)
            dibujar_etiqueta_personalizada(c, datos_etiqueta, x, y)
        
        c.save()
        print(f"✓ PDF masivo generado: {output_path} ({total_etiquetas} etiquetas)")
        
    except Exception as e:
        raise RuntimeError(f"Error generando PDF masivo: {str(e)}")

@app.route('/generar-etiquetas')
def generar_etiquetas():
    """Paso 3: Generar PDFs"""
    if 'productos' not in session or 'tipo_etiqueta' not in session:
        return redirect(url_for('index'))

    productos = session['productos']
    tipo_etiqueta = session['tipo_etiqueta']
    
    print("\n" + "="*50)
    print("INFORMACIÓN DE LAYOUT")
    print("="*50)
    for key, value in LabelConfig.get_layout_info().items():
        print(f"{key}: {value}")
    print("="*50 + "\n")
    
    os.makedirs('pdfs_generados', exist_ok=True)
    
    pdfs_generados = []
    
    # CÓDIGO DE BARRAS: UN PDF POR PRODUCTO (como estaba)
    if tipo_etiqueta == 'codigo_barras':
        for idx, producto in enumerate(productos):
            nombre_archivo = f"{producto['sku']}_{producto['codigo']}_etiquetas.pdf"
            titulo_producto = producto['sku']
            ruta_archivo = os.path.join('pdfs_generados', nombre_archivo)
            
            try:
                generar_pdf_codigo_barras(producto['codigo'], producto['cantidad'], ruta_archivo)
                
                pdfs_generados.append({
                    'titulo': titulo_producto,
                    'cantidad': producto['cantidad'],
                    'nombre_archivo': nombre_archivo,
                    'archivo': ruta_archivo,
                    'generado': True,
                    'tipo': tipo_etiqueta
                })
                
            except Exception as e:
                print(f"✗ Error generando PDF para {titulo_producto}: {str(e)}")
                pdfs_generados.append({
                    'titulo': titulo_producto,
                    'cantidad': producto['cantidad'],
                    'nombre_archivo': nombre_archivo,
                    'archivo': '',
                    'generado': False,
                    'tipo': tipo_etiqueta,
                    'error': str(e)
                })
    
    # ETIQUETAS PERSONALIZADAS: UN SOLO PDF CON TODAS LAS ETIQUETAS
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"etiquetas_personalizadas_{timestamp}.pdf"
        ruta_archivo = os.path.join('pdfs_generados', nombre_archivo)
        
        # Calcular total de etiquetas
        total_etiquetas = sum(p['cantidad'] for p in productos)
        
        try:
            generar_pdf_personalizado_masivo(productos, ruta_archivo)
            
            pdfs_generados.append({
                'titulo': 'Etiquetas Personalizadas',
                'cantidad': total_etiquetas,
                'nombre_archivo': nombre_archivo,
                'archivo': ruta_archivo,
                'generado': True,
                'tipo': tipo_etiqueta,
                'productos_count': len(productos)
            })
            
        except Exception as e:
            print(f"✗ Error generando PDF personalizado masivo: {str(e)}")
            pdfs_generados.append({
                'titulo': 'Etiquetas Personalizadas',
                'cantidad': total_etiquetas,
                'nombre_archivo': nombre_archivo,
                'archivo': '',
                'generado': False,
                'tipo': tipo_etiqueta,
                'error': str(e)
            })

    session['pdfs_generados'] = pdfs_generados
    return render_template('panel_descarga.html', pdfs=pdfs_generados, tipo_etiqueta=tipo_etiqueta)

@app.route('/descargar/<filename>')
def descargar_pdf(filename: str):
    """Descargar PDF individual"""
    if '..' in filename or '/' in filename:
        flash("Nombre de archivo inválido.")
        return redirect(url_for('index'))
    
    ruta_archivo = os.path.join('pdfs_generados', filename)
    
    if os.path.exists(ruta_archivo):
        return send_file(ruta_archivo, as_attachment=True)
    else:
        flash("El archivo no existe.")
        return redirect(url_for('generar_etiquetas'))

@app.route('/descargar-todos')
def descargar_todos():
    """Descargar todos los PDFs en ZIP"""
    if 'pdfs_generados' not in session:
        return redirect(url_for('index'))

    pdfs_exitosos = [pdf for pdf in session['pdfs_generados'] if pdf.get('generado')]
    
    if not pdfs_exitosos:
        flash("No hay archivos para descargar.")
        return redirect(url_for('generar_etiquetas'))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"etiquetas_silk_perfumes_{timestamp}.zip"
    zip_path = os.path.join('pdfs_generados', zip_filename)

    try:
        crear_zip_pdfs(pdfs_exitosos, zip_path)
        return send_file(zip_path, as_attachment=True)
    except Exception as e:
        flash(f"Error creando ZIP: {str(e)}")
        return redirect(url_for('generar_etiquetas'))

@app.route('/reiniciar')
def reiniciar():
    """Reiniciar sesión"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/limpiar-archivos')
def limpiar_archivos():
    """Limpiar archivos generados"""
    try:
        if os.path.exists('pdfs_generados'):
            archivos_eliminados = 0
            for archivo in os.listdir('pdfs_generados'):
                os.remove(os.path.join('pdfs_generados', archivo))
                archivos_eliminados += 1
            flash(f"Se eliminaron {archivos_eliminados} archivos.")
        else:
            flash("No hay archivos para eliminar.")
    except Exception as e:
        flash(f"Error limpiando archivos: {str(e)}")
    
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(error):
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(error):
    flash("Ocurrió un error interno. Por favor, intenta nuevamente.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)