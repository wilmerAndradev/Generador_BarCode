# 1. Importaciones
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from reportlab.lib.pagesizes import letter   # Volvemos a usar tamaño carta estándar
from reportlab.pdfgen import canvas          # Para generar el PDF
from reportlab.lib.utils import ImageReader    # Para leer la imagen del código de barras desde el buffer
from reportlab.lib.units import mm, cm        # Para trabajar con milímetros y centímetros directamente

# 2. Definición de funciones

def generar_barcode(codigo):
    """
    Genera una imagen de código de barras en formato Code128 a partir de una cadena.
    Optimizado para maximizar el ancho del código de barras en etiquetas pequeñas.
    """
    BARCODE_FORMAT = barcode.get_barcode_class('code128')
    
    # Configuración específica para etiquetas de 35x25mm
    options = {
        "write_text": True,          # Mostrar el número debajo del código
        "module_height": 8.0,        # Altura de las barras (reducida para etiquetas pequeñas)
        "module_width": 0.3,         # Ancho de cada barra (más delgado para mejor ajuste)
        "quiet_zone": 0.3,           # Zona silenciosa mínima (reducida)
        "font_size": 8,              # Tamaño de la fuente más pequeño
        "text_distance": 3.0,        # Distancia entre barras y texto (reducida)
        "margin": 0                  # Sin margen adicional para maximizar el área útil
    }
    
    my_barcode = BARCODE_FORMAT(codigo, writer=ImageWriter())
    buffer = BytesIO()
    my_barcode.write(buffer, options=options)
    buffer.seek(0)
    return buffer

def generar_pdf(codigo, cantidad, output_path):
    """
    Genera un PDF en hoja tamaño CARTA con plantilla precortada de 66 etiquetas.
    
    Especificaciones de la plantilla precortada:
    - Hoja: Tamaño carta estándar (8.5" x 11" = 215.9 x 279.4 mm)
    - Etiquetas: 35 x 25 mm cada una
    - Separación: 1mm entre etiquetas (ya definida en el precortado)
    - Total: Exactamente 66 etiquetas por hoja (distribución calculada)
    
    La hoja viene precortada, por lo que debemos calcular la distribución exacta
    para que las etiquetas coincidan perfectamente con los espacios precortados.
    
    Parámetros:
      codigo (str): El código para generar el código de barras.
      cantidad (int): Número total de etiquetas a generar.
      output_path (str): Ruta y nombre del archivo PDF generado.
    """
    
    # === CONFIGURACIÓN DE PÁGINA ESTÁNDAR ===
    # Usar tamaño carta estándar (la hoja física es carta)
    page_width, page_height = letter  # 612 x 792 puntos (8.5" x 11")
    
    # === CONFIGURACIÓN DE ETIQUETAS PRECORTADAS ===
    # Dimensiones exactas de cada etiqueta precortada
    label_width = 35 * mm      # 35 milímetros de ancho
    label_height = 25 * mm     # 25 milímetros de alto
    
    # Separación fija entre etiquetas (ya definida en el precortado)
    gap_x = 0.7 * mm             # 1mm de separación horizontal
    gap_y = 0.7 * mm             # 1mm de separación vertical
    
    # === CONFIGURACIÓN FIJA PARA PLANTILLA PRECORTADA ===
    # La plantilla precortada tiene EXACTAMENTE 6 columnas x 11 filas = 66 etiquetas
    num_labels_per_row = 6     # 6 columnas fijas (según precortado)
    num_labels_per_col = 11    # 11 filas fijas (según precortado)
    total_labels_per_page = 66 # Total fijo de 66 etiquetas por hoja
    
    # Márgenes mínimos de impresora (área no imprimible)
    printer_margin = 6 * mm    # 6mm de margen mínimo en todos los lados
    
    # Área disponible para imprimir
    printable_width = page_width - (2 * printer_margin)
    printable_height = page_height - (2 * printer_margin)
    
    # === CÁLCULO DE POSICIONAMIENTO CORRECTO ===
    # Calcular el área total ocupada por la grilla de etiquetas
    total_grid_width = num_labels_per_row * label_width + (num_labels_per_row - 1) * gap_x
    total_grid_height = num_labels_per_col * label_height + (num_labels_per_col - 1) * gap_y
    
    # Centrar la grilla dentro del área imprimible (no de toda la página)
    start_x = printer_margin + (printable_width - total_grid_width) / 2
    start_y = printer_margin + (printable_height - total_grid_height) / 2 + total_grid_height - label_height
    
    print(f"Grilla: {total_grid_width/mm:.1f}mm x {total_grid_height/mm:.1f}mm")
    print(f"Posición inicial: x={start_x/mm:.1f}mm, y={start_y/mm:.1f}mm")
    
    # === AJUSTE FINO DE CALIBRACIÓN ===
    # Corrección basada en pruebas de impresión
    calibration_offset_x = 0 * mm   # Eje X ya está correcto
    calibration_offset_y = 0 * mm   # Eje Y
    
    # Aplicar los ajustes de calibración
    start_x += calibration_offset_x
    start_y += calibration_offset_y
    
    # === GENERACIÓN DEL PDF ===
    c = canvas.Canvas(output_path, pagesize=letter)  # Usar tamaño carta estándar
    barcode_buffer = generar_barcode(codigo)
    barcode_image = ImageReader(barcode_buffer)
    
    # Obtener las dimensiones reales de la imagen del código de barras
    img_width, img_height = barcode_image.getSize()
    
    # Generar etiquetas
    for i in range(cantidad):
        # Calcular posición en la página actual
        pos_in_page = i % total_labels_per_page
        
    # Generar etiquetas con distribución regular (sin posiciones especiales)
    for i in range(cantidad):
        # Calcular posición en la página actual
        pos_in_page = i % total_labels_per_page
        
        # Distribución regular en grilla
        row = pos_in_page // num_labels_per_row
        col = pos_in_page % num_labels_per_row
        
        # Calcular coordenadas x, y de la etiqueta
        x = start_x + col * (label_width + gap_x)
        y = start_y - row * (label_height + gap_y)
        
        # === CONFIGURACIÓN DEL CÓDIGO DE BARRAS DENTRO DE LA ETIQUETA ===
        # Márgenes internos de la etiqueta (muy pequeños para maximizar espacio)
        margin_x = 2  # margen horizontal interno mínimo
        margin_y = 2  # margen vertical interno mínimo
        
        # Espacio utilizable dentro de la etiqueta
        usable_width = label_width - 2 * margin_x
        usable_height = label_height - 2 * margin_y
        
        # Calcular el factor de escala para ajustar el código de barras
        # Priorizar el ancho para maximizar legibilidad
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
        
        # === DIBUJAR BORDES DE LA ETIQUETA ===
        # Estos bordes son ESENCIALES para verificar alineación con el precortado
        c.setLineWidth(0.1)
        c.rect(x, y, label_width, label_height, stroke=1, fill=0)
        
        # === CONTROL DE PÁGINAS ===
        # Si se completó una página y aún hay más etiquetas, crear nueva página
        if (i + 1) % total_labels_per_page == 0 and (i + 1) < cantidad:
            c.showPage()
            # Resetear posición inicial para la nueva página
            start_y = page_height - (page_height - total_grid_height) / 2 - label_height
    
    # Finalizar y guardar el PDF
    c.save()

