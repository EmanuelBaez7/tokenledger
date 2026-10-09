# PLAN.md — TokenLedger v0.1 (paso a paso)

## Reglas del juego (léelas una vez)
1. **Un paso = una sesión.** Al terminar un paso: verifica, haz commit, ejecuta `/clear` y empieza el siguiente. Contexto limpio = menos vueltas.
2. **No avances si la verificación falla.** Pega el error al agente y pídele que lo corrija dentro del mismo paso.
3. **Revisa antes de commitear:** pide `/pre-commit-review`. Para entender lo que se hizo: `/explain-changes`.
4. **Cada prompt asume** que `CLAUDE.md` y `SPEC.md` están en la raíz del repo.
5. Si el agente intenta hacer más de lo pedido, respóndele: "Fuera de alcance. Revierte eso y limítate al paso."
6. Tiempo estimado total: 15 a 25 horas, repartidas en 2 a 3 semanas.

---

## Paso 0 — Preparación manual (sin agente) · 1 h
- Instala: Python 3.12, `uv`, Docker Desktop, Git, GitHub CLI (`gh`) y Claude Code (o Antigravity).
- `mkdir tokenledger && cd tokenledger && git init`
- Copia aquí `SPEC.md`, `PLAN.md`, `CLAUDE.md` y la carpeta `docs/` (los 6 documentos de producto y técnica).
- Copia la carpeta `skills/` a `.claude/skills/` (queda `.claude/skills/task-tdd/SKILL.md`, etc.).
- Crea un repo en GitHub y conecta el remoto.
- Primer commit: `chore: add spec, plan and project rules`.
- Abre el agente en esa carpeta y ejecuta `/doctor` para comprobar la instalación.

**Verificación:** `git log` muestra el commit y el agente responde cuando le preguntas "¿qué dice SPEC.md sobre el alcance fuera de v0.1?".

---

## Paso 1 — Esqueleto del proyecto · 1 h
**Prompt:**
```
Usa la skill task-tdd. Implementa solo el esqueleto del proyecto según SPEC.md secciones 8 y 9.
Haz:
- pyproject.toml con uv (Python 3.12) y dependencias: fastapi, uvicorn, pydantic-settings, sqlalchemy, alembic, psycopg[binary], httpx, pytest, pytest-cov, ruff.
- Estructura de carpetas vacía con __init__.py: app/{api,services,repositories,db,core}, sdk/tokenledger, tests/{unit,integration}.
- app/main.py con FastAPI y GET /health que devuelve {"status":"ok"}.
- Un test de integración para /health usando TestClient.
- Configuración de ruff en pyproject.toml.
- .gitignore para Python y .env.example vacío de secretos.
No hagas nada más: ni base de datos, ni Docker, ni otros endpoints.
```
**Verificación:** `uv run pytest -q` pasa; `uv run ruff check .` limpio; `uv run uvicorn app.main:app` y `curl localhost:8000/health` responde ok.
**Commit:** `feat: project skeleton with health endpoint`

---

## Paso 2 — Docker Compose, Postgres y configuración · 1.5 h
**Prompt:**
```
Usa task-tdd. Implementa solo Docker y configuración.
- app/core/config.py con pydantic-settings: DATABASE_URL, API_KEY. Sin valores por defecto para API_KEY.
- Dockerfile para la API (python:3.12-slim, uv).
- docker-compose.yml con servicios db (postgres, con healthcheck y volumen) y api (depende de db saludable).
- .env.example con DATABASE_URL de ejemplo y API_KEY=change-me.
- Un test unitario que verifique que Settings falla si falta API_KEY.
No crees tablas ni modelos todavía.
```
**Verificación:** `cp .env.example .env && docker compose up --build` levanta; `curl /health` responde; tests pasan.
**Commit:** `feat: docker compose with postgres and typed settings`

---

## Paso 3 — Modelos de base de datos y migración · 1.5 h
**Prompt:**
```
Usa task-tdd. Implementa solo el acceso a datos base según SPEC.md sección 5.
- app/db/session.py: engine y sesión SQLAlchemy 2 + dependencia get_session.
- app/db/models.py: modelos Event y Price exactamente como en el SPEC (UUID, Numeric, índices en feature y customer, restricción única provider+model+effective_from).
- Alembic configurado y una primera migración generada.
- Tests de integración contra Postgres real (usa la base del compose o una de test) que verifiquen que se puede insertar y leer un Event y un Price.
No crees repositories ni endpoints.
```
**Verificación:** `docker compose run --rm api alembic upgrade head` funciona; tests pasan.
**Commit:** `feat: db models and initial migration`

---

