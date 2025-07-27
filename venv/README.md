# Sistema de Generación de Etiquetas Silk Perfumes

## 📋 Descripción
Sistema web para generar etiquetas con códigos de barras en formato PDF optimizado para impresión en hojas precortadas de 66 etiquetas (35x25mm).

## 🚀 Versión 1.2.1 - Mejoras de Interfaz
- ✨ Interfaz mejorada y más intuitiva
- 🔧 Correcciones de bugs menores
- 📱 Mejor responsividad en dispositivos móviles
- 🎨 Diseño más moderno y profesional

## 📦 Instalación

### Requisitos previos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/tu-repositorio.git
cd tu-repositorio
```

2. **Crear entorno virtual**
```bash
python -m venv venv
```

3. **Activar entorno virtual**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

## 🖥️ Uso

1. **Ejecutar la aplicación**
```bash
python app.py
```

2. **Abrir navegador**
Ir a: `http://127.0.0.1:5000`

3. **Proceso de generación**
   - Paso 1: Indicar cantidad de productos
   - Paso 2: Ingresar datos (SKU, código de barras, cantidad)
   - Paso 3: Descargar PDFs generados

## 📄 Características

- **Formato optimizado**: Etiquetas de 35x25mm en hoja carta
- **Plantilla precortada**: 66 etiquetas por hoja (6 columnas x 11 filas)
- **Códigos de barras**: Formato Code128
- **Descarga múltiple**: Archivos individuales o ZIP con todos
- **Interfaz intuitiva**: Proceso paso a paso
- **Validación**: Verificación de entradas de usuario

## 🔧 Configuración de Impresión

### Configuración recomendada:
- **Papel**: Carta (8.5" x 11")
- **Orientación**: Vertical
- **Márgenes**: Mínimos (6mm)
- **Calidad**: Alta resolución
- **Escala**: 100% (sin ajustar al papel)

## 📁 Estructura del Proyecto

```
proyecto/
├── app.py                 # Aplicación principal
├── requirements.txt       # Dependencias
├── static/               # Archivos estáticos
│   ├── styles.css        # Estilos CSS
│   └── logo.png          # Logo de la empresa
├── templates/            # Plantillas HTML
│   ├── index.html        # Página principal
│   ├── ingresar_productos.html
│   └── panel_descarga.html
└── pdfs_generados/       # PDFs generados (se crea automáticamente)
```

## 🔄 Historial de Versiones

### v1.2.1 (Actual)
- 🎨 Mejoras en la interfaz de usuario
- 📱 Mejor responsividad
- 🔧 Correcciones menores

### v1.2.0
- 🆕 Sistema de descarga mejorado
- 📦 Generación de archivos ZIP
- 🔄 Proceso de reinicio mejorado

### v1.0.0
- 🎉 Versión inicial
- ✅ Generación básica de etiquetas
- 📄 Formato PDF optimizado

## 🤝 Contribuir

1. Fork del proyecto
2. Crear rama para feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit de cambios (`git commit -am 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Crear Pull Request

## 📞 Soporte

Para soporte técnico o reportar bugs, crear un issue en el repositorio.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---
**Desarrollado para Silk Perfumes** 🌸