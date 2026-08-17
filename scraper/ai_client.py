"""
Infraestructura de clientes IA con fallback en cadena.

Cadena: ChatGPT (OpenAI) -> GPT-OSS 120B (Groq) -> Qwen QwQ 32B (Groq) -> Llama 3.3 70B (Groq)
"""
import json
import logging
import re
from typing import Any, Dict, Optional

import requests

from config import (
    GROQ_API_KEY, GROQ_MODEL, OPENAI_API_KEY,
    AI_MODEL_PRIMARY, AI_MODEL_SECONDARY, AI_MODEL_TERTIARY,
)

logger = logging.getLogger(__name__)


def _get_groq_client() -> Any:
    """Retorna el cliente Groq (lazy init)."""
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
    except Exception:
        return None


def _get_openai_client() -> Any:
    """Retorna el cliente OpenAI (lazy init)."""
    try:
        import openai
        return openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    except Exception:
        return None


_groq_client = None
_openai_client = None


def _ensure_clients() -> None:
    global _groq_client, _openai_client
    if _groq_client is None and GROQ_API_KEY:
        _groq_client = _get_groq_client()
    if _openai_client is None and OPENAI_API_KEY:
        _openai_client = _get_openai_client()


def limpiar_respuesta_json(raw_text: str) -> str:
    """Elimina etiquetas de razonamiento <think> y bloques markdown ```json."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    if text.startswith("```json"):
        text = text[7:]
        if "```" in text:
            text = text[:text.rfind("```")]
        text = text.strip()
    elif text.startswith("```"):
        text = text[3:]
        if "```" in text:
            text = text[:text.rfind("```")]
        text = text.strip()
    return text


def _llamar_groq_modelo(prompt: str, model_id: str, timeout: int = 45) -> Optional[Dict[str, Any]]:
    """Invoca un modelo especifico en Groq y retorna JSON parseado o None si falla."""
    _ensure_clients()
    if not GROQ_API_KEY or not _groq_client:
        return None
    is_reasoning = ("gpt-oss" in model_id.lower() or "deepseek" in model_id.lower() or "qwq" in model_id.lower())
    try:
        req_params = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "Eres una API JSON estricta. Devuelves UNICAMENTE JSON valido, sin etiquetas markdown ni texto extra."},
                {"role": "user", "content": prompt},
            ],
        }
        if is_reasoning:
            req_params["temperature"] = 1
            req_params["max_completion_tokens"] = 2048
            req_params["top_p"] = 1
            if "gpt-oss" in model_id.lower():
                req_params["reasoning_effort"] = "medium"
        else:
            req_params["temperature"] = 0.2
            req_params["max_tokens"] = 2048
        completion = _groq_client.chat.completions.create(**req_params)
        raw = completion.choices[0].message.content or ""
        clean = limpiar_respuesta_json(raw)
        return json.loads(clean) if clean else None
    except Exception as e:
        logger.warning("Groq [%s] fallo: %s", model_id, e)
        return None


def _llamar_openai_modelo(prompt: str, timeout: int = 45) -> Optional[Dict[str, Any]]:
    """Invoca ChatGPT real via OpenAI API si hay OPENAI_API_KEY. Retorna JSON o None."""
    _ensure_clients()
    if not OPENAI_API_KEY:
        return None

    if _openai_client:
        try:
            completion = _openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres una API JSON estricta. Devuelves UNICAMENTE JSON valido, sin etiquetas markdown ni texto extra."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2048,
                timeout=timeout,
            )
            raw = completion.choices[0].message.content or ""
            clean = limpiar_respuesta_json(raw)
            return json.loads(clean) if clean else None
        except Exception as e:
            err_str = str(e)
            if "billing_not_active" in err_str:
                logger.warning("OpenAI Key presente pero sin saldo activo. Usando fallback GPT-OSS...")
            else:
                logger.warning("OpenAI [gpt-4o-mini SDK] fallo: %s", e)

    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Eres una API JSON estricta. Devuelves UNICAMENTE JSON valido, sin etiquetas markdown ni texto extra."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            raw = data["choices"][0]["message"]["content"] or ""
            clean = limpiar_respuesta_json(raw)
            return json.loads(clean) if clean else None
        else:
            err_msg = resp.json().get("error", {}).get("message", resp.text)
            if "billing_not_active" in str(err_msg):
                logger.warning("OpenAI Key sin saldo activo. Escalando a GPT-OSS 120B...")
            else:
                logger.warning("OpenAI REST API HTTP %s: %s", resp.status_code, err_msg)
            return None
    except Exception as e:
        logger.warning("OpenAI REST API fallo: %s", e)
        return None


def post_groq_json(prompt: str, timeout: int = 45, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Cadena de IA con fallback automatico en 3 niveles:
      Nivel 1 -- ChatGPT (OpenAI) / GPT-OSS 120B (Groq)
      Nivel 2 -- Qwen QwQ 32B (Groq)
      Nivel 3 -- Llama 3.3 70B (Groq, fallback final)
    """
    if model and model not in (AI_MODEL_PRIMARY, AI_MODEL_SECONDARY, AI_MODEL_TERTIARY):
        return _llamar_groq_modelo(prompt, model, timeout)

    if OPENAI_API_KEY:
        result = _llamar_openai_modelo(prompt, timeout)
        if result is not None:
            logger.debug("IA activa: ChatGPT (OpenAI)")
            return result
        logger.warning("ChatGPT fallo, escalando a Nivel 1 (GPT-OSS 120B)...")

    result = _llamar_groq_modelo(prompt, AI_MODEL_PRIMARY, timeout)
    if result is not None:
        logger.debug("IA activa: GPT-OSS 120B (Groq - Nivel 1)")
        return result
    logger.warning("GPT-OSS 120B fallo, escalando a Nivel 2 (Qwen)...")

    result = _llamar_groq_modelo(prompt, AI_MODEL_SECONDARY, timeout)
    if result is not None:
        logger.debug("IA activa: Qwen QwQ 32B (Groq - Nivel 2)")
        return result
    logger.warning("Qwen fallo, escalando a Nivel 3 (Llama)...")

    result = _llamar_groq_modelo(prompt, AI_MODEL_TERTIARY, timeout)
    if result is not None:
        logger.debug("IA activa: Llama 3.3 70B (Groq - Nivel 3)")
        return result

    if not GROQ_API_KEY:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"}
    payload = {
        "model": AI_MODEL_TERTIARY,
        "messages": [
            {"role": "system", "content": "Devuelve UNICAMENTE JSON valido sin markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2, "max_tokens": 2048,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        clean = limpiar_respuesta_json(raw)
        return json.loads(clean) if clean else None
    except Exception as e:
        logger.warning("Fallback HTTP final fallo: %s", e)
        return None