## Paso 4 — Precios y calculadora de costos (el corazón) · 2 h
**Prompt:**
```
Usa task-tdd. Implementa solo el cálculo de costos según SPEC.md RF2 y secciones 5 y 8.
- prices.seed.yaml con 2 modelos de ejemplo por proveedor (anthropic y openai). Pon VALORES DE EJEMPLO y un comentario "verificar en la página oficial del proveedor". No inventes que sean reales.
- Script app/db/seed.py que carga el YAML a la tabla prices (idempotente).
- app/services/cost_calculator.py con un Protocol/clase base CostStrategy y una estrategia por proveedor (patrón Strategy), usando Decimal.
- Fórmula: (input_tokens/1_000_000)*input_per_mtok + (output_tokens/1_000_000)*output_per_mtok, redondeado a 8 decimales.
- Tests unitarios (sin BD): costo correcto, cero tokens = cero costo, modelo desconocido lanza un error de dominio claro, nunca devuelve float.
```
**Verificación:** tests de cálculo pasan; revisa a mano un caso con calculadora.
**Commit:** `feat: price seeding and cost calculator with strategy pattern`

---

## Paso 5 — Repositorios · 1.5 h
**Prompt:**
```
Usa task-tdd. Implementa solo la capa repositories según SPEC.md sección 8.
- EventRepository: add(event), aggregate(group_by, date_from, date_to) que devuelve key, total_cost_usd, total_input_tokens, total_output_tokens, calls ordenado por costo descendente.
- PriceRepository: get_current(provider, model, at_date) devuelve el precio vigente más reciente o None.
- Todo el SQL vive aquí. Los repositorios reciben la sesión por constructor.
- Tests de integración con datos sembrados: agregación por feature, por customer y por model, filtro de fechas, orden correcto.
No crees servicios ni endpoints.
```
**Verificación:** tests pasan.
**Commit:** `feat: event and price repositories`

---

## Paso 6 — Ingesta de eventos (POST /v1/events) · 2 h
**Prompt:**
```
Usa task-tdd. Implementa solo RF1, RF2 y la autenticación según SPEC.md sección 6.
- Dependencia de auth por header X-API-Key contra settings.API_KEY (401 si falta o es incorrecta). /health queda sin auth.
- Esquemas Pydantic de entrada y salida con extra="forbid": el cliente NO envía id, created_at ni cost_usd (si los incluye, 422). Validaciones de longitud según docs/05-BACKEND-SCHEMA.md.
- EventService que busca el precio vigente, calcula el costo y guarda por EventRepository.
- POST /v1/events -> 201. Modelo sin precio -> 422 con mensaje claro. Tokens negativos -> 422.
- Inyección de dependencias con Depends. Cero lógica de negocio en la ruta.
- Tests de integración: caso feliz con costo verificado a mano, 401, 422 por modelo desconocido, 422 por tokens negativos.
```
**Verificación:** tests pasan; prueba con `curl -X POST` y mira la fila en Postgres.
**Commit:** `feat: event ingestion endpoint with api key auth`

---

## Paso 7 — Reportes (GET /v1/costs) · 1.5 h
**Prompt:**
```
Usa task-tdd. Implementa solo RF3 según SPEC.md sección 6.
- ReportService que llama a EventRepository.aggregate.
- GET /v1/costs?group_by=feature|customer|model&from=&to= con auth.
- group_by inválido -> 422. Rango de fechas inválido (from > to) -> 422.
- Tests de integración: agrupa por cada dimensión, filtra por fechas, orden descendente, 401 sin API key, respuesta vacía válida cuando no hay datos.
```
**Verificación:** tests pasan; inserta 3 eventos con curl y comprueba el agregado a mano.
**Commit:** `feat: cost reporting endpoint`

---

## Paso 8 — CI en GitHub Actions · 1 h
**Prompt:**
```
Usa task-tdd. Implementa solo CI según SPEC.md sección 10.
- .github/workflows/ci.yml: en push y pull_request, con servicio Postgres, instala con uv, corre ruff check, ruff format --check y pytest con cobertura (falla si app/ queda por debajo de 80%).
- Cachea dependencias de uv.
- Agrega un badge de CI al README.md (créalo con un título y una línea de descripción por ahora).
```
**Verificación:** haz push y confirma que la acción queda en verde en GitHub.
**Commit:** `ci: lint, tests and coverage gate`

---

## Paso 9 — SDK · 2 h
**Prompt:**
```
Usa task-tdd. Implementa solo el SDK según SPEC.md sección 7 y RF4.
- sdk/tokenledger/client.py con la clase TokenLedger(base_url, api_key) y el método track(fn, provider, feature, customer=None).
- Mide latencia, extrae tokens de la respuesta (Anthropic: usage.input_tokens/output_tokens; OpenAI: usage.prompt_tokens/completion_tokens), envía el evento en un hilo aparte con httpx y timeout corto.
- Si el envío falla: warning en logs y NUNCA lanzar excepción al usuario. Siempre devolver la respuesta original.
- Si fn lanza excepción: registrar evento status=error con tokens 0 y volver a lanzar la excepción original.
- Tests unitarios con objetos falsos (sin llamar a ninguna API real) y httpx mockeado: éxito, fallo de red, excepción del LLM, ambos formatos de usage.
- Un test de integración que envíe un evento real al servidor y lo encuentre en /v1/costs.
```
**Verificación:** tests pasan. Apaga la API a mano y confirma que el código del usuario sigue funcionando.
**Commit:** `feat: python sdk with non-blocking tracking`

