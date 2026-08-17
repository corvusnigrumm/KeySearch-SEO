import hashlib
import json
import os
import time
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

logger = logging.getLogger(__name__)

_CLEANUP_DONE = False


def _safe_mkdir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def _cache_path(cache_dir: str, key: str) -> str:
    return os.path.join(cache_dir, f"{key}.json")


def make_key(url: str) -> str:
    raw_url = url or ""
    try:
        parts = urlsplit(raw_url)
        query = parse_qsl(parts.query, keep_blank_values=True)
        query.sort(key=lambda item: (item[0], item[1]))
        canonical = urlunsplit(
            (
                (parts.scheme or "").lower(),
                (parts.netloc or "").lower(),
                parts.path or "",
                urlencode(query, doseq=True),
                parts.fragment or "",
            )
        )
    except Exception:
        canonical = raw_url
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cleanup_expired(cache_dir: str, ttl_seconds: int) -> int:
    """Elimina archivos de cache expirados. Devuelve la cantidad eliminada."""
    global _CLEANUP_DONE
    if _CLEANUP_DONE:
        return 0

    _CLEANUP_DONE = True
    removed = 0
    if not cache_dir or not os.path.isdir(cache_dir):
        return 0

    now = int(time.time())
    try:
        for filename in os.listdir(cache_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(cache_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                ts = int(payload.get("ts", 0))
                if ttl_seconds > 0 and (now - ts) > ttl_seconds:
                    os.remove(path)
                    removed += 1
            except Exception:
                continue
    except Exception as exc:
        logger.debug("Cache cleanup error: %s", exc)

    if removed:
        logger.info("Cache cleanup: %d expired files removed", removed)
    return removed


def get_text(cache_dir: str, key: str, ttl_seconds: int) -> str | None:
    if not cache_dir:
        return None

    cleanup_expired(cache_dir, ttl_seconds)

    path = _cache_path(cache_dir, key)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
        ts = int(payload.get("ts", 0))
        if ttl_seconds > 0 and (int(time.time()) - ts) > ttl_seconds:
            return None
        if payload.get("status") != 200:
            return None
        text = payload.get("text")
        return text if isinstance(text, str) else None
    except Exception:
        return None


def set_text(cache_dir: str, key: str, text: str, status: int = 200) -> None:
    if not cache_dir:
        return

    try:
        _safe_mkdir(cache_dir)
        path = _cache_path(cache_dir, key)
        payload = {"ts": int(time.time()), "status": int(status), "text": text}
        with open(path, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, ensure_ascii=False)
    except Exception:
        return
