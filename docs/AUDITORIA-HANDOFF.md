# Auditoría de traspaso a Codex

Fecha: **2026-10-27**. Revisión de `main` en `2cc3234`, antes del commit documental de este informe.

**Actualización del mini-paso 9.2:** M3, M2 y M4 están resueltos. La evidencia original se conserva como fotografía de la auditoría inicial; el cierre añadido al final registra las correcciones y su validación actual.

**Actualización del mini-paso 9.1:** A1 y A2 también están resueltos; ver el cierre del SDK añadido después del 9.2, según el orden de autorización del dueño.

## Alcance y conclusión

Se leyeron, en orden, `CLAUDE.md`, `SPEC.md`, `PROGRESS.md`, `PLAN.md` y los seis documentos de `docs/`. Auditoría de código, tests, migraciones, configuración, historia alcanzable y documentación. No se corrigieron hallazgos ni se modificaron código, tests o workflows. Únicos cambios previstos: `AGENTS.md`, este informe y una entrada añadida a `PROGRESS.md`.

Los pasos **0 a 11 tienen implementación**, con reservas documentadas abajo; el último commit funcional corresponde al **Paso 9 (SDK)**, terminado después del dashboard y del seed. **Paso 12 no iniciado según la evidencia del repositorio**: no existe `docs/DEPLOY.md`, ni un commit de preparación de despliegue. Pasos 13 y 14 pendientes. No puede descartarse trabajo externo que no esté registrado aquí.

Las pruebas existentes pasan, pero no demuestran cumplimiento completo: hay fallos reproducidos fuera de sus casos actuales. No se considera terminada v0.1.

## A. Commits contra el plan

Estados: **OK** = artefactos y commit localizados; **aviso** = desviación o aceptación incompleta; **fallo** = problema reproducido. Un paso pendiente no implica una regresión.

| Paso | Commit esperado en PLAN.md | Commit real: hash y mensaje | Archivos clave presentes | Estado |
|---|---|---|---|---|
| 0 | `chore: add spec, plan and project rules` | `d79aeb2 chore: add spec, plan and project rules` | SPEC, PLAN, CLAUDE, seis docs, .gitignore | OK; no hay skills del kit versionadas |
| 1 | `feat: project skeleton with health endpoint` | `37fc30a feat: skeleton, docker, db models, cost calculator and repositories` | pyproject, app/main.py, test_health.py | aviso: comparte commit con 2–5 |
| 2 | `feat: docker compose with postgres and typed settings` | `37fc30a feat: skeleton, docker, db models, cost calculator and repositories` | Dockerfile, Compose, config.py, test_config.py | aviso: commit compartido; arranque completo sin revalidar |
| 3 | `feat: db models and initial migration` | `37fc30a feat: skeleton, docker, db models, cost calculator and repositories` | models.py, session.py, migración inicial, test_db.py | aviso histórico; esquema y tests OK |
| 4 | `feat: price seeding and cost calculator with strategy pattern` | `37fc30a feat: skeleton, docker, db models, cost calculator and repositories` | prices.seed.yaml, db/seed.py, cost_calculator.py, tests | aviso: commit compartido; SQL y parseo monetario fuera de reglas |
| 5 | `feat: event and price repositories` | `37fc30a feat: skeleton, docker, db models, cost calculator and repositories` | repositories/events.py, prices.py, test_repositories.py | aviso: commit compartido; límite superior de fecha falla |
| Limpieza PRD | No previsto; eliminación solicitada del duplicado | `97f01b9 chore: remove stray 01-PRD.md from repo root` | 01-PRD.md raíz ausente; docs/01-PRD.md presente | OK |
| 6 | `feat: event ingestion endpoint with api key auth` | `0766337 feat: event ingestion endpoint with api key auth` | deps.py, schemas.py, v1/events.py, services/events.py, tests | aviso: límites numéricos y auth Unicode |
| 6.1 | No definido en PLAN; unificación de errores | `394fa83 refactor: unify api error format` | api/errors.py, tests de errores, SPEC y schema actualizados | aviso: errores inesperados aún no son JSON |
| 7 | `feat: cost reporting endpoint` | `929c332 feat: cost reporting endpoint` | v1/costs.py, services/reports.py, tests | aviso: `to=9999-12-31` falla |
| 8 | `ci: lint, tests and coverage gate` | `9c77a5d ci: lint, tests and coverage gate` | ci.yml, README con badge | aviso: resultado remoto no inspeccionado |
| 8.1 | No definido en PLAN; actualización de acciones | `d8fb3ac ci: update github actions versions` | checkout@v7, setup-uv@v10.3.0 | OK en archivos; ejecución remota por comprobar |
| 9 | `feat: python sdk with non-blocking tracking` | `2cc3234 feat: python sdk with non-blocking tracking` | sdk/tokenledger, 16 tests unitarios y 1 de integración | fallo en casos adicionales; sin push |
| 10 | `feat: streamlit dashboard` | `b8dd2f2 feat: streamlit dashboard` | dashboard/app.py, data.py, Dockerfile, tema, 14 tests | aviso: conversión a float; UI no inspeccionada |
| 11 | `chore: demo data generator` | `c8acf5a chore: demo data generator` | scripts/seed_demo.py, 16 tests unitarios y 8 de integración | fallo: comando publicado no importa app |
| 12 | `docs: deployment guide and production-ready dockerfile` | Ninguno | docs/DEPLOY.md ausente; imágenes aún sin preparar | aviso: pendiente, sin evidencia de inicio |
| 13 | `docs: readme with architecture diagram and decision log` | Ninguno | README básico de 5 líneas; DECISIONS.md ausente | aviso: pendiente |
| 14 | Tag `v0.1.0`; no mensaje de commit prescrito | Ninguno | Sin tags ni retrospectiva en DECISIONS.md | aviso: pendiente |

