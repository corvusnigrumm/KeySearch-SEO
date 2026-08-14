"""
Test para la integración de OpenAI / GPT-OSS 120B con Groq SDK.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GROQ_MODEL, GROQ_AVAILABLE_MODELS
from scraper.ai_filter import _post_groq_json, _limpiar_respuesta_json


def test_groq_gpt_oss_model_config():
    print("--> Testeando Configuración del Modelo GPT-OSS 120B...")
    print(f"  - Modelo por defecto en config: {GROQ_MODEL}")
    assert "gpt-oss-120b" in GROQ_MODEL or "llama" in GROQ_MODEL, "Modelo no válido"

    model_ids = [m["id"] for m in GROQ_AVAILABLE_MODELS]
    print(f"  - Modelos disponibles en catálogo: {model_ids}")
    assert "openai/gpt-oss-120b" in model_ids, "openai/gpt-oss-120b debe estar disponible"

    print("\n--> Testeando Limpieza de Tokens de Razonamiento (<think> y ```json)...")
    sample_reasoning_output = "<think>Analizando la mejor estructura de respuesta...</think>\n```json\n{\"resultado\": \"ok\", \"modelo\": \"gpt-oss-120b\"}\n```"
    cleaned = _limpiar_respuesta_json(sample_reasoning_output)
    print(f"  - Salida limpia: {cleaned}")
    assert "<think>" not in cleaned, "No debe contener etiquetas <think>"
    assert "```json" not in cleaned, "No debe contener bloques ```json"
    assert "gpt-oss-120b" in cleaned, "Debe preservar el contenido del JSON"

    print("\n>>> PRUEBA DE GPT-OSS 120B Y GROQ SDK EXITOSA <<<")


if __name__ == "__main__":
    test_groq_gpt_oss_model_config()
