# 04 · UI y UX Design Brief — TokenLedger

## Audiencia y tono
Desarrolladores y fundadores técnicos. Tres adjetivos: **claro, sobrio, confiable**. Datos primero, adornos después.

## Referencias
Paneles de observabilidad y facturación de proveedores de nube (tomar: jerarquía clara, una cifra principal grande, tablas legibles; evitar: exceso de widgets y colores).

## Paleta (se aplica con `.streamlit/config.toml`)
| Rol | Color |
|---|---|
| Primario | `#2563EB` |
| Acento (énfasis en el gasto más alto) | `#F59E0B` |
| Fondo | `#FFFFFF` (claro) o `#0F172A` (oscuro) |
| Texto | `#0F172A` / `#E2E8F0` |
| Éxito | `#16A34A` |
| Error | `#DC2626` |
Verificar contraste mínimo 4.5:1 en texto con una herramienta de contraste antes de cerrar.

## Tipografía
La del tema por defecto de Streamlit (sans-serif). Jerarquía: título de página, subtítulo por sección, cifras destacadas con `st.metric`, tablas en tamaño normal.

## Componentes
`st.metric` para el gasto total y el top feature/customer, `st.date_input` para el rango, gráficos de barras horizontales (ordenados de mayor a menor), `st.dataframe` para la tabla, `st.error/st.info` para estados.

## Reglas de diseño
- Una columna en móvil; dos columnas (feature y customer lado a lado) en escritorio.
- Orden vertical: filtros → métricas → gráficos → tabla.
- Barras horizontales con etiqueta y valor visibles; el valor más alto en color de acento.
- Importes con 2 a 4 decimales según el tamaño (los costos por llamada son muy pequeños).

## Notas de pantalla (Dashboard)
1. **Cabecera:** nombre, rango de fechas.
2. **Métricas:** gasto total, nº de llamadas, costo medio por llamada, feature más cara.
3. **Gasto por feature:** gráfico de barras + tabla.
4. **Gasto por customer:** gráfico de barras + tabla.
5. **Pie:** versión y enlace al repo.

## Accesibilidad
- No depender solo del color: cada barra lleva etiqueta y número.
- Tablas con encabezados claros como alternativa textual a los gráficos.
- Textos de error comprensibles, sin códigos solos.
- Navegable con teclado (lo que ofrece Streamlit por defecto).

## Estados de interacción
Carga: spinner con texto. Vacío: mensaje guía. Error: mensaje con acción de reintento. Éxito: datos visibles sin mensajes de confirmación.

## Assets necesarios
Logo simple en texto (sin imagen en v0.1), una captura del dashboard con datos de demo para el README, diagrama Mermaid de arquitectura.
