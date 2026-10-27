# Guía para agentes

- Antes de cada tarea, lee `CLAUDE.md`, `SPEC.md` y `PROGRESS.md`, en ese orden.
- Sigue `CLAUDE.md` como reglas del proyecto y formato de respuesta; `SPEC.md` es la fuente de verdad funcional.
- Inspecciona el código, `git status` y `git log` antes de modificar archivos.
- Entorno: Windows con PowerShell, Python 3.12 con uv y Docker Desktop.
- Usa el puerto 8500 para uvicorn y 8501 para Streamlit; Windows reserva 7918–8217 en este equipo.
- El agente hace commit únicamente cuando el prompt lo pide de forma explícita, con commits convencionales (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`). Nunca ejecutes push, amend, reset ni force.
- Nunca muestres el contenido ni los valores de `.env`, ni lo incluyas en staging.
- Privacidad: en documentos, informes y mensajes de commit no incluyas rutas absolutas del equipo, nombres de usuario de Windows, correos personales ni zonas horarias; usa rutas relativas al repositorio.
- Consulta el estado y los pendientes en `PROGRESS.md` antes de continuar otro paso.
