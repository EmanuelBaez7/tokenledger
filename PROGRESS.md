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
| **Mini-paso 6.1** | Unificación del formato de errores (SPEC §10) | **Completado** | Formato único `{"code", "message", "details"}` en toda la API; sin `detail` duplicado. |
| **Paso 7** | Reportes (`GET /v1/costs`) | **Completado** | `ReportService`, endpoint de costos agregados por dimensión, filtros de fechas y validaciones 422/401 unificadas. |
| **Paso 8** | CI en GitHub Actions | **Completado** | Workflow `.github/workflows/ci.yml` con Postgres 16, uv, ruff y cobertura ≥ 80%. |
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

### Mini-paso 6.1 — Unificación del formato de errores (SPEC §10)
- **Formato único:** Toda la API responde a errores con `{"code": "<string>", "message": "<texto legible>", "details": <opcional>}` sin campo `detail` duplicado.
- **Manejadores centralizados:** Módulo `app/api/errors.py` con manejadores para `StarletteHTTPException` (401 `unauthorized`, 404 `not_found`, etc.), `UnknownModelPriceError` (422 `unknown_model_price` con `details={"model": ...}`) y `RequestValidationError` (422 `validation_error`, `message="Request validation failed"`, y `details` con lista sanitizada de `{field, message}` sin exponer inputs sensibles).
- **Documentación:** Actualizado `SPEC.md` §10 y `docs/05-BACKEND-SCHEMA.md`.

### Paso 7 — Reportes (`GET /v1/costs`)
- **Servicio:** `ReportService` en `app/services/reports.py` que delega la agregación a `EventRepository.aggregate(group_by, date_from, date_to)` y valida que `from <= to` lanzando `InvalidDateRangeError`.
- **Ruta y Esquema:** `GET /v1/costs` en `app/api/v1/costs.py` con autenticación `X-API-Key`. Parámetro obligatorio `group_by` (`feature|customer|model`) y filtros opcionales `from` y `to` mapeados con `Query(alias="from")` y `Query(alias="to")`.
- **Serialización:** Esquema `CostReportItem` con `key`, `total_cost_usd` serializado como string con 8 decimales (nunca float), `total_input_tokens`, `total_output_tokens` y `calls`, ordenados por costo descendente.
- **Manejo de Errores Unificado:** `group_by` inválido o ausente, fechas mal formadas o `from > to` devuelven 422 con código `validation_error` en el formato centralizado `{code, message, details}`.
- **Tests:** Suite exhaustiva de tests unitarios y de integración en base `tokenledger_test` cubriendo agregación por feature, customer (con nulos como "unassigned"), model, orden descendente, suma coincidente con total global, filtro con inclusión de día final, auth 401, respuesta 200 vacía y casos 422.

### Paso 8 — CI en GitHub Actions
- **Workflow:** `.github/workflows/ci.yml` configurado para ejecutarse en `push` y `pull_request` sobre `main` y `master`, con `permissions: contents: read` y `timeout-minutes: 10`.
- **Servicios:** Contenedor de servicio PostgreSQL 16 con healthcheck (`pg_isready`), puertos mapeados (`5432:5432`) y credenciales de superusuario `postgres` para permitir crear y migrar la base `tokenledger_test` durante la suite de tests de integración.
- **Instalación y Orden de Ejecución:** Instalación oficial de `uv` con acción `astral-sh/setup-uv@v5` (con caché habilitada y Python 3.12), ejecutando en orden: `uv sync --frozen`, `uv run ruff check .`, `uv run ruff format --check .` y `uv run pytest --cov=app --cov-fail-under=80`.
- **README y Badge:** Creación de `README.md` con título, descripción y badge de CI apuntando a `https://github.com/EmanuelBaez7/tokenledger/actions/workflows/ci.yml/badge.svg`.
- **Verificación:** Validación de sintaxis YAML con `yaml.safe_load`; ejecución local de cobertura obteniendo 96.96% (umbral ≥ 80% superado).

---

## Pendientes y avisos
- [ ] Crear el repo remoto en GitHub, hacer push y comprobar que el workflow queda en verde.
- [x] **Formato de errores unificado (Resuelto en Mini-paso 6.1):** Formato único consistente `{"code", "message", "details"}` documentado e implementado para 401, 422 (modelo y validación Pydantic) y HTTP general.
- En este equipo Windows reserva los puertos 7918-8217; para correr uvicorn en local usa `--port 8500. Los tests no se ven afectados.

