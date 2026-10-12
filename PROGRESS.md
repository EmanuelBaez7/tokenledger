# PROGRESS.md — TokenLedger v0.1

Estado de avance del proyecto según los pasos definidos en `PLAN.md` y `docs/06-IMPLEMENTATION-PLAN.md`.

## Resumen del progreso

| Paso | Descripción | Estado | Notas |
|---|---|---|---|
| **Paso 0** | Preparación manual y estructura inicial | Completado | Reglas, especificación y planes base. |
| **Paso 1** | Esqueleto del proyecto y endpoint `/health` | Completado | FastAPI, uv, pytest, ruff. |
| **Paso 2** | Docker Compose, Postgres y configuración | Completado | Settings tipados con Pydantic Settings. |
| **Paso 3** | Modelos de base de datos y migraciones Alembic | Completado | Modelos `Event` y `Price` con índices y constraints. |
| **Paso 4** | Precios y calculadora de costos (`CostCalculator`) | Completado | Patrón Strategy, Decimal a 8 decimales, seed YAML. |
| **Paso 5** | Repositorios (`EventRepository`, `PriceRepository`) | Completado | Consultas SQL y agregaciones por dimensión. |
| **Paso 6** | Ingesta de eventos (`POST /v1/events`) y autenticación | **Completado** | Auth con `X-API-Key`, esquemas Pydantic `extra="forbid"`, `EventService`, error 422 `unknown_model_price`, `cost_usd` serializado como string. |
| **Paso 7** | Reportes (`GET /v1/costs`) | Pendiente | `ReportService` y endpoint agregado por dimensión. |
| **Paso 8** | CI en GitHub Actions | Pendiente | Workflow con Postgres, ruff y cobertura ≥ 80%. |
| **Paso 9** | SDK Python (`sdk/tokenledger`) | Pendiente | Envoltorio con `tl.track(...)` sin bloqueo. |
| **Paso 10** | Dashboard en Streamlit | Pendiente | Métricas, filtros y gráficos de gasto. |
| **Paso 11** | Seed de datos de demostración | Pendiente | Generación de ~300 eventos sintéticos. |
| **Paso 12** | Despliegue en la nube | Pendiente | Despliegue público con base gestionada. |
| **Paso 13** | README y `DECISIONS.md` | Pendiente | Arquitectura y registro de decisiones de diseño. |
| **Paso 14** | Cierre y tag `v0.1.0` | Pendiente | Verificación de criterios de aceptación. |

---

## Detalle por paso completado

### Paso 0 — Preparación manual
- Configuración de repositorio, reglas en `CLAUDE.md`, especificación base en `SPEC.md` y plan de trabajo en `PLAN.md` y `docs/`.

### Paso 1 — Esqueleto del proyecto
- Configuración de `pyproject.toml` con Python 3.12, dependencias uv y herramientas de linting (`ruff`).
- Estructura modular `app/`, `sdk/`, `tests/` y endpoint `/health` público.

### Paso 2 — Docker Compose, Postgres y configuración
- `Settings` con `pydantic-settings` para `DATABASE_URL` y `API_KEY`.
- `docker-compose.yml` con servicios `api` y `db` (Postgres 16 con healthcheck).

### Paso 3 — Modelos de base de datos y migración
- Modelos SQLAlchemy 2: `Event` y `Price` con tipos precisos (`UUID`, `Numeric(14,8)`, `Numeric(14,6)`), índices compuestos y restricciones CHECK.
- Configuración de Alembic y primera migración ejecutada.

### Paso 4 — Precios y calculadora de costos
- `prices.seed.yaml` con valores de ejemplo y script `app/db/seed.py` idempotente.
- `CostCalculator` con patrón Strategy (`AnthropicCostStrategy`, `OpenAICostStrategy`), cálculos con `Decimal` a 8 decimales.

### Paso 5 — Repositorios
- `EventRepository`: método `add` y agregaciones multi-dimensión (`aggregate`) por `feature`, `customer` y `model` con filtros de fecha UTC.
- `PriceRepository`: método `get_current` para recuperar el precio vigente más reciente según fecha.
- Aislamiento estricto de SQL en `app/repositories/`.

### Paso 6 — Ingesta de eventos (`POST /v1/events`) y autenticación
- **Autenticación:** Dependencia `verify_api_key` con header `X-API-Key` validado contra `settings.API_KEY` usando `hmac.compare_digest`. Devuelve error 401 consistente con código `unauthorized`. `/health` se mantiene público.
- **Esquemas:** `EventCreate` con `extra="forbid"` (rechaza `cost_usd`, `id`, `created_at` con 422). Validaciones para provider (`anthropic|openai`), modelo (1-128 chars), tokens enteros (≥ 0), feature (1-64 chars sin espacios al borde), customer (opcional ≤ 128), latency_ms (opcional ≥ 0) y status (`ok|error`, default `ok`).
- **Servicio:** `EventService` busca el precio vigente con `PriceRepository.get_current(provider, model, fecha_utc_hoy)`, calcula con `CostCalculator`, persiste con `EventRepository` y efectúa el commit en la base. Si no hay precio, lanza `UnknownModelPriceError` traducido por la API a 422 con código `unknown_model_price` y nombre del modelo.
- **Ruta:** `POST /v1/events` devuelve 201 con el evento creado y `cost_usd` serializado como string (nunca float). Sin lógica de negocio ni SQL en la ruta.
- **Tests:** Suite de tests unitarios y de integración con base de test aislada (`tokenledger_test`) y API key provista mediante fixture.

---

## Pendientes y avisos
- Unificar el formato de errores: los 422 de validación de Pydantic devuelven {"detail":[...]} sin code ni message, a diferencia del 401 y unknown_model_price (SPEC §10). Arreglar antes del despliegue.
- En este equipo Windows reserva los puertos 7918-8217; para correr uvicorn en local usa --port 8500. Los tests no se ven afectados.
