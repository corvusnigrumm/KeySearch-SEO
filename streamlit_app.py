import streamlit as st

st.set_page_config(page_title="KeySearch V 6.0", page_icon="🔍", layout="wide")

st.title("🔍 KeySearch V 6.0")
st.write("Si puedes ver esto, Streamlit Cloud funciona correctamente.")
st.success("✅ Conexion exitosa")

# Test basico de imports
errores = []

try:
    import requests
    st.write("✅ requests OK")
except Exception as e:
    errores.append(f"requests: {e}")

try:
    from bs4 import BeautifulSoup
    st.write("✅ beautifulsoup4 OK")
except Exception as e:
    errores.append(f"bs4: {e}")

try:
    import openpyxl
    st.write("✅ openpyxl OK")
except Exception as e:
    errores.append(f"openpyxl: {e}")

try:
    import pandas
    st.write("✅ pandas OK")
except Exception as e:
    errores.append(f"pandas: {e}")

try:
    import lxml
    st.write("✅ lxml OK")
except Exception as e:
    errores.append(f"lxml: {e}")

try:
    from config import APP_VERSION, COUNTRY_CATALOG
    st.write(f"✅ config OK (Version: {APP_VERSION})")
except Exception as e:
    errores.append(f"config: {e}")

try:
    from scraper.utils import limpiar_texto
    st.write("✅ scraper.utils OK")
except Exception as e:
    errores.append(f"scraper.utils: {e}")

try:
    from scraper.http_cache import make_key
    st.write("✅ scraper.http_cache OK")
except Exception as e:
    errores.append(f"scraper.http_cache: {e}")

try:
    from scraper.categorizer import auto_categorizar
    st.write("✅ scraper.categorizer OK")
except Exception as e:
    errores.append(f"scraper.categorizer: {e}")

try:
    from scraper.autocomplete import get_autocomplete_suggestions
    st.write("✅ scraper.autocomplete OK")
except Exception as e:
    errores.append(f"scraper.autocomplete: {e}")

try:
    from scraper.google_serp import scrape_google
    st.write("✅ scraper.google_serp OK")
except Exception as e:
    errores.append(f"scraper.google_serp: {e}")

try:
    from scraper.volume_estimator import estimar_volumenes
    st.write("✅ scraper.volume_estimator OK")
except Exception as e:
    errores.append(f"scraper.volume_estimator: {e}")

try:
    from scraper.ai_filter import filtrar_con_ia
    st.write("✅ scraper.ai_filter OK")
except Exception as e:
    errores.append(f"scraper.ai_filter: {e}")

try:
    from scraper.google_ads_metrics import enrich_with_google_ads_metrics
    st.write("✅ scraper.google_ads_metrics OK")
except Exception as e:
    errores.append(f"scraper.google_ads_metrics: {e}")

try:
    from exporters.excel_export import exportar_excel
    st.write("✅ exporters.excel_export OK")
except Exception as e:
    errores.append(f"exporters.excel_export: {e}")

try:
    from exporters.json_export import exportar_json
    st.write("✅ exporters.json_export OK")
except Exception as e:
    errores.append(f"exporters.json_export: {e}")

if errores:
    st.error("Errores encontrados:")
    for err in errores:
        st.code(err)
else:
    st.balloons()
    st.success("🎉 TODOS los modulos importan correctamente. Listo para la interfaz completa.")
