"""
Tests para scraper/ai_client.py: clientes IA y limpieza de respuestas.
"""
import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.ai_client import limpiar_respuesta_json, post_groq_json


class TestLimpiarRespuestaJSON:
    def test_json_limpio_sin_marcado(self):
        raw = '{"resultado": "ok"}'
        assert limpiar_respuesta_json(raw) == '{"resultado": "ok"}'

    def test_elimina_think_tags(self):
        raw = '<think>Analizando...</think>\n{"resultado": "ok"}'
        result = limpiar_respuesta_json(raw)
        assert "<think>" not in result
        assert '"resultado": "ok"' in result

    def test_elimina_think_multiline(self):
        raw = '<think>\nLinea 1\nLinea 2\n</think>\n{"key": "value"}'
        result = limpiar_respuesta_json(raw)
        assert "<think>" not in result
        assert '"key": "value"' in result

    def test_elimina_json_markdown_block(self):
        raw = '```json\n{"key": "value"}\n```'
        result = limpiar_respuesta_json(raw)
        assert "```" not in result
        assert '"key": "value"' in result

    def test_elimina_triple_backtick_sin_json(self):
        raw = '```\n{"key": "value"}\n```'
        result = limpiar_respuesta_json(raw)
        assert "```" not in result
        assert '"key": "value"' in result

    def test_texto_vacio(self):
        assert limpiar_respuesta_json("") == ""

    def test_none(self):
        assert limpiar_respuesta_json(None) == ""

    def test_solo_think_tags(self):
        raw = '<think>razonamiento</think>'
        result = limpiar_respuesta_json(raw)
        assert result == ""

    def test_think_tags_y_json_markdown(self):
        raw = '<think>pensando</think>\n```json\n{"a": 1}\n```'
        result = limpiar_respuesta_json(raw)
        assert "<think>" not in result
        assert "```" not in result
        assert '"a": 1' in result


class TestPostGroqJson:
    @patch("scraper.ai_client._groq_client", None)
    @patch("scraper.ai_client.GROQ_API_KEY", "")
    def test_sin_api_key_devuelve_none(self):
        assert post_groq_json("test prompt") is None

    @patch("scraper.ai_client._groq_client", None)
    @patch("scraper.ai_client.GROQ_API_KEY", "test-key")
    def test_cliente_no_inicializado_devuelve_none(self):
        assert post_groq_json("test prompt") is None

    @patch("scraper.ai_client._llamar_groq_modelo")
    def test_cadena_fallback_llama_modelos(self, mock_groq):
        mock_groq.return_value = {"resultado": "ok"}
        result = post_groq_json("test prompt")
        assert result == {"resultado": "ok"}
        assert mock_groq.called

    @patch("scraper.ai_client._llamar_groq_modelo")
    def test_cadena_fallback_escalada(self, mock_groq):
        from config import AI_MODEL_PRIMARY, AI_MODEL_SECONDARY, AI_MODEL_TERTIARY

        def side_effect(prompt, model_id, timeout=45):
            if model_id == AI_MODEL_PRIMARY:
                return None
            if model_id == AI_MODEL_SECONDARY:
                return {"from": "qwen"}
            return None

        mock_groq.side_effect = side_effect
        result = post_groq_json("test")
        assert result == {"from": "qwen"}

    @patch("scraper.ai_client._llamar_groq_modelo")
    def test_modelo_especifico_respetado(self, mock_groq):
        mock_groq.return_value = {"custom": True}
        result = post_groq_json("test", model="custom-model-id")
        mock_groq.assert_called_once_with("test", "custom-model-id", 45)
        assert result == {"custom": True}
