# SPEC.md — TokenLedger v0.1

> Fuente única de verdad. Si el código y este documento difieren, se detiene el trabajo y se pregunta al humano.

## 1. Objetivo
Registrar el gasto de llamadas a LLMs y responder: **¿qué función (feature) y qué cliente (customer) gastan más?**

## 2. Usuario objetivo
Un desarrollador de una startup pequeña que usa APIs de LLM y no sabe cuánto cuesta cada función ni cada cliente.

## 3. Fuera de alcance (v0.1) — NO implementar
Alertas, presupuestos, multi-tenant, login de usuarios, ClickHouse, OpenTelemetry, soporte de más de 2 proveedores, caché, colas de mensajes, frontend en React.

## 4. Requisitos funcionales
- **RF1** Ingestar un evento de uso de LLM vía API.
- **RF2** Calcular el costo en USD a partir de tokens y una tabla de precios en base de datos.
- **RF3** Consultar costos agregados por `feature`, `customer` o `model`, con filtro de fechas.
- **RF4** SDK Python que envuelve una llamada al LLM y envía el evento sin bloquear ni romper el código del usuario.
- **RF5** Dashboard de una pantalla con gasto por feature y por customer.
- **RF6** Endpoint `/health`.

## 5. Modelo de datos
**events**
| campo | tipo | notas |
|---|---|---|
| id | UUID PK | generado en el servidor |
| created_at | timestamptz | UTC, default now |
| provider | text | `anthropic` \| `openai` |
| model | text | ej. nombre del modelo tal como lo devuelve la API |
| input_tokens | int ≥ 0 | |
| output_tokens | int ≥ 0 | |
| cost_usd | numeric(14,8) | calculado en servidor, nunca enviado por el cliente |
| latency_ms | int ≥ 0 | opcional |
| feature | text | requerido, índice |
| customer | text | opcional, índice |
| status | text | `ok` \| `error` |

**prices**
| campo | tipo | notas |
|---|---|---|
| id | int PK | |
| provider, model | text | único junto con `effective_from` |
| input_per_mtok_usd | numeric(14,6) | precio por millón de tokens de entrada |
| output_per_mtok_usd | numeric(14,6) | precio por millón de tokens de salida |
| effective_from | date | |

Reglas: dinero siempre con `Decimal`, nunca `float`. Los precios viven en `prices.seed.yaml` y se cargan a la BD; **no se escriben precios reales en el código**. Los valores del seed son de ejemplo y el humano los verifica en las páginas oficiales de cada proveedor.

## 6. API (prefijo `/v1`)
Autenticación: header `X-API-Key` comparado con la variable de entorno `API_KEY`. Falta o error → 401.

- `POST /v1/events` → 201 con el evento y su `cost_usd`. Modelo sin precio → 422 con mensaje claro. Tokens negativos → 422.
- `GET /v1/costs?group_by=feature|customer|model&from=YYYY-MM-DD&to=YYYY-MM-DD` → lista de `{key, total_cost_usd, total_input_tokens, total_output_tokens, calls}` ordenada por costo descendente. `group_by` inválido → 422.
- `GET /health` → `{"status":"ok"}` sin auth.

## 7. SDK (`sdk/tokenledger`)
```python
tl = TokenLedger(base_url="http://localhost:8000", api_key="...")
resp = tl.track(lambda: client.messages.create(...), provider="anthropic", feature="resumen", customer="acme", model="claude-3-5-sonnet-20241022")
```
- Mide latencia, lee el uso de tokens de la respuesta (Anthropic: `usage.input_tokens/output_tokens`; OpenAI: `usage.prompt_tokens/completion_tokens`) y envía el evento en un hilo aparte.
- Parámetro opcional `model`: si no se pasa, se extrae de `response.model`. Si falta el modelo o el uso de tokens en la respuesta, se registra un warning y no se envía el evento, sin lanzar excepción.
- **Si el envío falla, nunca lanza excepción al usuario** (se registra un warning). Siempre devuelve la respuesta original del LLM.
- Si la llamada al LLM lanza excepción: si se pasó `model`, registra evento `status=error` con tokens 0 y ese modelo; si no se pasó `model`, no hay evento válido y solo se registra un warning. En ambos casos vuelve a lanzar la excepción original sin envolverla.

## 8. Arquitectura
Monolito modular, capas con dependencias en un solo sentido:

`api/` → `services/` → `repositories/` → `db/`

- `api/`: rutas FastAPI y esquemas Pydantic. Sin lógica de negocio.
- `services/`: `CostCalculator`, `EventService`, `ReportService`.
- `repositories/`: `EventRepository`, `PriceRepository` (SQLAlchemy). Único lugar con SQL.
- Patrones: **Repository**, **Strategy** (cálculo de costo por proveedor), **Dependency Injection** (FastAPI `Depends`).

Estructura del repo:
```
tokenledger/
├── app/{api,services,repositories,db,core}/
├── sdk/tokenledger/
├── dashboard/app.py
├── migrations/            # Alembic
├── tests/{unit,integration}/
├── prices.seed.yaml
├── docker-compose.yml  Dockerfile  pyproject.toml
├── .github/workflows/ci.yml
├── SPEC.md  PLAN.md  CLAUDE.md  DECISIONS.md  README.md
```

## 9. Stack
Python 3.12, uv, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2, Alembic, Postgres, pytest, httpx, ruff, Streamlit, Docker Compose, GitHub Actions.

## 10. Requisitos no funcionales
- `docker compose up` levanta API + Postgres + dashboard.
- Cobertura de tests ≥ 80% en `app/` y `sdk/`.
- `ruff check` y `ruff format --check` limpios.
- Secretos solo por variables de entorno; `.env.example` sin valores reales.
- Respuestas de error en JSON consistente con formato único: `{"code": "<string>", "message": "<texto>", "details": <opcional>}` (401: `unauthorized`, 422 modelo: `unknown_model_price` con modelo en details, 422 validación: `validation_error` con lista `{field, message}` sin datos sensibles).

## 11. Criterios de aceptación (v0.1 terminada)
1. `docker compose up` y luego `curl /health` devuelve ok.
2. Un evento enviado por el SDK aparece en `/v1/costs?group_by=feature` con el costo correcto (verificado por test).
3. CI en verde en GitHub.
4. Dashboard muestra datos de demostración.
5. Desplegado en una URL pública.
6. README con diagrama, y `DECISIONS.md` con al menos 5 decisiones.

## 12. Documentos complementarios y reglas añadidas
- Detalle en `docs/`: `01-PRD.md`, `02-TRD.md`, `03-APP-FLOW.md`, `04-UI-UX-BRIEF.md`, `05-BACKEND-SCHEMA.md`, `06-IMPLEMENTATION-PLAN.md`. **Este SPEC manda**; si hay contradicción, se pregunta al humano.
- **Privacidad:** no se almacenan prompts ni respuestas del LLM, solo metadatos de uso.
- **Índices:** los índices de `feature` y `customer` se implementan como compuestos con `created_at` (ver `05-BACKEND-SCHEMA.md`).
- **El cliente no envía** `id`, `created_at` ni `cost_usd`; si los incluye, la API responde 422.