Evidencia: `git log --all --oneline --decorate`, `git show --numstat <hash>`, `git ls-files` y `git log --all -- Dockerfile dashboard/Dockerfile docs/DEPLOY.md DECISIONS.md`.

Corrección del contexto recibido: **Paso 0 sí tiene commit propio**. El commit combinado contiene **1–5**, no 0–5. No se reescribió historia publicada.

### Tamaño, tests y archivos mezclados

`git log --all --numstat` permite contar adiciones y eliminaciones; las cifras incluyen documentación y lockfile.

| Commit | Añadidas | Eliminadas | Total cambiado | Archivos de tests cambiados |
|---|---:|---:|---:|---:|
| d79aeb2 | 833 | 0 | 833 | 0: documentación/configuración inicial |
| 37fc30a | 3174 | 0 | 3174 | 10 |
| 97f01b9 | 0 | 63 | 63 | 0: eliminación documental |
| 0766337 | 885 | 1 | 886 | 3 |
| 394fa83 | 243 | 52 | 295 | 2 |
| 929c332 | 728 | 4 | 732 | 3 |
| 9c77a5d | 77 | 2 | 79 | 0: workflow/README/progreso |
| d8fb3ac | 12 | 3 | 15 | 0: versiones CI/progreso |
| b8dd2f2 | 1726 | 2 | 1728 | 1 |
| c8acf5a | 755 | 2 | 757 | 2 |
| 2cc3234 | 818 | 5 | 823 | 2 |

Cinco commits superan unas 800 líneas; en dashboard 948 líneas añadidas son del lockfile. Todos los commits de implementación incorporan tests; eso no demuestra que sus casos fueran suficientes ni que CI pasara históricamente. Los cuatro commits sin tests tienen alcance documental o de CI razonable.

Todos los mensajes siguen sintaxis de Conventional Commits. `ci:` está prescrito por PLAN pero no aparece en la lista abreviada de CLAUDE; `refactor:` tampoco aparece allí. Es una incoherencia documental, no un mensaje mal formado.

Mezclas adicionales: `PROGRESS.md` se creó dentro de `0766337`; el bloque Flujo de sesión de CLAUDE entró en `394fa83`. SDK también cambió SPEC, cobertura CI y `migrations/env.py` para conservar loggers. El duplicado raíz del PRD entró por error en `37fc30a` y fue eliminado por `97f01b9`. No quedan otros archivos históricos eliminados detectados. El kit `.claude/skills/` del Paso 0 no consta en Git; no se puede certificar si existe fuera del checkout.

## B. Identidad

Comando: `git log --all --format="%h %an <%ae> | %cn <%ce>"`.

En **los 11 commits alcanzables**, autor y committer son exactamente **Emanuel Baez <209174399+EmanuelBaez7@users.noreply.github.com>**. Sin excepciones:

| Hash | Autor | Committer |
|---|---|---|
| d79aeb2 | Emanuel Baez, noreply indicado | Igual |
| 37fc30a | Emanuel Baez, noreply indicado | Igual |
| 97f01b9 | Emanuel Baez, noreply indicado | Igual |
| 0766337 | Emanuel Baez, noreply indicado | Igual |
| 394fa83 | Emanuel Baez, noreply indicado | Igual |
| 929c332 | Emanuel Baez, noreply indicado | Igual |
| 9c77a5d | Emanuel Baez, noreply indicado | Igual |
| d8fb3ac | Emanuel Baez, noreply indicado | Igual |
| b8dd2f2 | Emanuel Baez, noreply indicado | Igual |
| c8acf5a | Emanuel Baez, noreply indicado | Igual |
| 2cc3234 | Emanuel Baez, noreply indicado | Igual |

`git config --show-origin --get-all user.name` y `user.email` devuelven una entrada cada uno desde `~/.gitconfig`, con esa identidad. `git config --local --get-regexp '^(user\.|include|includeIf)'` no devuelve entradas: **sin override local ni inclusión local detectados**. Alcance: historia alcanzable mediante refs; no objetos huérfanos inaccesibles.

## C. Sincronización

`git fetch origin` terminó correctamente. `git branch -vv` y `git status -sb`: única rama local `main`, inicialmente limpia y **ahead 1**. `origin/main` y `origin/HEAD` apuntan a `c8acf5a`. `git log origin/main..HEAD --oneline`: únicamente `2cc3234 feat: python sdk with non-blocking tracking`. Dashboard y seed ya están publicados. Sin ramas locales sobrantes y sin tags (`git tag -n` vacío).

El único commit autorizado de esta sesión añadirá un segundo commit local pendiente de push. No se hará push.

## D. Verificación técnica ejecutada

| Verificación | Resultado |
|---|---|
| `uv sync --frozen` | Exit 0; lockfile sin cambios. Quitó 26 paquetes del entorno local al excluir el grupo opcional dashboard; no cambió archivos versionados |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `53 files already formatted` |
| `uv run pytest --collect-only -q` | 139 tests recogidos, 1 warning |
| `uv run pytest tests/unit -q --tb=short` | 81 passed |
| `$env:PGCONNECT_TIMEOUT='2'; uv run pytest --cov=app --cov=sdk --cov-fail-under=80 -q --tb=no` | **139 passed, 1 warning**, 18.85 s, exit 0 |
| Cobertura total | **94.37%**, 551 sentencias, 31 sin cubrir; supera 80% |
| Cobertura calculada separadamente desde `.coverage` | app: **96.96%** (427/13); sdk: **85.48%** (124/18); ambos superan 80% |
| `docker compose config -q` | Exit 0, sin imprimir configuración expandida |
| `docker compose up -d db` | Base ya corriendo; servicio db healthy. Solo se solicitó levantar db |
| `compare_metadata(MigrationContext.configure(conn), Base.metadata)` sobre tokenledger_test | `[]`: sin diferencias entre tablas migradas y modelos |

