# Changelog

Todas las versiones notables de Key Search.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [10.0] - 2026-08-17

### Added
- **Testing**: 87 tests unitarios e integracion (conftest.py, tests de auth, categorizer, ai_client, http_cache, endpoints FastAPI)
- **Seguridad API**: Rate limiting in-memory por IP (30 req/min general, 5 req/min IA), Pydantic request/response models, security headers (X-Frame-Options, X-Content-Type-Options, etc.), global exception handler
- **Monitoring**: Structured JSON logging, Request ID middleware (UUID por request), `/health` endpoint con status de DB, uptime, version
- **Type Hints**: Anotaciones de retorno completas en 10 funciones criticas (ai_client, auth, database)
- **Pydantic Models**: SchemaRequest, AdsCopyRequest, GroqModelRequest, SchemaResponse, AdsCopyResponse, HealthResponse, ErrorResponse
- **Documentacion**: SECURITY.md, CHANGELOG.md, README actualizado con endpoints de monitoreo

### Changed
- `/api/generate-schema`, `/api/generate-ads-copy`, `/api/set-groq-model` ahora usan Pydantic models en vez de `request.json()` raw
- SECRET_KEY de auth ya no esta hardcodeada; genera fallback con `secrets.token_hex(32)`
- Logging reconfigurado a formato JSON estructurado

### Fixed
- `volume_estimator.py`: typo `"pasp a paso"` corregido a `"pasos a paso"`
- `kgr_estimator.py`: import muerto `import math, re` eliminado
- `utils.py`: `return False` inalcanzable eliminado
- `ai_filter.py` refacturado en 3 modulos: `ai_client.py`, `ai_filter.py`, `ai_generator.py`
- FastAPI lifespan: `@app.on_event("startup")` reemplazado por `@asynccontextmanager`
- Session persistence: in-memory dict reemplazado por DB-backed `PipelineSession`

### Removed
- `ai_filter.py` monolitico (789 lineas) - reemplazado por modulos separados

---

## [9.0] - 2026

### Added
- Editoria Studio con pipeline completo (IDEAR -> REDACTAR -> EXPORTAR DOCX)
- Content Brief + KGR integrados
- Copys de Ads (Google Ads, Facebook Ads, TikTok Hooks)
- SERP Weakness detector
- Clasificador automatico de keywords (categorizer)
- Google Ads Metrics via YAML
- Fallback a SQLite cuando no hay PostgreSQL
