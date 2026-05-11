# 🔍 KeySearch SEO v6.0

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-FF4B4B.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**KeySearch SEO** es una potente herramienta de investigación de palabras clave que extrae señales reales de demanda directamente de los motores de búsqueda de Google. Combina autocompletado, preguntas frecuentes (PAA), Google Trends y Google Ads API para proporcionar una visión 360° de cualquier nicho.

## 🚀 Características Principales

- **Autocompletado Pro**: Expansión profunda mediante modificadores de preguntas y barrido alfabético (A-Z).
- **People Also Ask (PAA)**: Extracción recursiva de preguntas reales de la SERP.
- **Validación con Google Trends**: Filtra por interés real en lugar de solo volumen estático.
- **Enriquecimiento con Google Ads**: Conexión nativa con la API de Google Ads para obtener volúmenes exactos.
- **IA Groq Integration**: Filtrado inteligente de resultados para eliminar ruido y temas irrelevantes.
- **Interfaz Dual**: Úsala desde la terminal (CLI) o mediante una aplicación web moderna (Streamlit).

## 🛠️ Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/corvusnigrumm/KeySearch-SEO.git
   cd KeySearch-SEO
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Configura tus credenciales (opcional):
   - Crea un archivo `.env` o configura variables de entorno para `GROQ_API_KEY`.
   - Coloca tu `google-ads.yaml` en la raíz para habilitar métricas de Ads.

## 💻 Uso

### Aplicación Web (Recomendado)
```bash
streamlit run streamlit_app.py
```

### Interfaz de Línea de Comandos
```bash
python main.py --keyword "tu keyword" --country "co" --profile "normal"
```

## 📊 Salida
La herramienta genera reportes detallados en:
- **Excel (.xlsx)**: Con formato profesional y priorización por scores.
- **JSON**: Para integración con otras herramientas.

---
Desarrollado con ❤️ para SEOs y Creadores de Contenido.