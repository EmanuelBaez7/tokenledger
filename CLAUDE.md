# CLAUDE.md — Reglas del proyecto TokenLedger

Lee `SPEC.md` antes de cada tarea. `SPEC.md` manda sobre cualquier suposición tuya.
Para el detalle consulta `docs/` (PRD, TRD, App Flow, UI/UX, Schema, Implementation Plan) solo cuando el paso lo requiera; si contradicen al SPEC, pregunta.

## Cómo trabajar
- Haz **solo** lo que pide el paso actual. Nada más. Si ves algo fuera de alcance, anótalo al final como "sugerencia", no lo implementes.
- Si algo es ambiguo o contradice el SPEC, **pregunta antes de escribir código**.
- Escribe los tests primero (o junto con el código). No des un paso por terminado si `ruff` o `pytest` fallan.
- No agregues dependencias nuevas sin decirlo y justificarlo en una línea.
- No inventes APIs ni funciones de librerías: si no estás seguro, revisa la documentación o dilo.
- Cambios pequeños: máximo ~200 líneas por paso. Si crece, divide y avisa.

## Convenciones
- Código, nombres, comentarios y commits en **inglés**. Explicaciones al usuario en **español**.
- Tipado en todo el código (`type hints`). Dinero con `Decimal`, nunca `float`.
- Capas: `api → services → repositories → db`. Prohibido SQL fuera de `repositories/`. Prohibida lógica de negocio en `api/`.
- Commits convencionales: `feat:`, `fix:`, `test:`, `chore:`, `docs:`.
- Nunca escribir secretos en el código. Todo por variables de entorno.

## Comandos
- Instalar: `uv sync`
- Tests: `uv run pytest -q`
- Lint: `uv run ruff check . && uv run ruff format --check .`
- Levantar: `docker compose up --build`

## Al terminar cada paso, responde con
1. Qué hiciste (3 líneas máximo).
2. Archivos creados o modificados.
3. Salida de los comandos de verificación.
4. Qué NO hiciste a propósito.
5. Una sugerencia para el siguiente paso.

## Flujo de sesión
- Un paso de PLAN.md por sesión. No avances al siguiente sin que el humano verifique.
- Al empezar: lee CLAUDE.md, SPEC.md y PROGRESS.md; revisa git log y git status.
- Al terminar: actualiza PROGRESS.md (paso hecho, decisiones tomadas, pendientes) y no hagas commit; lo hace el humano.
- Toda decisión importante se escribe en un archivo del repo (docs/ o DECISIONS.md), nunca solo en el chat.