# 3. Definición de las rutas de Flask
app = Flask(__name__)
# Define la clave secreta para poder usar flash
app.secret_key = "tu_clave_secreta_aqui"

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Ruta principal que maneja tanto la visualización del formulario (GET)
    como el procesamiento de la generación de etiquetas (POST).
    
    Formulario requiere:
    - codigo: Texto para el código de barras
    - cantidad: Número de etiquetas a generar (mínimo 1)
    """
    if request.method == 'POST':
        # Capturamos el código y la cantidad enviados en el formulario
        codigo = request.form.get('codigo')
        try:
            cantidad = int(request.form.get('cantidad', 0))
        except ValueError:
            cantidad = 0

        # === VALIDACIONES DEL SERVIDOR ===
        if not codigo:
            flash("El campo código de barra es obligatorio.")
            return redirect(url_for('index'))
        if cantidad < 1:
            flash("La cantidad debe ser 1 o superior.")
            return redirect(url_for('index'))

        # Definimos el nombre del archivo PDF de salida
        output_file = f"etiqueta_{codigo}.pdf"

        # Llamamos a la función para generar el PDF con las etiquetas
        generar_pdf(codigo, cantidad, output_file)

        # Se envía el PDF para descarga, como un archivo adjunto
        return send_file(output_file, as_attachment=True)

    # Si es método GET, mostrar el formulario
    return render_template('index.html')

# 4. Bloque de prueba y ejecución
if __name__ == '__main__':
    """
    Ejecutar la aplicación Flask en modo debug para desarrollo.
    En producción, usar un servidor WSGI como Gunicorn.
    """
    app.run(debug=True)