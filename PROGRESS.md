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
| **Mini-paso 8.1** | Actualización de versiones de GitHub Actions | **Completado** | `actions/checkout@v7` y `astral-sh/setup-uv@v10.3.0` (tag inmutable verificado en releases oficiales). |
| **Paso 9** | SDK Python (`sdk/tokenledger`) | **Completado** | Envoltorio con `tl.track(...)` sin bloqueo, cola daemon y tolerancia total a fallos. |
| **Paso 10** | Dashboard en Streamlit | **Completado** | Pantalla única con métricas, gráficos horizontales con acento, tablas y estados de error/vacío. |
| **Paso 11** | Seed de datos de demostración | **Completado** | ~300 eventos sintéticos reproducibles; `traduccion` top feature, `globex` top customer. |
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
- **Instalación y Orden de Ejecución:** Instalación oficial de `uv` con acción `astral-sh/setup-uv` (con caché habilitada y Python 3.12), ejecutando en orden: `uv sync --frozen`, `uv run ruff check .`, `uv run ruff format --check .` y `uv run pytest --cov=app --cov-fail-under=80`.
- **README y Badge:** Creación de `README.md` con título, descripción y badge de CI apuntando a `https://github.com/EmanuelBaez7/tokenledger/actions/workflows/ci.yml/badge.svg`.
- **Verificación:** Validación de sintaxis YAML con `yaml.safe_load`; ejecución local de cobertura obteniendo 96.96% (umbral ≥ 80% superado).

### Mini-paso 8.1 — Actualización de versiones de GitHub Actions
- **Verificación de versiones oficiales:** Verificadas en las páginas de releases oficiales de GitHub:
  - `actions/checkout`: versión mayor estable `v7` (release oficial `v7.0.1`).
  - `astral-sh/setup-uv`: versión completa `v10.3.0` (debido al uso de tags inmutables desde v8.0.0).
- **Workflow:** Actualizado `.github/workflows/ci.yml` únicamente en las referencias `uses` para utilizar `actions/checkout@v7` y `astral-sh/setup-uv@v10.3.0`, preservando la configuración del servicio Postgres y comandos de build/test.
- **Validación:** Sintaxis YAML validada con `yaml.safe_load`, suite de tests completa y linters pasando al 100%.

### Paso 9 — SDK Python (`sdk/tokenledger`)
- **Cliente no bloqueante (`sdk/tokenledger/client.py`):** Clase `TokenLedger(base_url, api_key, timeout=2.0, http_client=None)` con cola acotada (`maxsize=1000`) y worker daemon en segundo plano. Exportado en `sdk/tokenledger/__init__.py`. Sin dependencias de `app/` ni de los SDKs oficiales de Anthropic u OpenAI.
- **Medición e Inferencia:** `track(fn, provider, feature, customer=None, model=None)` mide latencia en ms con `time.perf_counter`, devuelve exactamente el objeto original del LLM, y extrae tokens de forma desacoplada (`input_tokens`/`output_tokens` para Anthropic, `prompt_tokens`/`completion_tokens` para OpenAI; modelo de `response.model` o parámetro explícito). Si faltan tokens o modelo, registra warning y no envía el evento sin romper el flujo.
- **Manejo de Errores y Excepciones:** Si `fn()` lanza una excepción, re-lanza exactamente la excepción original sin envolverla; si se pasó `model`, encola un evento `status="error"` con tokens 0; si no se pasó `model`, registra un warning. Los fallos internos o de red del SDK son capturados en el worker y registrados con `logging.getLogger("tokenledger")`, nunca propagados al usuario ni filtrando la API key.
- **Drenado y Cierre:** Métodos `flush(timeout=5.0)` con espera acotada sobre `all_tasks_done` y `close()` para liberar recursos.
- **Decisión:** Para los tests de integración con hilo secundario, se inyecta `TestClient(app)` como `http_client`, omitiendo el parámetro `timeout` a nivel de petición para evitar advertencias de Starlette.
- **Tests Unitarios (16):** Extracción para Anthropic y OpenAI, retorno de objeto idéntico, latencia, tolerancia a fallos de red, re-lanzamiento de excepción con y sin modelo, falta de usage/model, descarte sin bloqueo con cola llena, entrega con `flush()`, y comprobación estricta de que la API key no aparece en logs (`caplog`).
- **Test de Integración (1):** Envío asíncrono con `tl.track()`, drenado con `tl.flush()`, y verificación de persistencia y agregación exacta de costos en `/v1/costs`.
- **CI y Cobertura:** Workflow de GitHub Actions actualizado con `--cov=app --cov=sdk --cov-fail-under=80`. Cobertura total alcanzada: 94.37%.

---