Al principio `docker info` falló por ausencia del pipe de Docker Desktop. Un primer pytest quedó esperando el backend y emitió errores de setup; se interrumpió exclusivamente ese proceso de auditoría después de identificarlo por PID y comando. Docker quedó disponible durante la sesión (servidor 29.5.2); la repetición con espera de conexión acotada pasó completa. No se atribuyen los errores iniciales al código. Había una API antigua ya corriendo; no se levantó, reconstruyó ni se usó como prueba del HEAD actual. No se inició dashboard.

Warning observado: **StarletteDeprecationWarning** al importar `fastapi.testclient`: uso de httpx con starlette.testclient deprecado. No se instalaron dependencias nuevas ni se cambió el lockfile para silenciarlo. La versión exacta compatible debe evaluarse antes de corregirlo.

## E. Aceptación

**OK** significa verificado en esta ejecución; **parcial** indica evidencia automatizada sin validación completa; **pendiente** indica no demostrado. Los nombres de tests permiten ejecutarlos con `uv run pytest <ruta>::<nombre> -q`.

### SPEC §11

| Criterio | Cómo se verifica | Resultado |
|---|---|---|
| 1. Compose + /health | `tests/integration/test_health.py::test_health_check`; ejecutar Compose y petición real al puerto 8500 | Test OK; Compose valida y db healthy. Arranque completo de imágenes actuales y curl real pendientes |
| 2. SDK → reporte con costo correcto | `tests/integration/test_sdk_integration.py::test_sdk_track_event_persists_and_appears_in_costs` | OK: persistencia y agregado `0.00500000`; usa TestClient en proceso, no socket HTTP real |
| 3. CI verde en GitHub | Revisar ejecución remota asociada al SHA publicado y después al SHA del SDK | Pendiente: no se consultaron resultados remotos; suite local OK |
| 4. Dashboard con demo | tests/unit/test_dashboard_data.py y tests/integration/test_seed_demo.py; abrir Streamlit con seed | Parcial: tests OK; UI no inspeccionada; comando del seed falla (M1) |
| 5. URL pública | Acceder a API/dashboard públicos y guardar URL en documentación | Pendiente: ninguna URL de despliegue registrada |
| 6. README con diagrama + ≥5 decisiones | Inspección de README.md y DECISIONS.md | Pendiente: README de 5 líneas, sin diagrama; DECISIONS.md ausente |

### PRD, criterios 1 a 7

| Criterio | Test o comando | Resultado |
|---|---|---|
| 1. 1000/500 tokens → 0.01050000 | test_cost_calculator.py::test_calculate_cost_exact_example y test_events.py::test_create_event_happy_path_with_manual_cost_verification | OK |
| 2. Modelo sin precio → 422 con nombre | test_events.py::test_create_event_422_unknown_model_price | OK |
| 3. Clave incorrecta → 401 salvo health | test_events.py::test_create_event_401_invalid_key, test_costs.py::test_get_costs_401_invalid_api_key, test_events.py::test_health_remains_public_without_auth | OK para rutas funcionales; caracteres no ASCII fallan (M3). /docs y /openapi.json son públicos, coherente con App Flow, aunque PRD dice literalmente cualquier endpoint |
| 4. Orden y suma global por feature | test_costs.py::test_get_costs_ordered_by_cost_descending y ::test_get_costs_sum_matches_global_total | OK |
| 5. API caída no rompe track | test_sdk_client.py::test_network_failure_does_not_raise_to_caller | OK para fallo HTTP; no garantiza todos los fallos internos (A2) |
| 6. Error LLM → evento error + excepción original | test_sdk_client.py::test_llm_exception_with_model_enqueues_error_event y ::test_llm_exception_is_reraised_unchanged | OK con model explícito; sin model no hay evento, como manda SPEC §7 sobre el texto menos preciso del PRD |
| 7. Clon nuevo + Compose → health/dashboard | Inspección Compose/Dockerfiles; prueba manual de arranque limpio, migración, precios, demo y UI | Parcial: configuración válida, sin prueba de imágenes nuevas. API no migra ni carga precios al iniciar; puerto 8000 por defecto choca con este Windows |

Las siete aceptaciones sobre el despliegue público siguen pendientes; los tests locales no sustituyen esa validación. Tampoco se midieron instalación ≤10 min, p95 <150 ms ni consulta sobre 100000 eventos <500 ms. No son métricas obtenidas.

### RF1 a RF6

| Requisito | Evidencia | Resultado |
|---|---|---|
| RF1: ingesta | tests/integration/test_events.py y tests/unit/test_schemas.py | OK en casos actuales; rango de enteros pendiente (M4) |
| RF2: costo servidor/BD | tests de calculadora, seed, PriceRepository y EventService | OK para precios/casos actuales; parseo YAML usa float (M7) |
| RF3: agregados/fechas | tests/integration/test_costs.py y test_repositories.py | OK para rangos normales, nulos y día final; date.max falla (M4) |
| RF4: SDK | 16 unitarios + 1 integración | Parcial: comportamiento nominal y red OK; A1/A2 incumplen garantías |
| RF5: dashboard | 14 tests de datos; inspección de pantalla única, filtros, métricas y gráficos | Parcial: UI y responsive/teclado/contraste sin verificar; M7/M8 |
| RF6: health | test_health.py y test_events.py::test_health_remains_public_without_auth | OK en TestClient sin auth |

## F. Coherencia código/documentación

### Esquema

Comparación de `app/db/models.py`, migración `e1032904f93e` y docs/05; además `compare_metadata` sobre la BD de tests migrada devuelve `[]`.

