# KeySearch V 6.0 - Engine & UI

Esta es la suite completa de KeySearch V 6.0, que incluye dos versiones de la interfaz web para adaptarse a tus necesidades de diseño y despliegue.

## 🚀 Opciones de Interfaz

### 1. Versión Streamlit (Recomendada para Despliegue Rápido)
Es la versión que se ejecuta actualmente en Streamlit Cloud.
- **Fidelidad:** 90% (Imitación del diseño Stitch con CSS inyectado).
- **Ventajas:** Despliegue en 1 click, reactividad automática en Python.
- **Cómo ejecutar localmente:**
  ```bash
  streamlit run main.py
  ```

### 2. Versión FastAPI (Fidelidad 100%)
Esta versión utiliza los archivos HTML/CSS originales de Stitch sin ninguna modificación.
- **Fidelidad:** 100% (Uso directo de las plantillas de Stitch).
- **Ventajas:** Diseño píxel-perfect, control total sobre el frontend, mejor rendimiento.
- **Cómo ejecutar localmente:**
  ```bash
  python fastapi_app.py
  ```
  Luego abre [http://localhost:8000](http://localhost:8000) en tu navegador.

## ⚙️ Requisitos
Instala las dependencias necesarias:
```bash
pip install -r requirements.txt
```

## 📂 Estructura del Proyecto
- `main.py`: Entrada para Streamlit.
- `fastapi_app.py`: Entrada para FastAPI.
- `templates/`: Plantillas HTML puras para FastAPI.
- `scraper/`: Motor de búsqueda y extracción (compartido).
- `config.py`: Configuración global.