### Paso 10 — Dashboard en Streamlit
- **Módulo de datos (`dashboard/data.py`):** Funciones puras independientes de Streamlit para consumo de API con `httpx`, cálculo de totales (`calculate_totals`), costo medio por llamada seguro ante divisiones por cero, detección de feature más cara (`get_top_feature`), ordenamiento descendente y formateo para gráficos (`prepare_chart_data`) y tablas (`prepare_table_data`).
- **Manejo de Errores y Estados de Red:** Excepciones específicas (`MissingConfigurationError`, `UnauthorizedError`, `ApiConnectionError`, `ApiError`) que permiten mapear de forma amigable los estados definidos en `docs/03-APP-FLOW.md`: variables faltantes, 401 unauthorized sin filtrar clave, caída de red / API no disponible y respuesta vacía (invitando a ejecutar seed de demo).
- **Interfaz Streamlit (`dashboard/app.py`):** Pantalla única vertical conforme a `docs/04-UI-UX-BRIEF.md`: filtros de fecha con rango por defecto de últimos 14 días, 4 tarjetas de métricas destacadas, gráficos de barras horizontales (con etiquetas visibles, orden descendente y barra principal destacada con color de acento `#F59E0B` sobre azul `#2563EB`) y tablas comparativas formateadas.
- **Tema y Configuración:** `.streamlit/config.toml` con paleta corporativa neutra (`primaryColor="#2563EB"`, `backgroundColor="#FFFFFF"`, `secondaryBackgroundColor="#F8FAFC"`, `textColor="#0F172A"`).
- **Aislamiento de Dependencias:** `streamlit` aislado en dependency group `dashboard` en `pyproject.toml`, sin contaminar el entorno base de la API ni la imagen de producción ni el pipeline de CI. Actualizado `uv.lock`.
- **Docker Compose:** Agregado servicio `dashboard` en `docker-compose.yml` conectado a la red interna hacia `http://api:8000`. Puertos del host parametrizados con `API_HOST_PORT` (default 8000) y `DASHBOARD_HOST_PORT` (default 8501) documentados en `.env.example`.
- **Tests Unitarios:** 14 tests exhaustivos en `tests/unit/test_dashboard_data.py` cubriendo cálculos con Decimal, división por cero, ordenamiento, formateo de gráficos/tablas y manejo de errores HTTP y de red.

---


### Paso 11 — Seed de datos de demostración
- **Script:** `scripts/seed_demo.py` escribe directamente en la base (no vía API) usando `PriceRepository`, `CostCalculator` y `EventRepository`, con `created_at` histórico configurable por evento. Protección de host: rechaza DATABASE_URL no-local salvo `--allow-remote`; pide confirmación interactiva salvo `--yes`.
- **Función pura:** `generate_demo_events(rng, now)` genera ~300 `RawEvent` sin acceso a DB; reproducible con semilla fija 42. Sin `cost_usd` en el valor puro (se calcula al insertar).
- **Historia del dashboard:** `traduccion` es la feature más cara (muchos tokens de salida), `globex` es el cliente que más gasta (peso alto + spike en día 10 con 4× eventos extra con el modelo más caro). Tendencia ligeramente creciente de 0.8× a 1.2× por día. ~3% de eventos `status=error` con tokens 0 y costo 0.
- **Tests unitarios (16):** cantidad ~300, timestamps UTC, sin futuro, dentro de 14 días, 4 features y 5 customers, eventos sin customer, tasa de error, reproducibilidad exacta con misma semilla, traduccion top feature, globex top customer, todos los modelos presentes.
- **Test de integración (8):** inserta en `tokenledger_test`, verifica que suma por feature == suma por customer, `traduccion` primero por costo, `globex` primero por costo, eventos error con costo 0, tipos Decimal, todos los grupos presentes.
- **Dashboard:** mensaje de estado vacío actualizado a `uv run python scripts/seed_demo.py`.
- **Decisión:** El seed escribe directo en la base (no por la API) porque la API rechaza con 422 cualquier campo `created_at` enviado por el cliente, lo que haría imposible generar eventos históricos con fechas pasadas.

---


