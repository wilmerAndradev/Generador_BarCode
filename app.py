# 1. Importaciones
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session, jsonify
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm, cm
import os
import zipfile
from datetime import datetime

# 2. Definición de funciones

def generar_barcode(codigo):
    """
    Genera una imagen de código de barras en formato Code128 a partir de una cadena.
    Optimizado para maximizar el ancho del código de barras en etiquetas pequeñas.
    """
    BARCODE_FORMAT = barcode.get_barcode_class('code128')
    
    # Configuración específica para etiquetas de 35x25mm
    options = {
        "write_text": True,
        "module_height": 8.0,
        "module_width": 0.3,
        "quiet_zone": 0.3,
        "font_size": 8,
        "text_distance": 3.0,
        "margin": 0
    }
    
    my_barcode = BARCODE_FORMAT(codigo, writer=ImageWriter())
    buffer = BytesIO()
    my_barcode.write(buffer, options=options)
    buffer.seek(0)
    return buffer

def generar_pdf(codigo, cantidad, output_path):
    """
    Genera un PDF en hoja tamaño CARTA con plantilla precortada de 66 etiquetas.
    """
    # Configuración de página estándar
    page_width, page_height = letter
    
    # Configuración de etiquetas precortadas
    label_width = 35 * mm
    label_height = 25 * mm
    gap_x = 0.7 * mm
    gap_y = 0.7 * mm
    
    # Configuración fija para plantilla precortada
    num_labels_per_row = 6
    num_labels_per_col = 11
    total_labels_per_page = 66
    
    # Márgenes mínimos de impresora
    printer_margin = 6 * mm
    
    # Área disponible para imprimir
    printable_width = page_width - (2 * printer_margin)
    printable_height = page_height - (2 * printer_margin)
    
    # Cálculo de posicionamiento correcto
    total_grid_width = num_labels_per_row * label_width + (num_labels_per_row - 1) * gap_x
    total_grid_height = num_labels_per_col * label_height + (num_labels_per_col - 1) * gap_y
    
    # Centrar la grilla dentro del área imprimible
    start_x = printer_margin + (printable_width - total_grid_width) / 2
    start_y = printer_margin + (printable_height - total_grid_height) / 2 + total_grid_height - label_height
    
    # Ajuste fino de calibración
    calibration_offset_x = 0 * mm
    calibration_offset_y = 0 * mm
    
    # Aplicar los ajustes de calibración
    start_x += calibration_offset_x
    start_y += calibration_offset_y
    
    # Generación del PDF
    c = canvas.Canvas(output_path, pagesize=letter)
    barcode_buffer = generar_barcode(codigo)
    barcode_image = ImageReader(barcode_buffer)
    
    # Obtener las dimensiones reales de la imagen del código de barras
    img_width, img_height = barcode_image.getSize()
    
    # Generar etiquetas
    for i in range(cantidad):
        # Calcular posición en la página actual
        pos_in_page = i % total_labels_per_page
        
        # Distribución regular en grilla
        row = pos_in_page // num_labels_per_row
        col = pos_in_page % num_labels_per_row
        
        # Calcular coordenadas x, y de la etiqueta
        x = start_x + col * (label_width + gap_x)
        y = start_y - row * (label_height + gap_y)
        
        # Configuración del código de barras dentro de la etiqueta
        margin_x = 2
        margin_y = 2
        
        # Espacio utilizable dentro de la etiqueta
        usable_width = label_width - 2 * margin_x
        usable_height = label_height - 2 * margin_y
        
        # Calcular el factor de escala para ajustar el código de barras
        width_ratio = usable_width / img_width
        height_ratio = usable_height / img_height
        
        # Usar el factor que mejor se ajuste sin exceder los límites
        scale_factor = min(width_ratio, height_ratio)
        
        new_width = img_width * scale_factor
        new_height = img_height * scale_factor
        
        # Centrar la imagen del código de barras en la etiqueta
        x_centered = x + margin_x + (usable_width - new_width) / 2
        y_centered = y + margin_y + (usable_height - new_height) / 2
        
        # Dibujar el código de barras en la etiqueta
        c.drawImage(barcode_image, x_centered, y_centered,
                    width=new_width, height=new_height, preserveAspectRatio=True)
        
        # Dibujar bordes de la etiqueta
        c.setLineWidth(0.1)
        c.rect(x, y, label_width, label_height, stroke=1, fill=0)
        
        # Control de páginas
        if (i + 1) % total_labels_per_page == 0 and (i + 1) < cantidad:
            c.showPage()
            start_y = page_height - (page_height - total_grid_height) / 2 - label_height
    
    # Finalizar y guardar el PDF
    c.save()

def crear_zip_todos_los_pdfs(lista_pdfs, zip_filename):
    """
    Crea un archivo ZIP con todos los PDFs generados.
    """
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for pdf_info in lista_pdfs:
            if os.path.exists(pdf_info['archivo']):
                zipf.write(pdf_info['archivo'], os.path.basename(pdf_info['archivo']))

