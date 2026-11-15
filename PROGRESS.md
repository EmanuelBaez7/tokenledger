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
| **Paso 9** | SDK Python (`sdk/tokenledger`) | **Completado** | Envoltorio con `tl.track(...)` sin bloqueo, cola daemon y manejo probado de fallos de envío y datos de uso inválidos; errores del LLM conservan su excepción original. |
| **Mini-paso 9.1** | Robustez y privacidad del SDK | **Completado** | A1 y A2 resueltos; warnings redactados y validación de usage. Ejecutado después de 9.2. |
| **Mini-paso 9.2** | Robustez de la API pública | **Completado** | M3, M2 y M4 resueltos; autenticación UTF-8, errores JSON y límites numéricos/fechas. |
| **Mini-paso 9.3** | Seed, dashboard, fixtures y coherencia documental | **Completado** | M1, B6, M7, M8, M9 y B3 (estado documental) resueltos en cinco commits; pasos 12–14 pendientes. |
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
- `docker-compose.yml` con servicios `api`, `db` (Postgres 16 con healthcheck) y `dashboard` (añadido en el Paso 10).

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
- **Dashboard:** mensaje de estado vacío actualizado a `uv run python -m scripts.seed_demo`.
- **Decisión:** El seed escribe directo en la base (no por la API) porque la API rechaza con 422 cualquier campo `created_at` enviado por el cliente, lo que haría imposible generar eventos históricos con fechas pasadas.

---