## Pendientes y avisos
- [ ] Crear el repo remoto en GitHub, hacer push y comprobar que el workflow queda en verde.
- [ ] El SDK se importa como sdk.tokenledger; empaquetarlo como paquete instalable queda para la v0.2.
- [x] **Formato de errores unificado (Resuelto en Mini-paso 6.1):** Formato único consistente `{"code", "message", "details"}` documentado e implementado para 401, 422 (modelo y validación Pydantic) y HTTP general.
- En este equipo Windows reserva los puertos 7918-8217; para correr uvicorn en local usa `--port 8500. Los tests no se ven afectados.

## Traspaso a Codex — 2026-10-27

- Auditoría de solo lectura de código, tests, workflows e historia, documentada en [AUDITORIA-HANDOFF.md](docs/AUDITORIA-HANDOFF.md). Se añade `AGENTS.md` como guía breve de entrada.
- Estado comprobado: pasos 0–11 con implementación y reservas en el informe; último commit funcional `2cc3234` (Paso 9, SDK). Paso 12 sin evidencia de inicio; pasos 13–14 pendientes.
- `git fetch origin` confirmó `origin/main` en `c8acf5a`; solo el SDK estaba sin push antes de esta entrega. Identidad de los 11 commits comprobada, sin excepciones.
- Verificación: 139 tests aprobados, 1 warning de Starlette/httpx; cobertura total app+sdk 94.37% (app 96.96%, sdk 85.48%); Ruff y formato limpios. Base de tests migrada sin diferencias respecto de los modelos.
- No se corrigieron hallazgos ni se avanzó de paso. Esta sesión autoriza únicamente el commit documental de traspaso; cualquier arreglo y continuación requieren aprobación del dueño. No se hizo push.

## Mini-paso 9.2 — Robustez de la API pública — 2026-10-27

Completado con autorización del dueño, preservando el historial anterior. Tres arreglos separados, test-first, identificados por mensaje exacto de commit, sin hashes:

| Hallazgo resuelto | Commit | Cambio |
|---|---|---|
| M3 | `fix: return 401 for non-ascii api keys` | Comparación constante de bytes UTF-8; clave no ASCII incorrecta → 401; Settings rechaza vacío y conserva claves cortas en desarrollo. SPEC recomienda clave larga y aleatoria en producción |
| M2 | `fix: return json for unexpected server errors` | Exception → 500 JSON internal_error con mensaje genérico, sin detalles internos; log de excepción sin agregar headers/cuerpo de la petición |
| M4 | `fix: validate numeric and date bounds` | Tokens ≤2147483647; desborde de numeric(14,8) → 422 cost_out_of_range antes de persistir; fechas from/to entre 2000-01-01 y 2100-12-31 inclusive |

- Ciclos test-first: M3 reprodujo 3 fallos y cerró con 143 tests; M2 reprodujo 1 fallo y cerró con 144; M4 reprodujo 10 fallos y cerró con 161. Ruff y formato comprobados antes de cada commit.
- Cobertura completa app+sdk: **94.57%**, con **161 tests aprobados** y un warning conocido de Starlette/httpx. No se añadieron dependencias ni migraciones.
- Comprobación manual con Invoke-RestMethod sobre la API actual en **8500**: input_tokens=2147483648 devuelve **422 validation_error** con detalle del campo, sin exponer la clave ni guardar el evento. La API local queda corriendo.
- [Informe actualizado](docs/AUDITORIA-HANDOFF.md): M2, M3 y M4 resueltos; los demás hallazgos y los pasos 12–14 siguen pendientes. No se hizo push, amend, reset ni force.

## Mini-paso 9.1 — Robustez y privacidad del SDK — 2026-10-27

Completado después del mini-paso 9.2, según la autorización del dueño. Dos commits separados, test-first, identificados por mensaje exacto y sin hashes:

| Hallazgo resuelto | Commit | Cambio |
|---|---|---|
| A1 | `fix: stop sdk from logging tracebacks that may contain the api key` | Warnings sin exc_info ni valores de metadatos; tipo de excepción y mensaje con la clave sustituida por ***. Clave en atributo privado, header construido al enviar y repr/str con api_key=*** |
| A2 | `fix: make sdk tolerate invalid usage data` | Tokens int no bool y no negativos; uso inválido/ausente no se encola. Extracción, modelo, evento y encolado protegidos; respuesta original intacta y excepción de fn relanzada tal cual, incluso si falla el seguimiento |

- A1 reprodujo 8 fallos y cerró con **169 tests aprobados**. A2 reprodujo 40 fallos y cerró con **211 tests aprobados**. Se comprobaron pytest, Ruff y formato antes de cada commit.
- Cobertura app+sdk **95.37%**; SDK redondeada **90%**. Persiste un warning conocido de Starlette/httpx. No se agregaron dependencias ni se modificaron API, base de datos o dashboard.
- [Auditoría actualizada](docs/AUDITORIA-HANDOFF.md): A1 y A2 resueltos, conservando evidencia histórica; los demás pendientes y los pasos 12–14 permanecen abiertos. No se hizo push, amend, reset ni force.

## Ajuste de referencias y privacidad documental

- `docs/AUDITORIA-HANDOFF.md` identifica por mensaje exacto el commit del SDK que era local al auditar; las correcciones y el traspaso ya emplean sus mensajes, conservando la evidencia histórica.
- `AGENTS.md` y `CLAUDE.md` prohíben datos del equipo y personales en documentos, informes y mensajes de commit, y requieren rutas relativas al repositorio. Sin cambios de código ni avance de paso.

