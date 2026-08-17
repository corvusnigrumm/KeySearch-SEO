# Politica de Seguridad

## Reporte de Vulnerabilidades

Si descubres una vulnerabilidad de seguridad, **no abras un issue publico**. Envia un email a:
`[INSERTAR_EMAIL_DE_SEGURIDAD]`

Incluye:
- Descripcion del problema
- Pasos para reproducir
- Impacto potencial
- Sugerencia de remediacion (si aplica)

Responderemos en un plazo maximo de 72 horas.

## Medidas de Seguridad Implementadas

### Autenticacion
- JWT tokens con expiracion de 7 dias
- Password hashing con SHA-256 + salt aleatorio
- Cookies HttpOnly y SameSite=Lax

### API
- Rate limiting por IP (30 req/min general, 5 req/min para endpoints de IA)
- Validacion de entrada con Pydantic (min_length, max_length)
- Security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection)
- Global exception handler (no expone stack traces en produccion)
- Request IDs unicos para tracing

### Datos
- SQLite en `data/` excluido de git (ver `.gitignore`)
- Variables sensibles en `.env` (nunca en codigo fuente)
- `SECRET_KEY` generada dinamicamente si no se define en `.env`

## Configuracion Segura

```bash
# Generar un SECRET_KEY estable
python -c "import secrets; print(secrets.token_hex(32))"

# Agregar al .env
echo "JWT_SECRET=tu_clave_generada" >> .env
```

## Dependencias

Ejecutar periodicamente:
```bash
pip install --upgrade -r requirements.txt
```
