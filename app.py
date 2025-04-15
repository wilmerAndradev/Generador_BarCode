# 1. Importaciones
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from reportlab.lib.pagesizes import letter   # Para el tamaño de la página (carta)
from reportlab.pdfgen import canvas          # Para generar el PDF
from reportlab.lib.utils import ImageReader    # Para leer la imagen del código de barras desde el buffer

# 2. Definición de funciones

def generar_barcode(codigo):
    """
    Genera una imagen de código de barras en formato Code128 a partir de una cadena.
    Optimizado para maximizar el ancho del código de barras.
    """
    BARCODE_FORMAT = barcode.get_barcode_class('code128')
    
    # Configuración específica para la biblioteca python-barcode
    options = {
        "write_text": True,          # Mostrar el número debajo del código
        "module_height": 12.0,       # Altura de las barras
        "module_width": 0.45,        # Ancho de cada barra
        "quiet_zone": 0.5,           # Zona silenciosa mínima
        "font_size": 15,             # Tamaño de la fuente para el texto
        "text_distance": 7.0,        # Distancia entre barras y texto
        "margin": 0                  # Sin margen adicional para maximizar el área útil
    }
    
    my_barcode = BARCODE_FORMAT(codigo, writer=ImageWriter())
    buffer = BytesIO()
    my_barcode.write(buffer, options=options)
    buffer.seek(0)
    return buffer

def generar_pdf(codigo, cantidad, output_path):
    """
    Genera un PDF en formato carta, distribuyendo etiquetas con el código de barras (formato Code128)
    en etiquetas de 3.5 cm x 1.5 cm (aprox. 103 x 45 pts).
    
    Parámetros:
      codigo (str): El código para generar el código de barras.
      cantidad (int): Número total de etiquetas a generar.
      output_path (str): Ruta y nombre del archivo PDF generado.
    """
    # Tamaño de la página (carta): 612 x 792 pts aproximadamente.
    page_width, page_height = letter

    # Dimensiones de cada etiqueta en puntos (3.5 cm ≈ 103 pts, 1.5 cm ≈ 45 pts)
    label_width = 103
    label_height = 45

    # Márgenes externos para centrar la cuadrícula en la página.
    outer_margin_x = 20
    outer_margin_y = 20

    # Espacios entre etiquetas
    gap_x = 8
    gap_y = 8

    # Calcular el área disponible
    available_width = page_width - 2 * outer_margin_x
    available_height = page_height - 2 * outer_margin_y

    # Número de etiquetas por fila/columna
    num_labels_per_row = int((available_width + gap_x) // (label_width + gap_x))
    num_labels_per_col = int((available_height + gap_y) // (label_height + gap_y))

    grid_width = num_labels_per_row * label_width + (num_labels_per_row - 1) * gap_x
    grid_height = num_labels_per_col * label_height + (num_labels_per_col - 1) * gap_y

    start_x = (page_width - grid_width) / 2
    start_y = page_height - (page_height - grid_height) / 2

    total_labels_per_page = num_labels_per_row * num_labels_per_col

    c = canvas.Canvas(output_path, pagesize=letter)
    barcode_buffer = generar_barcode(codigo)
    barcode_image = ImageReader(barcode_buffer)

    # Obtener las dimensiones reales de la imagen del código de barras
    img_width, img_height = barcode_image.getSize()
    
    for i in range(cantidad):
        pos_in_page = i % total_labels_per_page
        row = pos_in_page // num_labels_per_row
        col = pos_in_page % num_labels_per_row

        x = start_x + col * (label_width + gap_x)
        y = start_y - (row + 1) * label_height - row * gap_y

        # Márgenes dentro de la etiqueta
        margin_x = 1  # margen horizontal interno
        margin_y = 1  # margen vertical interno
        
        # Espacio utilizable dentro de la etiqueta
        usable_width = label_width - 2 * margin_x
        usable_height = label_height - 2 * margin_y
        
        # Calcular el factor de escala para maximizar el ancho (sin exceder el área utilizable)
        width_ratio = usable_width / img_width
        height_ratio = usable_height / img_height
        
        scale_factor = width_ratio
        new_height = img_height * scale_factor
        if new_height > usable_height:
            scale_factor = height_ratio
        
        new_width = img_width * scale_factor
        new_height = img_height * scale_factor
        
        # Centrar la imagen en la etiqueta
        x_centered = x + margin_x + (usable_width - new_width) / 2
        y_centered = y + margin_y + (usable_height - new_height) / 2
        
        c.drawImage(barcode_image, x_centered, y_centered,
                    width=new_width, height=new_height, preserveAspectRatio=True)

        c.setLineWidth(0.10)
        c.rect(x, y, label_width, label_height, stroke=1, fill=0)

        if (i + 1) % total_labels_per_page == 0 and (i + 1) < cantidad:
            c.showPage()
            start_y = page_height - (page_height - grid_height) / 2

    c.save()

# 3. Definición de las rutas de Flask
app = Flask(__name__)
# Define la clave secreta para poder usar flash
app.secret_key = "tu_clave_secreta_aqui"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Capturamos el código y la cantidad enviados en el formulario
        codigo = request.form.get('codigo')
        try:
            cantidad = int(request.form.get('cantidad', 0))
        except ValueError:
            cantidad = 0

        # Validaciones del servidor
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

    return render_template('index.html')

# 4. Bloque de prueba y ejecución
if __name__ == '__main__':
    app.run(debug=True)
