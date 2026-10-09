# 06 · Implementation Plan — TokenLedger

Este documento organiza el trabajo en **hitos**. Los prompts exactos para el agente están en `PLAN.md` (pasos 0 a 14); la columna "Paso" indica cuál usar.

**Orden de autoridad:** `SPEC.md` manda sobre estos documentos; estos desarrollan el detalle. Si algo contradice al SPEC, se detiene el trabajo y se decide con el humano.

## Hito 1 · Preparación del proyecto (≈ 3.5 h)
| Tarea | Responsable | Entradas | Salida | Definición de terminado | Depende de | Paso |
|---|---|---|---|---|---|---|
| Entorno y repo | Humano | Herramientas instaladas | Repo con SPEC, docs, CLAUDE.md y skills | `git log` muestra el primer commit; el agente lee el SPEC | — | 0 |
| Esqueleto y `/health` | Agente | SPEC §8-9 | Estructura + endpoint + test | pytest y ruff en verde | Paso 0 | 1 |
| Docker y configuración | Agente | TRD | Compose con API y Postgres | `docker compose up` y `/health` ok | Paso 1 | 2 |

## Hito 2 · Datos (≈ 5 h)
| Tarea | Responsable | Entradas | Salida | Definición de terminado | Depende de | Paso |
|---|---|---|---|---|---|---|
| Modelos y migración | Agente | `05-BACKEND-SCHEMA.md` | Modelos + migración Alembic | `alembic upgrade head` y tests de inserción | Paso 2 | 3 |
| Precios y calculadora | Agente | Schema, SPEC RF2 | Seed + CostCalculator (Strategy) | Ejemplo 0.01050000 verificado en test | Paso 3 | 4 |
| Repositorios | Agente | Schema | Event/Price repositories | Agregaciones probadas por feature, customer y model | Paso 3-4 | 5 |

La autenticación se implementa junto con la ingesta (Hito 3), porque no hay usuarios que modelar en v0.1.

## Hito 3 · Recorrido central: registrar y consultar (≈ 5 h)
| Tarea | Responsable | Entradas | Salida | Definición de terminado | Depende de | Paso |
|---|---|---|---|---|---|---|
| Ingesta + API key | Agente | SPEC §6, PRD criterios 1-3 | `POST /v1/events` | Tests: 201, 401, 422 (modelo, tokens) | Paso 5 | 6 |
| Reportes | Agente | SPEC §6, PRD criterio 4 | `GET /v1/costs` | Tests por dimensión, fechas y orden | Paso 6 | 7 |
| SDK | Agente | SPEC §7, PRD criterios 5-6 | `tl.track(...)` | Tests: éxito, red caída, error del LLM, ambos formatos de `usage` | Paso 6 | 9 |

## Hito 4 · Funciones secundarias (≈ 2.5 h)
| Tarea | Responsable | Entradas | Salida | Definición de terminado | Depende de | Paso |
|---|---|---|---|---|---|---|
| Dashboard | Agente | `03-APP-FLOW.md`, `04-UI-UX-BRIEF.md` | App Streamlit | Muestra datos, estado vacío y error | Paso 7 | 10 |
| Datos de demo | Agente | PRD F6 | `scripts/seed_demo.py` | ~300 eventos; dashboard cuenta una historia | Paso 9-10 | 11 |

## Hito 5 · Calidad (≈ 3 h)
| Tarea | Responsable | Entradas | Salida | Definición de terminado | Depende de | Paso |
|---|---|---|---|---|---|---|
| CI | Agente | TRD | GitHub Actions | Verde con ruff, formato, pytest y cobertura ≥ 80% | Paso 7 (puede hacerse antes) | 8 |
| Revisión de accesibilidad y contraste | Humano | UI Brief | Lista comprobada | Contraste ≥ 4.5:1 y etiquetas en gráficos | Paso 10 | — |
| Medición de rendimiento | Humano + agente | PRD metas | Cifras reales | p95 y tiempo de consulta medidos con 100 000 eventos | Paso 11 | — |
| Revisión de seguridad | Humano | TRD §Seguridad | Checklist | Sin secretos en el repo; `.env` ignorado; API key obligatoria | Paso 6 | — |

## Hito 6 · Lanzamiento (≈ 4 h)
| Tarea | Responsable | Entradas | Salida | Definición de terminado | Depende de | Paso |
|---|---|---|---|---|---|---|
| Despliegue | Humano (con guía del agente) | `docs/DEPLOY.md` | URL pública con datos de demo | `/health` y dashboard accesibles | Hito 5 | 12 |
| README y decisiones | Agente + humano | TRD, PRD | README con diagrama, `DECISIONS.md` | Un tercero levanta el proyecto solo con el README | Paso 12 | 13 |
| Cierre | Humano | SPEC §11 | Tag `v0.1.0` | Criterios de aceptación revisados uno por uno | Paso 13 | 14 |

**Plan de pruebas de lanzamiento:** ejecutar los 7 criterios de aceptación del PRD en el entorno desplegado.
**Reversión:** redeploy de la imagen anterior; si una migración falla, restaurar desde el respaldo de la plataforma.
**Monitoreo mínimo:** `/health` consultado por un monitor gratuito de disponibilidad y revisión de logs de la plataforma.

## Antes de avanzar de un hito al siguiente
1. Ejecuta la app y comprueba los criterios de aceptación del PRD que corresponden.
2. `ruff` y `pytest` en verde.
3. Registra cualquier problema sin resolver en `DECISIONS.md` (sección "Pendientes").
4. Commit y `/clear`.

## Riesgos principales
| Riesgo | Mitigación |
|---|---|
| El agente se sale del alcance | `CLAUDE.md`, un paso por sesión, `pre-commit-review` |
| Precios del seed desactualizados | Marcados como ejemplo; verificación humana en páginas oficiales |
| Dashboard público expone datos | Despliegue público solo con datos sintéticos |
| API pública sin límite de peticiones | API key obligatoria; rate limiting en backlog v0.2 |
| Pérdida de motivación por alcance | Respetar "fuera de alcance"; v0.1 se cierra antes de v0.2 |