| Elemento | Resultado |
|---|---|
| events: 11 columnas | Coinciden UUID PK, timestamptz, text, integer, numeric(14,8), opcionales y defaults gen_random_uuid/now/ok |
| events: seis CHECK | Coinciden proveedor, estado, tokens entrada/salida, costo y latencia opcional no negativos |
| events: tres índices | Coinciden feature+created_at, customer+created_at y created_at |
| prices: seis columnas | Coinciden id integer identity, proveedor/modelo text, dos numeric(14,6), effective_from date |
| prices: CHECK, único, índice | Coinciden tres CHECK; único provider/model/effective_from; índice con effective_from DESC |
| Longitudes y espacios | Se validan en Pydantic, no como CHECK de BD; docs describe reglas de entrada. No hay discrepancia de tipo SQL |
| Relaciones/contenido | Sin FK ni campos prompt/response, conforme a la decisión de metadatos |

API: POST /v1/events → 201, GET /v1/costs con aliases from/to, auth y /health público coinciden con SPEC §6. Costos son strings decimales; no se acepta id/created_at/cost_usd del cliente. Orden y `unassigned` están en SQL. Errores previstos 401, 404 y 422 coinciden con §10; excepciones inesperadas devuelven texto 500 (M2).

SDK: cola de 1000, un daemon, perf_counter, dos extractores, modelo explícito o response.model y rethrow del mismo objeto concuerdan con §7. No hay importaciones de app ni dependencias de los SDK oficiales. Las garantías de no romper y no filtrar clave no cubren A1/A2. Hay una heurística por nombre de clase TestClient en código productivo (B4).

Documentos obsoletos/incompletos:

- PROGRESS: remoto ya creado y con commits publicados, aunque sigue pendiente «Crear el repo remoto». La descripción de Docker enumera solo api/db, pero ya existe dashboard. «Tolerancia total a fallos» del SDK sobreafirma los casos cubiertos. El comando del seed no funciona como está anunciado. La antigua cifra 96.96% de app es histórica; la cobertura total actual es 94.37%, sin contradicción entre ambas.
- README: solo título, badge y descripción; faltan arranque, SDK, diagrama, endpoints, demo, privacidad, roadmap y decisiones. Es trabajo pendiente del Paso 13.
- PLAN Paso 11 propone SDK/API para históricos; la decisión posterior registrada en PROGRESS usa inserción directa por rechazo de created_at. Es una desviación razonada, no una corrección pendiente de implementación.
- PLAN Paso 9 y PRD criterio 6 omiten la necesidad de model explícito para errores. SPEC ya resolvió la regla; conviene actualizar documentos secundarios.
- App Flow sitúa Compose antes de configurar .env; onboarding y puertos no contemplan este Windows ni migración/seed de precios. El dashboard usa os.getenv y no carga .env por sí solo fuera de Compose.
- docs/05 dice «ignora» y luego «rechaza con 422» para campos prohibidos; el código rechaza, conforme a SPEC. «sin filtrar datos sensibles» es ambiguo: el handler excluye input/contexto y mantiene field/message.
- CLAUDE prohíbe al agente commitear al cerrar; esta sesión tiene autorización explícita para un solo commit. PLAN prescribe ci, tipo omitido por la lista de CLAUDE. No se cambiaron estas reglas históricas.
- docs/DEPLOY.md y DECISIONS.md no existen; backups, restauración, borrado y URL aún no están documentados. No se inventó despliegue realizado.

## G. Arquitectura, dinero y mantenimiento

Comando base: `rg -n 'float|select\(|\.execute\(|\.scalars\(|pg_insert|text\(|commit\(|type: ignore' app sdk scripts dashboard`; lectura de todas las funciones y análisis AST de los Python versionados.

- **SQL fuera de repositories:** DML real en app/db/seed.py:55–68 (`pg_insert`, execute), incumple la regla literal. Los defaults/DDL de models.py, Alembic y SQL de infraestructura de tests son necesarios para definir/probar la BD; no son consultas de negocio escondidas. scripts/seed_demo delega las consultas en repositorios.
- **Negocio en api:** no se encontró cálculo de dinero ni agregación SQL en rutas. Las validaciones de esquema y la traducción de InvalidDateRangeError a 422 pertenecen al borde HTTP. Servicios calculan/validan; repositorios consultan. EventService accede a event_repo.session.commit(), acoplamiento concreto mejorable, sin SQL en api.
- **float monetario:** dashboard/data.py:176 convierte costo a float para Altair; totales/tablas permanecen Decimal/string. app/db/seed.py recibe floats de yaml.safe_load y después hace Decimal(str(...)). Son excepciones a la prohibición absoluta del SPEC, no evidencia de costo erróneo en los ejemplos. Los float del SDK/dashboard para timeouts, y del seed para aleatoriedad/tendencia, no son dinero. La calculadora menciona float para rechazarlo.
- **Precios en código:** no hay tarifas reales en app/sdk/scripts/dashboard. Tarifas de ejemplo están en YAML; fixtures de tests usan precios explícitos para comprobar aritmética. MODELS_CONFIG contiene nombres, no tarifas.
- **Type hints:** todas las funciones de app/sdk/scripts/dashboard tienen parámetros y retorno anotados. Faltan en tests/integration/conftest.py:44 (parámetro/retorno de test_engine), :51 (test_engine), y test_seed_demo.py:15,23 (fixtures), :39,60,75,89,108,132,148,158 (seeded_session). Se detectó `type: ignore[assignment]` en api/deps.py:18; no se ejecutó un type checker porque no hay uno configurado.
- **Archivos Python >300 líneas:** scripts/seed_demo.py 370; tests/integration/test_costs.py 514; tests/integration/test_repositories.py 524; tests/unit/test_sdk_client.py 425. No hay otro Python versionado sobre ese umbral. uv.lock tiene más de 300 líneas por su naturaleza generada.
- **Código sin uso claro:** FEATURES y CUSTOMERS en scripts/seed_demo.py se usan en tests, pero la generación real emplea los diccionarios de pesos; hay duplicación de la fuente de etiquetas. AggregatedCost.__getitem__ y CostCalculator.calculate_cost conservan compatibilidad interna; no se eliminaron sin analizar consumidores.