## Pendientes y avisos
- [x] Repo remoto creado en GitHub y proyecto subido; las correcciones de los mini-pasos 9.1, 9.2 y 9.3 están publicadas en main.
- [x] CI remota de `docs: align project docs with the current state` comprobada en verde el 2026-10-30: [ejecución de Actions](https://github.com/EmanuelBaez7/tokenledger/actions/runs/40888062060). Cada nueva publicación requiere comprobar su propia ejecución.
- [ ] El SDK se importa como sdk.tokenledger; empaquetarlo como paquete instalable queda para la v0.2.
- [x] **Formato de errores unificado (Resuelto en Mini-paso 6.1):** Formato único consistente `{"code", "message", "details"}` documentado e implementado para 401, 422 (modelo y validación Pydantic) y HTTP general.
- En este equipo Windows reserva los puertos 7918-8217; para correr uvicorn en local usa `--port 8500`. Los tests no se ven afectados.

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


## Mini-paso 9.3 — Seed ejecutable y resumen exacto

- M1 y B6 resueltos por `fix: make demo seed runnable as a module`.
- Comando oficial desde la raíz: `uv run python -m scripts.seed_demo`.
- Regresión: subproceso con configuración sintética rechaza el host remoto sin ModuleNotFoundError; resumen con líderes distintos por costo y por llamadas, usando solo los costos insertados en esta ejecución.
- La reproducción inicial dio 2 fallos y 1 control aprobado. Validación previa al commit: pytest completo, Ruff y formato en verde. Los demás arreglos de 9.3 continúan pendientes.

### Mini-paso 9.3 — Precios YAML exactos

- M7 (YAML) resuelto por `fix: parse seed prices as decimals`.
- Loader derivado de SafeLoader conserva los escalares decimales como texto antes de construir Decimal, sin modificar el loader global. Los tests comprueban 0.1 y 2.50 exactos, incluida su escala, y los precios oficiales del seed sin float.
- Reproducción: 2 fallos antes del arreglo. Validación previa al commit: pytest completo (incluida idempotencia del seed), Ruff y formato en verde. La excepción visual del dashboard se documentará en el commit final autorizado.

### Mini-paso 9.3 — Errores visibles del dashboard

- M8 resuelto por `fix: show dashboard errors instead of an empty state`.
- JSON corrupto, estructura inesperada, tipos incorrectos y costos no finitos generan ApiError (DashboardError), sin trasladar JSONDecodeError/TypeError a la interfaz.
- Las consultas por feature, customer y global comparten manejo de errores con Reintentar. Solo respuestas correctas y realmente vacías muestran la ayuda del seed.
- MockTransport y UI simulada reproducen 8 fallos iniciales y comprueban fallos en la segunda y tercera consulta, JSON inválido y ausencia real de eventos. Validación previa al commit: pytest completo, Ruff y formato en verde; sin dependencias nuevas.

### Mini-paso 9.3 — Fixtures destructivas protegidas

- M9 resuelto por `test: guard destructive fixtures against non-test databases`.
- Función pura en tests/database_safety.py exige nombre terminado en _test y host localhost, 127.0.0.1 o db. Rechaza overrides del destino en parámetros de conexión y no imprime credenciales.
- Setup valida antes de conectar/migrar; db_session comprueba la URL real del engine antes de TRUNCATE. No existen DROP de fixtures. La URL administrativa conserva host, puerto y credenciales de TEST_DATABASE_URL, cambiando solo la base a postgres; creación/consulta usan el nombre validado y un identificador escapado.
- Tests primero; 13 casos comprueban política pura, conexión administrativa derivada y rechazo previo a cualquier conexión. Validación previa al commit: pytest completo, Ruff y formato en verde.

### Mini-paso 9.3 — Cierre documental

- B3 (coherencia y estado documental) resuelto por `docs: align project docs with the current state`.
- AGENTS/CLAUDE: commits solo por petición explícita, convencionales; nunca push, amend, reset ni force. SPEC y CLAUDE permiten float únicamente al dibujar gráficos del dashboard; métricas/tablas/cálculos/persistencia mantienen Decimal.
- SPEC/PLAN/PRD exigen model explícito para registrar errores del LLM. PLAN refleja los cuatro modelos del seed y su escritura directa mediante repositorios, por el rechazo de created_at en la API. Schema documenta rechazo 422 de campos prohibidos.
- Resumen actual: remoto existente y proyecto subido; Compose incluye api, db y dashboard; mini-pasos 9.1, 9.2 y 9.3 completados. Pasos 12–14, aceptación pública y CI remota pendientes; no se certifican con tests locales.

| Hallazgo resuelto | Mensaje exacto del commit |
|---|---|
| M1, B6 | `fix: make demo seed runnable as a module` |
| M7, YAML sin float | `fix: parse seed prices as decimals` |
| M8 | `fix: show dashboard errors instead of an empty state` |
| M9 | `test: guard destructive fixtures against non-test databases` |
| B3, coherencia documental; excepción visual de M7 | `docs: align project docs with the current state` |

- Sin dependencias añadidas ni cambios de esquema; no se avanzó al Paso 12 ni se hizo push, amend, reset o force.

Validación final de 9.3: **243 tests aprobados**, cobertura app+sdk **95.38%** (umbral 80% superado), Ruff y formato limpios (**63 archivos**). Persiste un warning conocido de Starlette/httpx; no se cambian dependencias para silenciarlo.

## Diagrama de arquitectura solicitado — 2026-10-28

- Análisis del código actual y diagrama Archify con 9 componentes, flujo principal de ingesta, dependencias externas y límites del proceso cliente y del proceso API.
- Artefacto: [.archify/architecture-tokenledger-20261028-105642/tokenledger.html](.archify/architecture-tokenledger-20261028-105642/tokenledger.html); fuente editable `candidate.json` en la misma carpeta, con referencias al código de la revisión analizada.
- Decisión de representación: agrupar EventService y ReportService como servicios de aplicación, y ambos repositorios como acceso a datos; conservar cálculo, envío asíncrono, dashboard y PostgreSQL como componentes diferenciados. Los módulos internos no representan servicios desplegados independientes.
- Detalles de privacidad, autenticación, precisión monetaria y operación en tarjetas. Vista de la implementación local; no presupone despliegue público.
- Archify: validate, deliver, check y browser-check aprobados; sin revisión visual manual. Ruff: `All checks passed!`; formato: `63 files already formatted`.
- `uv run pytest -q`: **169 aprobados, 74 errores de setup y 1 warning**; PostgreSQL agotó el tiempo de conexión en la fixture de integración. Pendiente restablecer esa conexión y repetir la suite; este resultado no sustituye la validación histórica anterior.
- Sin cambios de código, dependencias, configuración ni esquema; sin commit ni push. Pasos 12–14 pendientes.

## Fuente de arquitectura versionable — 2026-10-28

- `.gitignore` excluye `.archify/`, incluidos HTML generados y recibos con datos locales.
- Fuente editable conservada en `docs/architecture/tokenledger.architecture.json`, con rutas relativas, revisión fijada y salida en `.archify/tokenledger/tokenledger.html`.
- `docs/architecture/README.md` documenta requisitos y regeneración con una instalación local de Archify, sin agregar dependencias a la aplicación.
- Verificación: `git check-ignore` confirma la exclusión, JSON válido sin rutas absolutas locales y solo cambia la ruta de salida respecto del original; regeneración Archify con validate, deliver, check y browser-check aprobados. `git diff --check` limpio. No se repite pytest al no cambiar código de aplicación ni tests.
- Se conserva el artefacto original local. Sin cambios funcionales, sin commit ni push; pasos 12–14 pendientes. Persiste el pendiente de conexión de PostgreSQL registrado en la tarea anterior.

## Verificación visual local del dashboard — 2026-10-29

- Reproducido `ModuleNotFoundError: No module named 'dashboard'` al arrancar mediante el ejecutable de Streamlit. Resuelto en ejecución, sin modificar imports ni rutas: desde la raíz usar `uv run --group dashboard python -m streamlit run dashboard/app.py --server.port 8501`. El modo módulo conserva la raíz para importar el paquete dashboard.
- Configuración local de la sesión: API_BASE_URL apunta a `http://127.0.0.1:8500`; API_KEY cargada en memoria desde Settings, sin imprimirla ni guardar valores en archivos. Dashboard disponible en `http://localhost:8501`; API y dashboard quedan funcionando tras las pruebas.
- Navegador real: filtro de 14 días, del 16 al 29 de octubre, con 371 llamadas y gasto total mostrado de $7.2777; traduccion lidera por costo ($6.5731) y globex entre clientes ($5.1347).
- M8: API detenida de forma controlada; recarga y clic en Reintentar muestran error de conexión y conservan Reintentar, sin ayuda del seed ni estado vacío. Después se restauró la API con su base original.
- Vacío global: API temporal conectada a la base de tests validada y vaciada por la fixture del test de reporte vacío; la pantalla muestra `uv run python -m scripts.seed_demo`. No se borraron ni insertaron eventos en la base de demo. La API temporal quedó detenida.
- Rango vacío con eventos fuera del filtro: del 16 al 29 de octubre de 2020 muestra "Sin gasto en este rango", sin sugerir el seed; es el comportamiento definido en App Flow. Al terminar se restauró el filtro habitual.
- M1: subproceso con DATABASE_URL y API_KEY sintéticas, sin PYTHONPATH; exit 1 por host remote.invalid no permitido, sin ModuleNotFoundError ni conexión a una base remota.
- Validación: 30 tests enfocados aprobados; suite completa de 243 tests aprobados y cobertura app+sdk 95.38%, con un warning conocido de Starlette/httpx. PostgreSQL respondió en esta ejecución, resolviendo el bloqueo de validación registrado el día anterior.
- Sin cambios de código, dependencias ni esquema; solo se añade este registro, conservando los cambios locales de arquitectura. Sin commit, staging ni push; pasos 12–14 pendientes. Sugerencia fuera de esta verificación: alinear el comando del Dockerfile del dashboard con la invocación por módulo y validar la imagen.

## Preparación de la rama dashboard-v2 — 2026-10-30

- Publicación autorizada expresamente por el dueño para esta tarea: guardar la evidencia y la documentación de arquitectura pendiente con `docs: record dashboard verification results`, publicar main y comprobar Actions antes de crear `feature/dashboard-v2`.
- Al terminar la sesión anterior, el dueño pidió detener los servicios: API y dashboard se detuvieron y se verificaron libres los puertos 8500 y 8501. No se reiniciaron en esta tarea.
- Cambios documentales revisados: evidencia de verificación, fuente de arquitectura con referencias relativas, instrucciones de regeneración y exclusión de artefactos locales de Archify. Sin código funcional, dependencias ni esquema modificados.
- Verificación previa al commit: 169 tests unitarios aprobados, un warning conocido de Starlette/httpx; Ruff y formato limpios (63 archivos). JSON de arquitectura válido y sin rutas locales absolutas.
- Docker estaba detenido y el control automático rechazó su inicio; no se repitió la integración local. La suite completa se valida en el CI del nuevo commit, tras publicarlo; la evidencia local completa del 2026-10-29 permanece registrada arriba.
- La rama nueva se creará únicamente después de confirmar success en Actions para el commit exacto publicado. Esta tarea prepara la rama; no implementa dashboard-v2 ni avanza los pasos 12–14.

## Paso 10.1 — Brief de dashboard v2 — 2026-10-30

- Primer entregable: `docs: dashboard v2 design brief`, exclusivamente en feature/dashboard-v2. Brief reescrito y RF5 ampliado como alcance pendiente de implementación y aprobación.
- Decisiones: IBM Plex Sans/Mono locales; tokens claro/oscuro con azul de marca; tablas semánticas accesibles, comparación de periodos iguales, picos sobre los siete días previos, modo demo explícito y exports protegidos. Presupuestos y filtros cruzados excluidos.
- APIs locales revisadas: Streamlit 1.65.0 y Altair 6.3.0, contrastadas con documentación oficial. Pares de texto propuestos superan 4.5:1; la revisión de la interfaz renderizada queda para su implementación.
- Skills relacionadas revisadas: find-skills, visualize y spreadsheets. No hay una especializada en UI/UX; se propone frontend-design de Anthropic tras leerla, sin instalarla. No se añadieron dependencias, fuentes, fixture ni código.
- Validación previa al commit: 243 tests aprobados, cobertura app+sdk 95.38%, Ruff y formato limpios (63 archivos), con el warning conocido de Starlette/httpx. Se usó el PostgreSQL ya disponible; no se inició Docker. Staging revisado sin secretos ni artefactos locales.
- Detenerse tras el commit documental y esperar aprobación expresa del brief; los otros cinco commits siguen pendientes. Sin push, amend, reset ni force.

## Paso 10.1 — Refinamiento aprobado

- `docs: refine dashboard v2 design brief`: ajustes del dueño incorporados antes de implementar los commits 2 a 5. Detención tras la interfaz; commit 6 pendiente de revisión.
- Bordes de control 4.76:1 claro / 5.00:1 oscuro y foco 6.41:1 / 8.31:1; Sans para cifras y Mono solo identificadores. WOFF2 estáticos oficiales: dígitos tabulares nativos de 600 unidades, sin etiqueta tnum, alternativa aprobada. Flechas disponibles en Sans Pi; Latin1 cubre el resto de glifos solicitados.
- Totales del periodo concilian con KPI incluso con búsqueda/límite visual de 100; CSV conserva todas las coincidencias. Media previa cero no es pico; una serie diaria alimenta comparación/tendencia/picos, caché por sesión de 60 segundos sin clave API en hash/logs.
- No se instalará frontend-design. Una sola dependencia de aplicación nueva prevista: openpyxl en dashboard, en el commit de exports. Sin Docker ni push.

### Paso 10.1 — Agrupación diaria

- `feat: add daily grouping to the costs endpoint`: day agrupa por fecha UTC explícita y ordena fechas ascendentes, manteniendo formato, autenticación, filtros inclusivos y errores. SPEC sección 6 y schema actualizados.
- Test-first: tres fallos reproducidos y dos controles aprobados en repositorio, servicio y API; cubre cambios de día con offsets y configuración de sesión de base distinta. Sin migración ni nueva dependencia; suite y Ruff en verde antes del commit.

### Paso 10.1 — Datos, comparación y demo

- `feat: dashboard data layer with period comparison and demo source`: funciones separadas para periodos inclusivos, comparación, picos con media positiva, observaciones y snapshot conciliado. Una consulta day cubre ambas ventanas y siete días previos; las dimensiones se consultan por separado.
- Fixture de 400 eventos sintéticos generada una vez a partir del generador y CostCalculator, sin base; cinco ventanas permiten comparar periodos de 7/14/30 días. Costos exactos como strings, reloj inyectable y agregación local equivalente al contrato.
- Selector: solo demo si falta configuración y bloqueo en demo si lo fija el entorno. Sin imports de app/ en ejecución del dashboard; errores HTTP o totales inconsistentes nunca se convierten en vacío. Caché de sesión se conectará con la interfaz, tras instalar el grupo dashboard en CI con el commit de exports.
- Tests primero: periodos/base cero/umbral estricto, fixture reproducible, fuentes, segunda consulta fallida, conciliación y ejecución demo sin credenciales ni imports de aplicación. Sin dependencia nueva, Docker ni push.

### Paso 10.1 — CSV y Excel

- `feat: dashboard csv and excel exports`: funciones puras devuelven CSV con BOM y XLSX con seis hojas, metadatos sin secretos, formatos, A2 congelado, totales SUM y costo medio ponderado mediante división. Nota de Habilitar edición en Resumen; fórmulas verificadas como texto al reabrir el libro.
- Neutralización de etiquetas con prefijos de fórmula, incluso tras espacios/saltos; caracteres no válidos para XML filtrados antes de escribir. CSV exporta todas las coincidencias con orden activo, sin límite visual de 100; libro exporta todo el periodo.
- Única dependencia directa añadida: openpyxl en dashboard, necesaria para generar/reabrir fórmulas y formatos; uv.lock actualizado. CI instala el grupo dashboard para ejecutar estos tests.
- Trece pruebas específicas cubren inyección, BOM, 150 filas, hojas/formulas/formatos/nota, fechas y libros vacíos sin referencias circulares. Suite, Ruff y formato en verde antes del commit. Sin Docker ni push.


### Paso 10.1 — Interfaz del dashboard

- Implementación de tema, fuentes, KPI, gráficos, tablas y estados en `feat: modern dashboard interface`. Commits de refinamiento, API diaria, datos y exports ya realizados en el orden aprobado. No se ejecutó el commit documental 6.
- Fuentes oficiales sin modificar: nueve WOFF2 locales con licencia OFL y manifiesto SHA-256. Latin1 conserva cifras tabulares nativas de 600 unidades en 400/500/600 y los glifos españoles, dólar y menos; Sans Pi aporta las flechas. HTTP devuelve los nueve archivos exactos; el navegador observa las fuentes locales. Telemetría desactivada.
- Crítica visual: eliminados pie de versión/GitHub, control de fechas deshabilitado, exportaciones duplicadas por tabla, reglas verticales y barra redundante del 100% en totales. Se mantiene la doble regla del cierre contable. Etiquetas largas envueltas y cifras con Sans tabular; identificadores con Mono.
- Validación: 296 tests aprobados y cobertura app+sdk 95.38%; Ruff y formato limpios (79 archivos). Se conserva el warning conocido de Starlette/httpx. Pruebas con AppTest y MockTransport cubren fallos en las cinco consultas, JSON inválido y recuperación con Reintentar sin consultas duplicadas; caché por sesión, credenciales fuera del hash y cambio de credencial invalida datos.
- Navegador: capturas claro/oscuro a 1440, 1024 y 390 px en `.archify/dashboard-v2-review/`, sin desbordamiento de página; tablas con desplazamiento interno y totales exactos. CSV descargado con BOM y una coincidencia buscada; Excel descargado con cuatro features completas, seis hojas, fórmulas y nota de edición. La interfaz se revisó antes del pulido posterior.
- Streamlit 1.65 sincroniza los paneles y gráficos al ejecutar Python de nuevo. El menú nativo conserva el cambio de tema y la barra lateral indica pulsar Aplicar para sincronizarlo.
- Sin Docker, push, amend, reset ni force. No se modifica la base para esta revisión; capturas y logs locales están ignorados por Git.

### Paso 10.1 — Pulido de la interfaz revisada

- `refactor: polish dashboard chart, kpis and demo data` reúne los cambios solicitados y actualiza el brief. Hasta tres picos por exceso, con umbral del 5% del gasto del periodo y desempate por fecha.
- Tendencia con fechas cortas, etiquetas de serie directas y cuadrícula horizontal tenue. Gasto total incorpora su comparación y el quinto KPI muestra al cliente líder. La nota de Excel está dentro de Exportar.
- Demo determinista con 62, 70, 79, 89 y 100 llamadas en ventanas consecutivas de 14 días. Conserva el pico y los líderes traduccion y globex.
- Navegador confirmó los modos con y sin comparación, el pico en la tabla y el contraste mínimo de 17.06:1 claro y 14.15:1 oscuro en ayudas y etiquetas revisadas. La etiqueta y el valor del selector Demo mantienen el contraste al quedar bloqueados.
- Validación con PostgreSQL temporal local. 301 tests aprobados, cobertura app+sdk 95.38%, Ruff limpio y 80 archivos con formato correcto. El commit documental 6 queda pendiente.

### Paso 10.1 — Alineación, tema y pico de la demo

- «Cliente más caro» y etiquetas con altura fija de 48 px. Se verificó la misma posición relativa de los cinco valores a 1440, 1024 y 390 px.
- El aviso del tema usa los mismos 14 px que las demás ayudas. El menú nativo de Streamlit 1.65 cambia sus colores en el navegador. Los gráficos y paneles se sincronizan al pulsar Aplicar.
- La demo conserva el pico solo en la ventana más reciente y distribuye el gasto de las cuatro ventanas históricas. El día más caro de la comparación pasó a 0.08016580 USD frente a 1.03007700 USD en la ventana actual. Se conservan el crecimiento y los líderes.
- La medición previa de 17.06:1 correspondía al texto principal. Se midieron las etiquetas de KPI en 7.58:1 claro y 7.16:1 oscuro, las ayudas en 7.48–7.66:1 y 8.23–8.78:1, y el ámbar sobre el gráfico en 4.80:1 y 5.81:1, respectivamente.
- Validación local con PostgreSQL temporal fuera de Docker. 301 tests aprobados, cobertura app+sdk de 95.38%, Ruff y formato en verde.
- Los ajustes quedan locales para revisión. Compose, Dockerfile, la plantilla de entorno y el registro de arranque conservan sus cambios preexistentes.

### Paso 10.1 — Cierre del dashboard v2

- Interfaz aprobada. `fix: make dashboard theme-consistent and fix section overlap` sincroniza el tema claro y oscuro en tarjetas, tablas y gráficos desde el menú nativo. Aplicar queda para los filtros. Las distribuciones crecen con sus filas y etiquetas; se verificó la separación con Detalle a 1440, 1024 y 390 px.
- Exportar ofrece CSV con todas las coincidencias y el orden activo, y un libro Excel del periodo completo con fórmulas y la nota de Habilitar edición.
- La demo usa 400 eventos sintéticos deterministas sin API ni base. Fijar la fuente en demo bloquea el selector. Para 14 días, las cuatro tablas concilian con el KPI en $1.89550540; la comparación conserva variación diaria y el periodo actual tiene un solo pico.
- Validación de cierre: 302 pruebas aprobadas, cobertura de `app` y `sdk` de 95.38%, Ruff y formato en verde.

Arranque local en modo demo desde la raíz del repositorio, en PowerShell:

```powershell
$env:DASHBOARD_DATA_SOURCE = "demo"
uv run --group dashboard python -m streamlit run dashboard/app.py --server.port 8501
```

Si el 8501 no está disponible, usa `--server.port 8765`.

## Arranque local de Docker Compose en Windows — 2026-11-08

- Windows rechazó la apertura de los puertos 5432 y 8000 con Winsock 10013. Compose admite `DB_HOST_PORT` para publicar PostgreSQL en loopback. En este equipo se usa 15432 para PostgreSQL, 8500 para la API y 8501 para el dashboard. Los servicios se comunican por los puertos internos de Compose.
- El contenedor del dashboard inicia Streamlit como módulo para resolver los imports desde la raíz. `.env.example` documenta los puertos y el uso de `API_BASE_URL` al ejecutar Streamlit en el host. La configuración local se mantiene en el archivo ignorado por Git y excluido de las imágenes.
- `docker compose up -d --build` completó el arranque de los tres servicios y reutilizó el volumen de PostgreSQL. `/health`, la consulta autenticada a `/v1/costs` y el endpoint de salud de Streamlit devolvieron HTTP 200. El navegador mostró métricas y gráficos con fuente API.
- Validación final con `TEST_DATABASE_URL` apuntando a la base aislada `tokenledger_test` en 15432: 301 tests aprobados, cobertura app+sdk de 95.38% y el aviso conocido de Starlette/httpx. Ruff y formato limpios. Servicios activos para uso local.

## Pausa del entorno local — 2026-11-12

- Se cerró la instancia local de Streamlit. Docker Desktop ya estaba detenido.
- Se verificó que los puertos de desarrollo 8500, 8501 y 15432 y los puertos alternativos 8000 y 5432 quedaron libres.
