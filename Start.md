Guía rápida: Levantar proyecto en Python con venv

Paso 1: Abrir el proyecto

Abre la carpeta del proyecto en VS Code, PyCharm o directamente desde la terminal.

Paso 2: Activar el entorno virtual (venv)

Windows (cmd):
venv\Scripts\activate

Windows (PowerShell):
.\venv\Scripts\Activate.ps1

Linux / MacOS:
source venv/bin/activate

Al activarse correctamente, deberías ver (venv) al inicio de la línea en la terminal.

Paso 3: Instalar dependencias

Si existe un archivo requirements.txt, ejecuta:
pip install -r requirements.txt

Paso 4: Ejecutar el proyecto

Script simple:
python app.py

API con FastAPI o Flask (ejemplo con FastAPI):
uvicorn app:app --reload
(Reemplaza app:app con el módulo y la variable de tu aplicación).

Paso 5: Desactivar el entorno virtual
Cuando termines de trabajar:
deactivate