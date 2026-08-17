# Key Search V 10.0 Ultra - Suite Profesional de SEO & Marketing Digital

**Key Search V 10.0 Ultra** es una plataforma integral de inteligencia de búsqueda, keyword research multi-motor, detección de oportunidades de posicionamiento rápido (SERP Weakness), generación de contenido editorial y creación de anuncios publicitarios de alta conversión.

---

## 🌟 Principales Super-Herramientas

1. **🔍 Suite Multi-Motor Gratuita en Tiempo Real:**
   * Extracción simultánea desde **Google Suggest**, **YouTube Autosuggest**, **Amazon Suggest**, **Bing** y **DuckDuckGo**.
   * Métricas cuantitativas reales vía **Wikimedia Pageviews REST API** (visitas mensuales y promedio diario).
   * Detección de consultas en aumento e interés relativo vía **Google Trends Breakouts**.

2. **🏆 Detector de "Oportunidades de Oro" / SERP Débil:**
   * Inspección en vivo del Top 10 orgánico de Google.
   * Detección de foros (*Reddit, Quora, Forocoches*) y redes sociales (*Pinterest, TikTok*) en las primeras posiciones para identificar victorias rápidas con contenido editorial especializado.

3. **📝 Content Brief & Estructura Editorial H1/H2/H3:**
   * Generación automática de guías completas para redactores y copywriters con objetivo de palabras, estructura H2/H3, términos semánticos obligatorios y checklist On-Page.
   * Copiado en 1 Clic en formato Markdown listo para redactores o LLMs.

4. **🌐 Mapa Radial de Clústeres D3.js (AnswerThePublic Style):**
   * Visualización ramificada interactiva por intención de búsqueda (*¿Qué?, ¿Cómo?, Dónde, Comparativas, Precios*).
   * Controles de zoom y exportación en **PNG** y **SVG** de alta resolución.

5. **⚡ SEO Snippet & Schema FAQPage Studio:**
   * Generador de código estándar **JSON-LD `FAQPage`** para obtener Rich Snippets (acordeones desplegables) en Google.
   * Simulador SERP móvil y desktop con contadores de caracteres (≤ 60 para títulos y ≤ 155 para descripciones).

6. **📢 Copywriter de Ads & Ganchos Virales:**
   * **Google Ads (PPC):** 5 Títulos (≤ 30 car) y 3 Descripciones (≤ 90 car) con simulador de anuncio patrocinado.
   * **Facebook / Instagram Ads:** Gancho *scroll-stopper* + fórmula PAS (*Problema - Agitación - Solución*) + CTA.
   * **TikTok / Reels / Shorts:** 5 ganchos virales de 3 segundos + guion estructurado de 30 segundos.

7. **🎯 Estimador de KGR (Keyword Golden Ratio):**
   * Metodología KGR para detectar micronichos de baja saturación en títulos web para rankear en tiempo récord.

8. **🧠 Soporte para OpenAI / GPT-OSS 120B & Llama 3.3 70B vía Groq SDK:**
   * Motor de IA con parámetros de razonamiento (`reasoning_effort="medium"`).
   * Selector dinámico de modelos en la interfaz web.

---

## 🚀 Despliegue en Render / Cloud

El proyecto cuenta con configuración nativa para **Render** ([`render.yaml`](render.yaml)):
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT`
- **Variables de Entorno (Opcionales):**
  - `GROQ_API_KEY`: Tu API Key de Groq Cloud para IA avanzada.
  - `GROQ_MODEL`: `openai/gpt-oss-120b` (por defecto) o `llama-3.3-70b-versatile`.

---

## Seguridad

Ver [SECURITY.md](SECURITY.md) para politicas de Reporte de Vulnerabilidades.

---

## Cambios

Ver [CHANGELOG.md](CHANGELOG.md) para historial de versiones.

---

## Endpoints de Monitoreo

| Endpoint | Descripcion |
|----------|-------------|
| `GET /ping` | Health check basico (200 OK) |
| `GET /health` | Health check detallado (DB, uptime, version, AI status) |

---

## Licencia

Uso interno / Privado.

---

## 💻 Ejecución Local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Iniciar servidor FastAPI
python fastapi_app.py
```
Abre en tu navegador: [http://localhost:8000](http://localhost:8000)