# 01 · Product Requirements Document (PRD) — TokenLedger

## Nombre e idea en una frase
**TokenLedger**: registra cuánto cuesta cada llamada a un LLM y responde "¿qué función y qué cliente de mi producto gastan más?".

## Usuarios objetivo
- **Principal:** desarrollador o fundador técnico de una startup pequeña (1 a 10 personas) que integra APIs de LLM en su producto. Necesita saber el costo real por función y por cliente para fijar precios y detectar fugas de gasto.
- **Secundario:** persona de producto o finanzas que consulta el dashboard sin escribir código.
- **Usuario de portafolio:** reclutador o ingeniero que evalúa el proyecto en 5 minutos: necesita demo en vivo, README claro y arquitectura entendible.

## Problema y alternativa actual
- **Dolor:** la factura del proveedor llega como un total mensual; no dice qué función ni qué cliente la causó. Un solo cliente o prompt mal diseñado puede disparar el gasto sin que nadie lo vea.
- **Qué hacen hoy:** revisar el panel del proveedor, exportar a hojas de cálculo o escribir logs propios y a medio terminar. Existen herramientas comerciales de observabilidad y FinOps, pero suelen ser pesadas, de pago o generalistas para un equipo pequeño.

## Objetivo y medida de éxito
**Objetivo:** que un desarrollador pase de cero a ver su gasto por función y por cliente en **menos de 10 minutos**.

| Señal | Meta (a verificar al terminar) |
|---|---|
| Tiempo de instalación a primer dato en el dashboard | ≤ 10 min siguiendo solo el README |
| Exactitud del costo calculado | 100% de los casos de prueba coinciden con el cálculo manual |
| Latencia de `POST /v1/events` (p95, un servidor, local) | < 150 ms |
| Consulta `GET /v1/costs` sobre 100 000 eventos | < 500 ms |
| El SDK nunca rompe la app del usuario | 0 excepciones propagadas por fallos de red en los tests |

Estas metas son objetivos de diseño, no resultados. Se miden en el Hito 5 y se publican en el README solo si se midieron de verdad.

## Funcionalidades principales
| # | Funcionalidad | Beneficio para el usuario | Prioridad |
|---|---|---|---|
| F1 | Ingesta de eventos de uso (API) | Capturar cada llamada con tokens y etiquetas | Must |
| F2 | Cálculo de costo con tabla de precios en BD | Costo exacto sin precios fijos en el código | Must |
| F3 | Reporte agregado por feature, customer o model, con fechas | Responder la pregunta central | Must |
| F4 | SDK Python que nunca rompe tu código | Integrar en minutos y sin riesgo | Must |
| F5 | Dashboard de una pantalla | Ver el gasto sin escribir consultas | Should |
| F6 | Generador de datos de demostración | Demo convincente sin datos reales | Should |
| F7 | `/health` y despliegue con Docker | Operable y desplegable | Must |

## Fuera de alcance en la versión 1
Alertas y detección de anomalías, presupuestos, multiusuario y login, más de dos proveedores, OpenTelemetry, colas, caché, frontend en React, almacenamiento de prompts o respuestas (**decisión de privacidad permanente**: solo se guardan metadatos de uso).

## Historias de usuario
- Como desarrollador, quiero envolver mi llamada al LLM con una línea, para registrar su costo sin cambiar mi lógica.
- Como desarrollador, quiero que un fallo de TokenLedger nunca rompa mi aplicación, para poder confiar en él en producción.
- Como fundador, quiero ver qué cliente gasta más, para decidir si su plan es rentable.
- Como desarrollador, quiero ver qué función cuesta más, para optimizar primero la que más pesa.
- Como mantenedor, quiero actualizar los precios sin tocar código, para reflejar cambios de los proveedores.
- Como reclutador, quiero abrir una demo con datos, para entender el proyecto sin instalar nada.

## Criterios de aceptación (Dado / Cuando / Entonces)
1. **Dado** un precio de ejemplo (entrada 3.00 y salida 15.00 USD por millón de tokens), **cuando** envío un evento con 1 000 tokens de entrada y 500 de salida, **entonces** `cost_usd` es `0.01050000`.
2. **Dado** un modelo sin precio registrado, **cuando** envío un evento, **entonces** recibo 422 con un mensaje que nombra el modelo.
3. **Dado** una API key incorrecta, **cuando** llamo a cualquier endpoint salvo `/health`, **entonces** recibo 401.
4. **Dado** eventos de 3 features, **cuando** consulto `group_by=feature`, **entonces** la lista viene ordenada por costo descendente y los totales suman el total global.
5. **Dado** que la API está apagada, **cuando** mi código llama a `track(...)`, **entonces** recibo la respuesta del LLM y no hay excepción.
6. **Dado** que la llamada al LLM falla, **cuando** uso `track(...)`, **entonces** se registra un evento `status=error` y se relanza la excepción original.
7. **Dado** un repo recién clonado, **cuando** ejecuto `docker compose up`, **entonces** `/health` responde ok y el dashboard abre.

## Preguntas abiertas (decide el dueño)
1. ¿Plataforma de despliegue? (decidir en el Paso 12; verificar planes gratuitos vigentes).
2. ¿Licencia del repo? (sugerencia: MIT).
3. ¿Se publica el dashboard abiertamente? Sugerencia: **solo con datos sintéticos**, porque el dashboard v0.1 no tiene login.
4. ¿Nombre final del paquete del SDK en PyPI? (fuera de v0.1; solo instalación desde el repo).