## H. Seguridad e higiene

### Historia y búsqueda de secretos

`git log --all --full-history -- .env`: **sin salida**. `git ls-files`: `.env` no versionado; `.env.example` sí, como corresponde. Solo se enumeró la existencia/ignorancia de `.env`, nunca su contenido ni sus valores.

Se inspeccionaron **102 blobs únicos de los 11 commits alcanzables**, con `git rev-list --all`, `git ls-tree -r` y `git cat-file blob`. Búsqueda de firmas de claves OpenAI/Anthropic/GitHub/AWS, cabeceras de claves privadas, asignaciones de api_key/password/secret/token y contraseñas en URLs de Postgres. La salida del escáner mostró **solo archivo, línea y revisión**, sin valores. Firmas fuertes: **0**. Candidatos de asignación/URL: **26 ubicaciones por versión**, revisadas como ejemplos, fixtures o credenciales locales/CI. No se detectaron secretos reales; es una búsqueda por patrones con revisión, no prueba universal de ausencia ni examen de objetos huérfanos.

Ubicaciones revisadas (líneas correspondientes a la versión indicada por el escáner; algunas se repiten entre blobs):

| Archivo | Líneas candidatas | Clasificación |
|---|---|---|
| .env.example | 4 | Ejemplo local; sin reproducir valores |
| .github/workflows/ci.yml | 38,39 | Conexiones efímeras de CI |
| SPEC.md | 58 en versiones previas/actual | Ejemplo de uso |
| app/core/config.py | 14 | Conexión local por defecto |
| docker-compose.yml | 29 | Fallback público de ejemplo, riesgo si se publica sin configurar |
| sdk/tokenledger/client.py | 6 | Ejemplo de uso |
| tests/integration/conftest.py | 10,20 | Conexiones locales de tests |
| tests/integration/test_costs.py | 13 | Clave sintética |
| tests/integration/test_events.py | 14 | Clave sintética |
| tests/integration/test_sdk_integration.py | 15 | Clave sintética |
| tests/unit/test_config.py | 21 | Clave sintética |
| tests/unit/test_dashboard_data.py | 185,202,229 | Claves sintéticas |
| tests/unit/test_sdk_client.py | 83 | Clave sintética |

La ausencia de claves reales versionadas no elimina la fuga dinámica reproducida en A1.

### Otras comprobaciones

- `git check-ignore .env .venv/ .coverage .pytest_cache/ .ruff_cache/ app/__pycache__/`: todos ignorados. No hay estos archivos en el índice. `.env.production` **no está cubierto** por .gitignore; `.dockerignore` cubre solo .env exacto, .venv, caches básicas, .coverage/htmlcov; no cubre variantes .env.*, .coverage.* ni coverage.xml (M6).
- No hay binarios, volcados de datos ni caches versionados. uv.lock es el lockfile esperado; migrations/README es legítimo. El único archivo suelto histórico identificado fue el PRD raíz ya eliminado.
- hmac.compare_digest presente en api/deps.py:21; el uso sobre str no ASCII falla (M3). Settings requiere API_KEY pero acepta cadena vacía; Compose tiene fallback de ejemplo: revisar antes de publicar.
- CI tiene permisos mínimos `contents: read`, sin escritura, sin secrets de producción ni ejecución pull_request_target.
- Ambos Dockerfiles omiten USER: ejecutan como root; dependencias de pytest/ruff están en dependencias base y llegan a las imágenes. Imagen de uv usa latest. API no inicia migraciones ni seed (M5).
- No se almacenan prompts/respuestas en esquema o payload SDK. Demo usa etiquetas ficticias acme/globex/etc., no clientes reales. Dashboard no incluye un dataset real versionado; consume la API configurada. **No se inspeccionaron datos reales de una BD privada ni existe prueba de que cualquier futura API pública sea sintética**: esa garantía debe comprobarla el dueño al desplegar. El dashboard no tiene login, por decisión de alcance.
- Tests usan tokenledger_test en esta ejecución. TEST_DATABASE_URL es configurable sin comprobar nombre/host, y db_session hace TRUNCATE. La URL administrativa está fijada a localhost y no sigue esa configuración (M9).

## I. CI: inspección y comprobación humana

Workflow leído completo: `.github/workflows/ci.yml`.

- Disparadores push/pull_request a main/master; runner ubuntu-latest; límite 10 minutos.
- Servicio postgres:16 con healthcheck, puerto 5432 y entorno de pruebas; fixtures crean/migran tokenledger_test.
- `actions/checkout@v7`, `astral-sh/setup-uv@v10.3.0`, Python 3.12 y caché uv. Se reportan las referencias del archivo; no se certifica aquí la vigencia de esas releases.
- Orden correcto: sync frozen, ruff check, ruff format check, pytest con `--cov=app --cov=sdk --cov-fail-under=80`. SDK sí está incluido en HEAD; **origin/main aún no tiene ese cambio del SDK**.
- El umbral CI se aplica al total combinado, no obliga por separado a cada directorio; ahora ambos superan 80% localmente.

El dueño debe comprobar en GitHub Actions la ejecución del SHA publicado, que se resuelvan las dos acciones, Postgres arranque y pasen instalación/lint/formato/tests/cobertura. Después de autorizar un push futuro, comprobar también el SDK y su SHA exacto; un badge verde de c8acf5a no demuestra que 2cc3234 pasara CI. No se accedió a resultados remotos ni se ejecutó push.

## Hallazgos por severidad

Cada hallazgo incluye evidencia, impacto y recomendación. **Ningún arreglo fue implementado.** «Pequeño» significa que puede aislarse con tests relevantes en un commit; no autoriza hacerlo.

### Alta