# 3. Definición de las rutas de Flask
app = Flask(__name__)
app.secret_key = "tu_clave_secreta_aqui"

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Paso 1: Elegir cuántos códigos de barras crear
    """
    if request.method == 'POST':
        try:
            num_productos = int(request.form.get('num_productos', 0))
        except ValueError:
            num_productos = 0

        # Validaciones
        if num_productos < 1:
            flash("El número de productos debe ser 1 o superior.")
            return redirect(url_for('index'))
        
        if num_productos > 50:  # Límite razonable
            flash("El número máximo de productos es 50.")
            return redirect(url_for('index'))

        # Guardar en sesión y redirigir al paso 2
        session['num_productos'] = num_productos
        session['productos'] = []
        return redirect(url_for('ingresar_productos'))

    return render_template('index.html')

@app.route('/ingresar-productos', methods=['GET', 'POST'])
def ingresar_productos():
    """
    Paso 2: Ingresar información de cada producto
    """
    if 'num_productos' not in session:
        return redirect(url_for('index'))

    num_productos = session['num_productos']
    productos = session.get('productos', [])

    if request.method == 'POST':
        # Procesar el formulario de productos
        nuevos_productos = []
        
        for i in range(num_productos):
            sku = request.form.get(f'sku_{i}', '').strip()
            codigo = request.form.get(f'codigo_{i}', '').strip()
            try:
                cantidad = int(request.form.get(f'cantidad_{i}', 0))
            except ValueError:
                cantidad = 0

            # Validaciones
            if not sku:
                flash(f"El SKU del producto {i+1} es obligatorio.")
                return render_template('ingresar_productos.html', 
                                     num_productos=num_productos, 
                                     productos_existentes=productos)
            
            if not codigo:
                flash(f"El código de barras del producto {i+1} es obligatorio.")
                return render_template('ingresar_productos.html', 
                                     num_productos=num_productos, 
                                     productos_existentes=productos)
            
            if cantidad < 1:
                flash(f"La cantidad del producto {i+1} debe ser 1 o superior.")
                return render_template('ingresar_productos.html', 
                                     num_productos=num_productos, 
                                     productos_existentes=productos)

            nuevos_productos.append({
                'sku': sku,
                'codigo': codigo,
                'cantidad': cantidad
            })

        # Verificar SKUs únicos
        skus = [p['sku'] for p in nuevos_productos]
        if len(skus) != len(set(skus)):
            flash("Los SKUs deben ser únicos.")
            return render_template('ingresar_productos.html', 
                                 num_productos=num_productos, 
                                 productos_existentes=productos)

        # Guardar productos en sesión y continuar
        session['productos'] = nuevos_productos
        return redirect(url_for('generar_etiquetas'))

    return render_template('ingresar_productos.html', 
                         num_productos=num_productos, 
                         productos_existentes=productos)

@app.route('/generar-etiquetas')
def generar_etiquetas():
    """
    Paso 3: Generar todos los PDFs y mostrar panel de descarga
    """
    if 'productos' not in session or not session['productos']:
        return redirect(url_for('index'))

    productos = session['productos']
    pdfs_generados = []

    # Crear directorio para PDFs si no existe
    if not os.path.exists('pdfs_generados'):
        os.makedirs('pdfs_generados')

    # Generar cada PDF
    for producto in productos:
        # Formato del nombre: {sku}_{codigo_barras}_etiquetas_silk_perfumes.pdf
        nombre_archivo = f"{producto['sku']}_{producto['codigo']}_etiquetas_silk_perfumes.pdf"
        ruta_archivo = os.path.join('pdfs_generados', nombre_archivo)
        
        try:
            # Generar el PDF
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
            pdfs_generados.append({
                'sku': producto['sku'],
                'codigo': producto['codigo'],
                'cantidad': producto['cantidad'],
                'nombre_archivo': nombre_archivo,
                'archivo': '',
                'generado': False,
                'error': str(e)
            })

    # Guardar lista de PDFs en sesión
    session['pdfs_generados'] = pdfs_generados

    return render_template('panel_descarga.html', pdfs=pdfs_generados)

@app.route('/descargar/<filename>')
def descargar_pdf(filename):
    """
    Descargar un PDF individual
    """
    ruta_archivo = os.path.join('pdfs_generados', filename)
    
    if os.path.exists(ruta_archivo):
        return send_file(ruta_archivo, as_attachment=True)
    else:
        flash("El archivo no existe.")
        return redirect(url_for('generar_etiquetas'))

@app.route('/descargar-todos')
def descargar_todos():
    """
    Descargar todos los PDFs en un archivo ZIP
    """
    if 'pdfs_generados' not in session:
        return redirect(url_for('index'))

    pdfs_generados = session['pdfs_generados']
    pdfs_exitosos = [pdf for pdf in pdfs_generados if pdf['generado']]

    if not pdfs_exitosos:
        flash("No hay archivos para descargar.")
        return redirect(url_for('generar_etiquetas'))

    # Crear nombre único para el ZIP
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"etiquetas_silk_perfumes_{timestamp}.zip"
    zip_path = os.path.join('pdfs_generados', zip_filename)

    # Crear el ZIP
    crear_zip_todos_los_pdfs(pdfs_exitosos, zip_path)

    return send_file(zip_path, as_attachment=True)

@app.route('/reiniciar')
def reiniciar():
    """
    Limpiar sesión y empezar de nuevo
    """
    session.clear()
    return redirect(url_for('index'))

# 4. Ruta de limpieza (opcional, para desarrollo)
@app.route('/limpiar-archivos')
def limpiar_archivos():
    """
    Eliminar archivos generados (solo para desarrollo)
    """
    try:
        if os.path.exists('pdfs_generados'):
            for archivo in os.listdir('pdfs_generados'):
                os.remove(os.path.join('pdfs_generados', archivo))
        flash("Archivos limpiados correctamente.")
    except Exception as e:
        flash(f"Error al limpiar archivos: {str(e)}")
    
    return redirect(url_for('index'))

# 5. Bloque de ejecución
if __name__ == '__main__':
    app.run(debug=True)
