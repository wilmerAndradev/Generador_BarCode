# 1. Importaciones
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import black
import os
import zipfile
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 2. Configuración de constantes (principio DRY)
class LabelConfig:
    """Configuración centralizada para etiquetas"""
    # Medidas de hoja y etiquetas
    PAGE_WIDTH = 21.7 * cm
    PAGE_HEIGHT = 28 * cm
    PRINTABLE_WIDTH = 21.1 * cm
    PRINTABLE_HEIGHT = 28 * cm
    
    # Dimensiones de etiquetas
    LABEL_WIDTH = 35 * mm
    LABEL_HEIGHT = 25 * mm
    
    # Layout de grilla
    LABELS_PER_ROW = int(PRINTABLE_WIDTH // LABEL_WIDTH)  # 6
    LABELS_PER_COL = int(PRINTABLE_HEIGHT // LABEL_HEIGHT)  # 11
    TOTAL_LABELS_PER_PAGE = LABELS_PER_ROW * LABELS_PER_COL  # 66
    
    # Ajustes de calibración (modificables según pruebas)
    CALIBRATION_X = 0 * mm  # Ajuste horizontal
    CALIBRATION_Y = 0 * mm  # Ajuste vertical
    
    # Configuración de código de barras
    BARCODE_CONFIG = {
        "write_text": True,
        "module_height": 8.0,
        "module_width": 0.3,
        "quiet_zone": 0.3,
        "font_size": 8,
        "text_distance": 3.0,
        "margin": 0
    }

def generar_barcode(codigo: str) -> BytesIO:
    """
    Genera código de barras optimizado para etiquetas de 35x25mm
    
    Args:
        codigo: String del código de barras
        
    Returns:
        BytesIO: Buffer con imagen del código de barras
    """
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
    Calcula las posiciones de layout de forma matemáticamente precisa
    
    Returns:
        Tuple: (margin_x, margin_y, start_x, start_y)
    """
    # Margen para centrar área de etiquetas en área imprimible
    margin_x = (LabelConfig.PAGE_WIDTH - LabelConfig.PRINTABLE_WIDTH) / 2
    margin_y = (LabelConfig.PAGE_HEIGHT - LabelConfig.PRINTABLE_HEIGHT) / 2
    
    # Calcular espacio usado y sobrante
    used_width = LabelConfig.LABELS_PER_ROW * LabelConfig.LABEL_WIDTH
    used_height = LabelConfig.LABELS_PER_COL * LabelConfig.LABEL_HEIGHT
    
    extra_margin_x = (LabelConfig.PRINTABLE_WIDTH - used_width) / 2
    extra_margin_y = (LabelConfig.PRINTABLE_HEIGHT - used_height) / 2
    
    # Posición inicial con calibración
    start_x = margin_x + extra_margin_x + LabelConfig.CALIBRATION_X
    start_y = LabelConfig.PAGE_HEIGHT - margin_y - extra_margin_y - LabelConfig.LABEL_HEIGHT + LabelConfig.CALIBRATION_Y
    
    return margin_x, margin_y, start_x, start_y

def calcular_posicion_etiqueta(index: int, start_x: float, start_y: float) -> Tuple[float, float, int, int]:
    """
    Calcula posición exacta de una etiqueta sin acumulación de errores
    
    Args:
        index: Índice de la etiqueta en la página
        start_x, start_y: Posiciones de inicio
        
    Returns:
        Tuple: (x, y, fila, columna)
    """
    fila = index // LabelConfig.LABELS_PER_ROW
    columna = index % LabelConfig.LABELS_PER_ROW
    
    # Cálculo directo desde origen (evita acumulación de errores)
    x = start_x + columna * LabelConfig.LABEL_WIDTH
    y = start_y - fila * LabelConfig.LABEL_HEIGHT
    
    return round(x, 1), round(y, 1), fila, columna

def generar_pdf(codigo: str, cantidad: int, output_path: str) -> None:
    """
    Genera PDF con etiquetas de código de barras
    
    Args:
        codigo: Código de barras a generar
        cantidad: Número de etiquetas
        output_path: Ruta del archivo de salida
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    
    # Configuración inicial
    margin_x, margin_y, start_x, start_y = calcular_layout()
    
    # Log de configuración (útil para debugging)
    print(f"Generando PDF: {os.path.basename(output_path)}")
    print(f"  - Código: {codigo}")
    print(f"  - Cantidad: {cantidad}")
    print(f"  - Layout: {LabelConfig.LABELS_PER_ROW}x{LabelConfig.LABELS_PER_COL} = {LabelConfig.TOTAL_LABELS_PER_PAGE}/página")
    print(f"  - Posición inicial: ({start_x/mm:.1f}, {start_y/mm:.1f}) mm")
    
    try:
        # Crear PDF
        c = canvas.Canvas(output_path, pagesize=(LabelConfig.PAGE_WIDTH, LabelConfig.PAGE_HEIGHT))
        
        # Generar código de barras una sola vez (eficiencia)
        barcode_buffer = generar_barcode(codigo)
        barcode_image = ImageReader(barcode_buffer)
        img_width, img_height = barcode_image.getSize()
        
        # Generar etiquetas
        for i in range(cantidad):
            pos_in_page = i % LabelConfig.TOTAL_LABELS_PER_PAGE
            
            # Nueva página si es necesario
            if pos_in_page == 0 and i > 0:
                c.showPage()
            
            # Calcular posición exacta
            x, y, fila, columna = calcular_posicion_etiqueta(pos_in_page, start_x, start_y)
            
            # Colocar código de barras centrado en etiqueta
            colocar_codigo_barras(c, barcode_image, img_width, img_height, x, y)
            
            # Dibujar borde de etiqueta (para verificación)
            dibujar_borde_etiqueta(c, x, y)
        
        # Guardar PDF
        c.save()
        print(f"  ✓ PDF generado exitosamente")
        
    except Exception as e:
        raise RuntimeError(f"Error generando PDF: {str(e)}")

def colocar_codigo_barras(c: canvas.Canvas, barcode_image: ImageReader, 
                         img_width: int, img_height: int, x: float, y: float) -> None:
    """
    Coloca el código de barras centrado en la etiqueta
    
    Args:
        c: Canvas de ReportLab
        barcode_image: Imagen del código de barras
        img_width, img_height: Dimensiones de la imagen
        x, y: Posición de la etiqueta
    """
    # Margen interno para que no toque los bordes
    padding = 1 * mm
    available_width = LabelConfig.LABEL_WIDTH - 2 * padding
    available_height = LabelConfig.LABEL_HEIGHT - 2 * padding
    
    # Calcular escala manteniendo proporción
    scale_x = available_width / img_width
    scale_y = available_height / img_height
    scale = min(scale_x, scale_y)
    
    # Dimensiones finales
    final_width = img_width * scale
    final_height = img_height * scale
    
    # Centrar en la etiqueta
    barcode_x = x + padding + (available_width - final_width) / 2
    barcode_y = y + padding + (available_height - final_height) / 2
    
    # Dibujar código de barras
    c.drawImage(barcode_image, barcode_x, barcode_y,
               width=final_width, height=final_height, 
               preserveAspectRatio=True)

def dibujar_borde_etiqueta(c: canvas.Canvas, x: float, y: float) -> None:
    """
    Dibuja borde de la etiqueta para verificación visual
    
    Args:
        c: Canvas de ReportLab
        x, y: Posición de la etiqueta
    """
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.rect(x, y, LabelConfig.LABEL_WIDTH, LabelConfig.LABEL_HEIGHT, stroke=1, fill=0)

def crear_zip_pdfs(lista_pdfs: List[Dict], zip_filename: str) -> None:
    """
    Crea archivo ZIP con todos los PDFs generados
    
    Args:
        lista_pdfs: Lista de diccionarios con información de PDFs
        zip_filename: Nombre del archivo ZIP
    """
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pdf_info in lista_pdfs:
                if pdf_info.get('generado') and os.path.exists(pdf_info['archivo']):
                    zipf.write(pdf_info['archivo'], os.path.basename(pdf_info['archivo']))
        print(f"ZIP creado: {zip_filename}")
    except Exception as e:
        raise RuntimeError(f"Error creando ZIP: {str(e)}")

def validar_producto(sku: str, codigo: str, cantidad: str, numero: int) -> Dict:
    """
    Valida datos de un producto
    
    Args:
        sku, codigo, cantidad: Datos del producto
        numero: Número del producto para mensajes de error
        
    Returns:
        Dict: Producto validado o error
    """
    # Limpiar datos
    sku = sku.strip()
    codigo = codigo.strip()
    
    # Validaciones
    if not sku:
        return {'error': f"El SKU del producto {numero} es obligatorio."}
    
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
        'cantidad': cantidad_int
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

        session.clear()  # Limpiar sesión anterior
        session['num_productos'] = num_productos
        return redirect(url_for('ingresar_productos'))

    return render_template('index.html')

@app.route('/ingresar-productos', methods=['GET', 'POST'])
def ingresar_productos():
    """Paso 2: Ingresar datos de productos"""
    if 'num_productos' not in session:
        return redirect(url_for('index'))

    num_productos = session['num_productos']

    if request.method == 'POST':
        productos = []
        errores = []
        
        # Validar cada producto
        for i in range(num_productos):
            sku = request.form.get(f'sku_{i}', '')
            codigo = request.form.get(f'codigo_{i}', '')
            cantidad = request.form.get(f'cantidad_{i}', '')
            
            resultado = validar_producto(sku, codigo, cantidad, i + 1)
            
            if 'error' in resultado:
                errores.append(resultado['error'])
            else:
                productos.append(resultado)
        
        # Verificar SKUs únicos
        if not errores:
            skus = [p['sku'] for p in productos]
            if len(skus) != len(set(skus)):
                errores.append("Los SKUs deben ser únicos.")
        
        # Si hay errores, mostrarlos
        if errores:
            for error in errores:
                flash(error)
            return render_template('ingresar_productos.html', 
                                 num_productos=num_productos)
        
        # Guardar productos y continuar
        session['productos'] = productos
        return redirect(url_for('generar_etiquetas'))

    return render_template('ingresar_productos.html', num_productos=num_productos)

@app.route('/generar-etiquetas')
def generar_etiquetas():
    """Paso 3: Generar PDFs"""
    if 'productos' not in session:
        return redirect(url_for('index'))

    productos = session['productos']
    
    # Crear directorio si no existe
    os.makedirs('pdfs_generados', exist_ok=True)
    
    pdfs_generados = []
    
    for producto in productos:
        # Nombre de archivo limpio y descriptivo
        nombre_archivo = f"{producto['sku']}_{producto['codigo']}_etiquetas.pdf"
        ruta_archivo = os.path.join('pdfs_generados', nombre_archivo)
        
        try:
            generar_pdf(producto['codigo'], producto['cantidad'], ruta_archivo)
            
            pdfs_generados.append({
                'sku': producto['sku'],
                'codigo': producto['codigo'],
                'cantidad': producto['cantidad'],
                'nombre_archivo': nombre_archivo,
                'archivo': ruta_archivo,
                'generado': True
            })
            
        except Exception as e:
            print(f"Error generando PDF para {producto['sku']}: {str(e)}")
            pdfs_generados.append({
                'sku': producto['sku'],
                'codigo': producto['codigo'],
                'cantidad': producto['cantidad'],
                'nombre_archivo': nombre_archivo,
                'archivo': '',
                'generado': False,
                'error': str(e)
            })

    session['pdfs_generados'] = pdfs_generados
    return render_template('panel_descarga.html', pdfs=pdfs_generados)

@app.route('/descargar/<filename>')
def descargar_pdf(filename: str):
    """Descargar PDF individual"""
    # Validación de seguridad básica
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

    # Crear ZIP con timestamp
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
    """Limpiar archivos generados (desarrollo)"""
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

# 4. Manejo de errores
@app.errorhandler(404)
def not_found(error):
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(error):
    flash("Ocurrió un error interno. Por favor, intenta nuevamente.")
    return redirect(url_for('index'))

# 5. Punto de entrada
if __name__ == '__main__':
    # Configuración para desarrollo
    app.run(debug=True, host='127.0.0.1', port=5000)