**A1 — El SDK puede registrar la API key al capturar una excepción inesperada.** Evidencia: sdk/tokenledger/client.py:243–246 y :280–283 usan `exc_info=True`. Sonda con `uv run --no-sync python -`: un cliente HTTP falso lanza `RuntimeError` conteniendo la clave sintética recibida en headers; captura con logging.StreamHandler en StringIO devuelve `SDK_GENERIC_EXCEPTION contains_synthetic_key=True`. No se imprimió la clave. Impacto: el traceback puede contener secretos de una excepción inesperada; el test actual solo cubre HTTPError saneado. Recomendación: registrar mensajes constantes/tipo de error sin excepción cruda o aplicar saneamiento explícito; añadir regresión con excepción no HTTP. **Commit pequeño: sí.** No se encontró una clave real filtrada en esta sesión.

**A2 — track puede romper la llamada del usuario al procesar usage inválido.** Evidencia: client.py:173 compara `< 0` fuera de los bloques protectores; respuesta sintética con `usage.input_tokens=None` y output_tokens válido → `SDK_NONE_USAGE raised=TypeError`. El objeto de respuesta no llega al usuario. Impacto: incumple RF4 y §7 ante metadatos incompletos/inválidos; los extractores solo capturan errores al leer atributos. Recomendación: validar tipos/valores y proteger la etapa de seguimiento, preservando la respuesta y la excepción original del LLM; no ocultar errores del LLM. **Commit pequeño: sí.**

### Media

**M1 — El comando de demo documentado no funciona desde la raíz.** Evidencia: ejecutar en subproceso `uv run python scripts/seed_demo.py --yes` con API_KEY sintética y DATABASE_URL sintética remota (para rechazar antes de insertar) devuelve exit 1, `ModuleNotFoundError: No module named 'app'`, antes de alcanzar la protección de host. scripts/seed_demo.py:346–347 importa app; Python coloca scripts, no la raíz, como directorio inicial de imports. Los tests importan el módulo con pythonpath configurado por pytest y no detectan el fallo CLI. Impacto: onboarding y ayuda del dashboard fallan. Recomendación: documentar/invocar `uv run python -m scripts.seed_demo` consistentemente y validar la CLI sin DB; no añadir sys.path a mano. **Commit pequeño: sí.**

**M2 — Los errores inesperados no siguen el formato JSON del SPEC.** Evidencia: api/errors.py:96–100 solo registra tres familias concretas. Sonda TestClient(raise_server_exceptions=False) con get_report_service sustituido en memoria por uno que lanza RuntimeError: `500`, `text/plain; charset=utf-8`, `Internal Server Error`. Impacto: consumidores no pueden tratar todos los errores con {code,message,details}; errores de BD siguen esta ruta. Recomendación: handler general con JSON seguro y logging saneado; conservar detalles internos fuera de la respuesta. **Commit pequeño: sí.**

**M3 — Clave con caracteres no ASCII provoca error en compare_digest.** Evidencia: llamada directa a verify_api_key con una clave sintética no ASCII y Settings de auditoría → `AUTH_NON_ASCII raised=TypeError`. api/deps.py:21 compara str; compare_digest solo admite str ASCII. Impacto: una clave inválida puede generar 500 en vez de 401; configuración no ASCII tampoco se valida. Recomendación: definir representación de comparación en bytes o política de claves validada y asegurar 401 para entrada inválida; probar ambos casos. **Commit pequeño: sí.**

**M4 — Entradas válidas para Pydantic exceden límites de BD/fechas.** Evidencia: EventCreate acepta input_tokens=2**31 (`OVERSIZED_TOKEN schema_accepts_above_postgres_int=True`), mientras models/migración usan integer de Postgres. EventRepository(None).aggregate('feature', date_to=date.max) → `OverflowError` en events.py:106 antes de consultar. Costos numeric(14,8) también tienen un máximo que no se valida cuando crecen tokens/precios. Impacto: peticiones aceptadas pueden acabar en 500, no 422. Recomendación: límites coherentes con almacenamiento y manejo explícito del día máximo/costo desbordado; pruebas de borde. **Commit pequeño: dividir en números y fechas.**

**M5 — Preparación de producción/arranque pendiente.** Evidencia: ambos Dockerfiles carecen de USER; pyproject pone pytest/pytest-cov/ruff en dependencias base; CMD API solo ejecuta uvicorn. No hay DEPLOY.md ni ejecución automática de Alembic/seed. Compose usa puerto 8000 por defecto y fallback de API_KEY de ejemplo. Impacto: imágenes aún no aptas para declarar Paso 12 completo; base nueva no ofrece ingesta sin preparar tablas/precios y este Windows requiere puerto 8500. Recomendación: atenderlo en Paso 12 con estrategia explícita de migración, usuario sin privilegios, dependencias apropiadas y configuración obligatoria para producción. **Commit pequeño: varios, dentro del paso aprobado; no desplegar aún.**

**M6 — Exclusiones incompletas para variantes de secretos y cobertura.** Evidencia: `git check-ignore .env.production` no devuelve coincidencia; lectura de .dockerignore muestra solo .env exacto y .coverage exacto. Impacto: futuros .env.production/.env.backup pueden entrar al repo o al contexto COPY . .; no hay evidencia de que existan/versionen ahora. Recomendación: patrones para variantes de entorno preservando .env.example y para artefactos de cobertura; verificar con check-ignore y contexto Docker. **Commit pequeño: sí.**

**M7 — Dos excepciones a «dinero nunca float».** Evidencia: `type(load_seed_prices()[0]['input_per_mtok_usd']).__name__` → `float`; db/seed convierte después con Decimal(str(...)). dashboard/data.py:176 usa float(cost_decimal), también confirmado por su test. Impacto: incumplimiento literal, posible pérdida previa de precisión en otros YAML; el gráfico aproxima aunque métricas/tablas y costos persistidos son exactos para los datos probados. Recomendación: parseo decimal desde origen; decidir y documentar con el dueño si la visualización permite conversión solo al renderizar o cambiar representación. **Commit pequeño: sí para YAML; dashboard requiere decidir la excepción al SPEC antes de cambiar código.**