---

## Paso 10 — Dashboard · 1.5 h
**Prompt:**
```
Usa task-tdd. Implementa solo RF5 según SPEC.md.
- dashboard/app.py en Streamlit: selector de rango de fechas, gráfico de barras de costo por feature, gráfico de barras por customer y tabla con los totales.
- Consume la API con httpx usando API_BASE_URL y API_KEY por variables de entorno.
- Agrega el servicio dashboard a docker-compose.yml.
- Extrae la lógica de obtención/transformación de datos a una función pura con un test unitario. La UI en sí no necesita tests.
```
**Verificación:** `docker compose up` y abre el dashboard; con datos vacíos muestra un mensaje amable, no un error.
**Commit:** `feat: streamlit dashboard`

---

## Paso 11 — Datos de demostración · 45 min
**Prompt:**
```
Usa task-tdd. Crea scripts/seed_demo.py que, usando el SDK o la API, genere unos 300 eventos aleatorios realistas en los últimos 14 días: 4 features, 5 customers, 3 modelos, tokens variables, con una función claramente "cara" y un cliente que gasta mucho más, para que el dashboard cuente una historia. Debe poder ejecutarse con un comando documentado en el README.
```
**Verificación:** ejecuta el script y mira el dashboard.
**Commit:** `chore: demo data generator`

---

## Paso 12 — Despliegue · 2 h
**Prompt:**
```
Usa task-tdd. Prepara el despliegue sin ejecutar nada en producción.
- Revisa que el Dockerfile sea apto para producción (usuario no root, sin dependencias de desarrollo, comando correcto) y que las migraciones se ejecuten al iniciar de forma segura.
- Escribe docs/DEPLOY.md con los pasos para una plataforma con soporte de Docker y Postgres gestionado. Indica en el documento que el humano debe verificar los pasos en la documentación actual de la plataforma elegida.
- No agregues credenciales ni archivos .env reales.
```
**Verificación (tú, manual):** despliega siguiendo el doc, crea las variables de entorno en la plataforma, corre el seed de demo y guarda la URL.
**Commit:** `docs: deployment guide and production-ready dockerfile`

---

## Paso 13 — README y decisiones · 1.5 h
**Prompt:**
```
Usa la skill explain-changes y luego task-tdd para documentación.
- README.md: problema que resuelve, GIF o captura del dashboard (déjame un marcador), arranque en 3 comandos, ejemplo de uso del SDK, diagrama de arquitectura en Mermaid (SDK -> API -> Services -> Repositories -> Postgres, y Dashboard -> API), tabla de endpoints, cómo correr tests, decisiones de alcance y roadmap v0.2.
- DECISIONS.md: al menos 5 decisiones reales tomadas en este proyecto (monolito vs microservicios, Decimal vs float, precios en BD vs código, SDK que nunca rompe, Repository pattern), con formato: contexto, decisión, alternativa descartada, consecuencia.
No inventes métricas que no existan.
```
**Verificación:** un amigo debería poder levantar el proyecto solo con el README.
**Commit:** `docs: readme with architecture diagram and decision log`

---

## Paso 14 — Cierre y retrospectiva · 30 min
- Revisa los criterios de aceptación de SPEC.md sección 11, uno por uno.
- Etiqueta el release: `git tag v0.1.0 && git push --tags`.
- Anota en `DECISIONS.md` qué te costó más y qué harías distinto.
- Backlog v0.2 (no empezar hasta cerrar v0.1): alertas de anomalías, presupuestos por customer, OpenTelemetry, trazas por request, más proveedores.

---

# Skills recomendadas

**Ya incluidas en el kit** (cópialas a `.claude/skills/`):
| Skill | Para qué |
|---|---|
| `task-tdd` | Obliga a trabajar con tests primero y alcance mínimo en cada paso. |
| `pre-commit-review` | Revisa el diff contra el SPEC antes de cada commit. |
| `explain-changes` | Te explica lo construido en español para que aprendas, no solo copies. |

**Del propio Claude Code:** `/doctor` (revisa tu instalación) y `skill-creator` si luego quieres crear más skills.

**Opcional:** un skill o plugin tipo "code simplifier" para limpiar código ya funcional. Instálalo solo desde el repositorio oficial de Anthropic o de una fuente que hayas revisado: una skill es texto que el agente obedece, así que léela antes de instalarla.

**Si usas Antigravity:** las skills siguen el estándar abierto Agent Skills, pero la ruta y el nombre del archivo de reglas pueden cambiar. Revisa su documentación y copia el contenido de `CLAUDE.md` al archivo de reglas del proyecto que use.
