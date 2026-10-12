# 05 · Backend Schema — TokenLedger

## Entidades
- **events**: una llamada a un LLM (qué modelo, cuántos tokens, cuánto costó, a qué función y cliente pertenece).
- **prices**: precio por millón de tokens de un modelo, con fecha de vigencia.

No hay tablas de usuarios en v0.1.

## Tabla `events`
| Campo | Tipo | Requerido | Default | Notas |
|---|---|---|---|---|
| id | uuid | sí | `gen_random_uuid()` | PK |
| created_at | timestamptz | sí | `now()` | UTC; lo fija el servidor, el cliente no lo envía |
| provider | text | sí | — | `anthropic` o `openai` |
| model | text | sí | — | 1 a 128 caracteres |
| input_tokens | integer | sí | — | ≥ 0 |
| output_tokens | integer | sí | — | ≥ 0 |
| cost_usd | numeric(14,8) | sí | — | ≥ 0; calculado en el servidor |
| latency_ms | integer | no | NULL | ≥ 0 |
| feature | text | sí | — | 1 a 64 caracteres, sin espacios al borde |
| customer | text | no | NULL | hasta 128 caracteres; usar IDs opacos |
| status | text | sí | `'ok'` | `ok` o `error` |

**Restricciones CHECK:** `provider IN ('anthropic','openai')`, `status IN ('ok','error')`, tokens ≥ 0, `latency_ms >= 0`, `cost_usd >= 0`.

**Índices** (cubren la necesidad de "índice en feature y customer" del SPEC):
- `ix_events_feature_created` en `(feature, created_at)`
- `ix_events_customer_created` en `(customer, created_at)`
- `ix_events_created` en `(created_at)`

## Tabla `prices`
| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| id | integer identity | sí | PK |
| provider | text | sí | mismo CHECK que events |
| model | text | sí | |
| input_per_mtok_usd | numeric(14,6) | sí | ≥ 0 |
| output_per_mtok_usd | numeric(14,6) | sí | ≥ 0 |
| effective_from | date | sí | |

**Único:** `(provider, model, effective_from)`. **Índice:** `(provider, model, effective_from DESC)` para buscar el precio vigente.

## Relaciones
No hay claves foráneas. `events` y `prices` se relacionan **lógicamente** por `(provider, model)` al momento de calcular el costo. Decisión consciente: el evento guarda su `cost_usd` ya calculado, así que un cambio futuro de precios **no reescribe el historial**.

## Propiedad por usuario
No aplica en v0.1 (un despliegue = un dueño). En v0.2 se añadiría `project_id` o `team_id` a `events` y una tabla `api_keys`.

## Flujo de autenticación
Sin registro ni sesiones. Cada petición lleva `X-API-Key`; el servidor la compara en tiempo constante con la variable de entorno `API_KEY`.

## Reglas de autorización
| Recurso | Lectura | Creación | Actualización | Borrado |
|---|---|---|---|---|
| events | con API key (vía `/v1/costs`) | con API key | no existe | no existe en la API |
| prices | no expuesto por API | solo por el script de seed | solo por el script de seed | manual en BD |
| /health | público | — | — | — |

## Validación de datos
- Tokens enteros ≥ 0; `feature` obligatorio; `provider` limitado a los permitidos.
- Si el par `(provider, model)` no tiene precio vigente → error 422 `unknown_model_price`.
- `group_by` ∈ {feature, customer, model}; `from` ≤ `to`; fechas en formato `YYYY-MM-DD`.
- Agrupación y fechas: eventos con customer NULL se agrupan bajo la clave 'unassigned' (COALESCE); 'from' es inclusivo desde 00:00 UTC y 'to' cubre el día completo (created_at < to + 1 día).
- La API ignora cualquier `cost_usd`, `id` o `created_at` que envíe el cliente (los rechaza con 422 si se incluyen, para evitar confusión).

## Ejemplo verificable
Con un precio de ejemplo (entrada 3.00, salida 15.00 USD/Mtok), 1 000 tokens de entrada y 500 de salida:
`cost_usd = 1000/1 000 000 × 3.00 + 500/1 000 000 × 15.00 = 0.003 + 0.0075 = 0.01050000`

## Retención y borrado
- v0.1: se conservan todos los eventos indefinidamente; sin PII por diseño (no hay prompts ni respuestas).
- Borrado manual con SQL si hace falta (documentado en `docs/DEPLOY.md`).
- v0.2 (backlog): retención configurable y tablas de resumen diarias.

## Migraciones y datos iniciales
- **Alembic:** una migración inicial crea `events` y `prices` con constraints e índices. Cada cambio posterior es una migración nueva y revisable.
- **Seed de precios:** `prices.seed.yaml` → `app/db/seed.py` (idempotente: no duplica filas). Los valores del archivo son de ejemplo y el humano los verifica en las páginas oficiales.
- **Seed de demo:** `scripts/seed_demo.py` genera ~300 eventos sintéticos para el dashboard.