**M8 — Dashboard puede fallar con JSON inválido o esconder un fallo de API como vacío.** Evidencia: data.py:104 retorna response.json sin validar forma, y app.py:161–163 captura cualquier excepción en la consulta global y la convierte a []. Sonda con MockTransport que devuelve 200/no JSON → JSONDecodeError; main no captura ese tipo. Impacto: traceback de UI o guía de seed engañosa ante respuesta corrupta/caída entre consultas. Recomendación: validar/deserializar y mapear a DashboardError; diferenciar fallo y ausencia de datos. **Commit pequeño: sí.**

**M9 — Fixtures de integración confían en una URL de test sin protección.** Evidencia: conftest.py:8–14 acepta TEST_DATABASE_URL; :54 trunca tablas; :20 fija conexión administrativa local aunque la URL configurada sea otra. Impacto: con una variable mal configurada se puede truncar una base ajena a tests; una BD remota legítima tampoco se prepara consistentemente. En esta sesión se comprobó tokenledger_test. Recomendación: validar nombre/host de test, derivar conexión administrativa de forma segura y fallar antes de SQL destructivo si no se cumple la política. **Commit pequeño: sí.**

### Baja

**B1 — SQL del seed fuera de repositories y sesión del repositorio expuesta.** Evidencia: búsqueda rg localiza pg_insert/execute en db/seed.py:55–68 y EventService usa event_repo.session.commit en :64. Impacto: excepción a la separación prometida; refactor futuro más difícil. Recomendación: mover upsert de precios a repositorio; mantener explícita la frontera transaccional sin abstracciones innecesarias. **Commit pequeño: sí para seed; transacciones por separado.**

**B2 — Tamaños y anotaciones de tests.** Evidencia: análisis AST y conteos de G; cuatro Python superan 300 líneas, y faltan hints en fixtures/tests de demo. deps.py:18 silencia una asignación incompatible. Impacto: navegación y revisión más difíciles; Ruff actual no controla tipado completo. Recomendación: separar generación/CLI o tests por responsabilidad cuando se modifiquen, completar anotaciones y corregir firma de dependencia. **Commit pequeño: varios independientes.**

**B3 — Documentación de avance desactualizada y artefactos de cierre pendientes.** Evidencia: secciones A/F; README 5 líneas, DECISIONS/DEPLOY/tag ausentes, PROGRESS aún habla de crear remoto. Impacto: traspaso confuso y criterios de lanzamiento no demostrados. Recomendación: corregir estado en una sesión aprobada y completar 12–14 en orden. **Commit pequeño: sí para erratas/estado; no para certificar despliegue/aceptación sin ejecutarlos.**

**B4 — SDK contiene adaptación específica de tests y cierre poco observable.** Evidencia: client.py:258 decide timeout según nombre de clase terminado en TestClient; :211 captura `(queue.Full, Exception)` y omite cualquier diagnóstico; :30 fuerza logger.disabled=False. Impacto: comportamiento condicionado por nombre, errores de cierre invisibles y configuración de logs del consumidor sobrescrita. Recomendación: contrato claro del transporte, timeout en construcción y cierre acotado con estado verificable; respetar el logger del consumidor. **Commit pequeño: separar transporte y ciclo de vida.** No se afirma una pérdida de eventos reproducida en el flujo nominal.

**B5 — Reproducibilidad/observabilidad de CI e imágenes.** Evidencia: Dockerfiles copian uv:latest; workflow usa tags en lugar de SHA; cobertura limita total combinado. Hay un warning upstream conocido. Impacto: cambios externos pueden alterar construcciones; un directorio podría caer bajo 80% sin fallar el total. Recomendación: evaluar fijación de versiones/digests y, si se exige umbral individual, comprobarlo explícitamente; resolver warning con compatibilidad verificada. **Commit pequeño: sí, por tema.** No se observaron acciones remotas fallidas ni se certificó vigencia de tags.

**B6 — Resumen del seed llama «Top» al mayor número de eventos.** Evidencia: scripts/seed_demo.py:314–321 toma max de contadores, no de costos; el comentario sí lo reconoce. Impacto: con otros datos/semillas la salida puede confundirse con el mayor gasto, objetivo central del producto. Recomendación: etiquetar «por llamadas» o informar costo calculado durante inserción. **Commit pequeño: sí.**

## Reproducción de las sondas sin modificar archivos

Se usó Python por stdin (`@' ... '@ | uv run --no-sync python -` en PowerShell), objetos SimpleNamespace y transportes falsos; sin llamadas a LLM ni escrituras de negocio. Las dependencias FastAPI se sustituyeron solo en memoria y se limpiaron al terminar. Para M1 el subproceso recibió entorno sintético con host remoto no permitido, de forma que, incluso si importara correctamente, abortara antes de insertar.

Fragmentos esenciales de reproducción (usar claves sintéticas, nunca .env):

```python
# A2: el transporte falso basta porque el fallo ocurre antes de encolar.
response = SimpleNamespace(
    model="audit-model",
    usage=SimpleNamespace(input_tokens=None, output_tokens=1),
)
sdk.track(lambda: response, provider="anthropic", feature="audit")
# Resultado observado: TypeError; cerrar sdk en finally.

# A1: inyectar este cliente y capturar el logger tokenledger en StringIO.
class UnsafeClient:
    def post(self, *args, **kwargs):
        raise RuntimeError(kwargs["headers"]["X-API-Key"])
# track con usage válido, flush y close; comprobar presencia booleana de
# la clave sintética en el buffer sin imprimirlo.

# M3/M4, con Settings(_env_file=None, API_KEY="audit-synthetic-key"):
verify_api_key("é", settings)  # TypeError
EventRepository(None).aggregate("feature", date_to=date.max)  # OverflowError
```

Estas sondas diagnostican casos omitidos por los tests actuales; no se añadieron a la suite por la prohibición expresa de modificarla.

## Cierre y límites de esta entrega

El cierre ejecutó de nuevo `uv run pytest -q` (**139 passed, 1 warning**, 13.74 s), `uv run ruff check .` (**All checks passed!**) y `uv run ruff format --check .` (**53 files already formatted**). Se conservó PGCONNECT_TIMEOUT=2 solo en el proceso de validación para acotar la conexión. Solo se preparan los tres documentos autorizados; se verifica que `.env`, `.venv` y `__pycache__` no entren al índice. Único commit: `docs: add agents guide and handoff audit`. Una comparación con `git show HEAD:PROGRESS.md` confirmó que la nota conserva íntegro el contenido anterior, normalizando únicamente finales de línea para la comprobación.

No se hizo push, amend, reset, force, tag, despliegue, corrección funcional ni avance al Paso 12. Quedan pendientes aprobación del dueño para arreglar hallazgos, comprobación de CI remota, validación visual y lanzamiento. Este informe no toma un badge, tests locales o un contenedor antiguo como prueba de despliegue del código actual.

## Resolución del mini-paso 9.2 — 2026-10-27

Tres arreglos autorizados, test-first y en el orden M3 → M2 → M4. Se identifican por sus mensajes exactos de commit, sin hashes, según la instrucción del dueño.

| Hallazgo | Estado | Commit | Evidencia de regresión y corrección |
|---|---|---|---|
| M3 | **Resuelto** | `fix: return 401 for non-ascii api keys` | tests/unit/test_api_auth.py reprodujo dos respuestas 500; test_config.py reprodujo la clave vacía aceptada. Comparación UTF-8 en bytes y Settings no vacío; clave corta correcta conserva 200. Suite previa al commit: 143 passed; Ruff y formato limpios |
| M2 | **Resuelto** | `fix: return json for unexpected server errors` | tests/unit/test_api_errors.py falló por content-type text/plain. Handler general devuelve exactamente 500 application/json con internal_error y mensaje seguro; registra excepción sin agregar headers/cuerpo. Suite previa al commit: 144 passed; Ruff y formato limpios |
| M4 | **Resuelto** | `fix: validate numeric and date bounds` | tests/integration/test_api_bounds.py y test_event_service.py reprodujeron 10 fallos. Ahora ambos tokens aceptan 2147483647 y rechazan 2147483648; costo máximo 999999.99999999 USD, desborde 422 cost_out_of_range antes de add/commit; from/to limitados inclusivamente a 2000-01-01…2100-12-31, incluido rechazo de 9999-12-31 |

Verificación completa: **161 tests aprobados**, un warning conocido de Starlette/httpx; cobertura app+sdk **94.57%**, por encima del 80%. Ninguna dependencia añadida ni migración necesaria: se ajustaron validaciones y traducción de errores, no el esquema SQL.

Prueba manual sobre el código actualizado con uvicorn en `127.0.0.1:8500`: `Invoke-RestMethod` usando la clave configurada cargada en memoria, sin imprimirla, y el payload del dueño con input_tokens=2147483648 devolvió **422**, `code=validation_error`, `message=Request validation failed`, `details=[{field: input_tokens, message: Input should be less than or equal to 2147483647}]`. No se guardó ese evento.

Los demás hallazgos permanecen pendientes. No se hizo push, amend, reset, force ni se avanzó al Paso 12. La API local de comprobación queda corriendo en el puerto 8500.

## Resolución del mini-paso 9.1 — 2026-10-27

Ejecutado después del 9.2, con dos commits separados y test-first, sin reescribir historia. Los arreglos se identifican por sus mensajes exactos, sin hashes:

| Hallazgo | Estado | Commit | Evidencia de regresión y corrección |
|---|---|---|---|
| A1 | **Resuelto** | `fix: stop sdk from logging tracebacks that may contain the api key` | tests/unit/test_sdk_security.py reprodujo 8 fallos. Comprueba RuntimeError con la clave del header, HTTPError, timeout, fallo del worker, respuestas 401/422/500 y cola llena. Los warnings no adjuntan traceback, registran tipo y mensaje redactado con ***, y no incluyen valores de metadatos. La clave permanece en el atributo privado y se incorpora al header al enviar; repr/str muestran api_key=***. Suite previa al commit: 169 passed; Ruff y formato limpios |
| A2 | **Resuelto** | `fix: make sdk tolerate invalid usage data` | tests/unit/test_sdk_usage.py reprodujo 40 fallos, con 2 controles válidos aprobados. Ambos formatos rechazan None, negativos, str, float, bool y objetos arbitrarios en ambos campos; también usage inválido/ausente. Devuelven el mismo objeto, registran warning sin valores sensibles y no encolan. Cero entero sigue válido. Un fallo de encolado no reemplaza ni el resultado ni la excepción original de fn |

La extracción y validación de modelo/tokens, el cálculo de latencia final, la construcción del evento y su encolado están dentro de una frontera que captura errores de seguimiento. La excepción de fn se relanza con `raise`, conservando el objeto original; los errores del LLM con modelo explícito siguen intentando registrar un evento error con cero tokens.

Verificación completa: **211 tests aprobados**, un warning conocido de Starlette/httpx; cobertura app+sdk **95.37%**, y SDK redondeada al **90%**, por encima del mínimo. No se añadieron dependencias ni se modificó código fuera de sdk/ y sus tests. PROGRESS conserva el contenido anterior. A1/A2 y M2/M3/M4 quedan resueltos; el resto de hallazgos continúa pendiente. No se hizo push, amend, reset, force ni se avanzó de paso.
