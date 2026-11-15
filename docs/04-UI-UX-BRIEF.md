# 04 · Dashboard v2: UI y UX — Paso 10.1

Estado **interfaz revisada y pulida** en `feature/dashboard-v2`. El pulido de la rejilla, la demo y el contraste se registra en `refactor: align kpi cards and simplify demo story`. El commit 6 queda pendiente.

## Propósito y alcance

Analítica financiera para desarrolladores y fundadores: entender cuánto gastan, qué concentra el gasto y cómo cambió frente al periodo anterior. Una pantalla con densidad útil, alineación izquierda y lenguaje preciso. TokenLedger será una marca de texto, sin imágenes, emojis, degradados ni sombras decorativas.

- Entran: fuentes API/demo, periodos, comparación, cinco KPI, tendencia diaria, distribución por feature/customer/modelo, tablas, observaciones deterministas, CSV y Excel.
- Quedan fuera: presupuesto y proyección mensual, filtros cruzados y sus parámetros API, alertas, IA, persistencia de preferencias en servidor, login, React y nuevas librerías de gráficos. Los opcionales no se aprueban en esta propuesta.
- Las pestañas organizan detalles dentro de la misma pantalla; no añaden navegación ni rutas. El flujo v1 sigue vigente mientras se implementa este refinamiento de RF5.

## Tokens de diseño

Una sola familia de marca, azul, con un tono por tema. Claro por defecto y oscuro desde el menú nativo de Streamlit. Streamlit 1.65.0 actualiza `color-scheme` en el navegador, por lo que las tarjetas, la banda y las tablas usan `light-dark()` para seguirlo. Altair hereda los colores del tema activo. La tendencia usa los valores nativos de Streamlit con `theme=None` para que ejes y título adopten el color principal, con mayor contraste que el gris de `theme="streamlit"`. Los colores de las series, las etiquetas y el pico se resuelven desde la configuración de Streamlit. El cambio de tema es inmediato. Aplicar actualiza el periodo, la comparación y la fuente.

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| Fondo | `#F8FAFC` | `#0B1220` | Lienzo y separación |
| Superficie | `#FFFFFF` | `#111C2E` | Controles, paneles y tablas |
| Texto principal | `#0F172A` | `#E5EAF3` | Títulos, importes y etiquetas |
| Texto secundario | `#475569` | `#9BA9BD` | Ayudas, ejes y metadatos |
| Borde de panel / divisor | `#CBD5E1` | `#465874` | Línea de 1 px, sin sombras |
| Borde de control | `#64748B` | `#7C8CA5` | Contraste contra superficie 4.76:1 / 5.00:1 |
| Marca / foco | `#1D4ED8` | `#93B4FF` | Acciones, selección y series |
| Acento | `#B45309` | `#B78730` | Mayor gasto y marca de pico |
| Disminución de costo | `#166534` | `#86EFAC` | Variación con flecha y signo |
| Aumento de costo | `#B91C1C` | `#FCA5A5` | Variación con flecha y signo |

Espaciado: 8, 16, 24, 32 y 48 px. Radios: 4 px en controles y 8 px en paneles. Foco visible de 2 px con separación de 2 px: contraste 6.41:1 contra fondo claro y 8.31:1 contra superficie oscura. Bordes de control y foco requieren al menos 3:1. Botones rellenos: blanco sobre #1D4ED8 en tema claro; #0B1220 sobre #93B4FF en oscuro. Nunca blanco sobre ámbar. En gráficos, marcas sin bordes decorativos y cuadrícula neutra fina; estados operativos con texto y superficies neutras, reservando verde/rojo a variaciones.

Contraste medido en el navegador con luminancia sRGB y el fondo efectivo, por elemento y tema.

| Elemento | Claro | Oscuro |
|---|---:|---:|
| Texto principal sobre superficie | 17.85:1 | 14.15:1 |
| Etiqueta secundaria de KPI | 7.58:1 | 7.16:1 |
| Ayudas de cabecera y barra lateral | 7.48–7.66:1 | 8.23–8.78:1 |
| Ejes y título del eje | 17.06:1 | 15.51:1 |
| Texto secundario de gráficos, incluida la etiqueta «Pico» | 7.24:1 | 7.85:1 |
| Variación de costo positiva / negativa en KPI | 6.47 / 7.13:1 | 9.00 / 12.17:1 |
| Acento ámbar de barras y marcador sobre el gráfico | 4.80:1 | 5.81:1 |
| Separadores de la fecha personalizada | 4.63:1 | 6.11:1 |
| Texto de ejemplo de búsqueda | 4.70:1 | 5.85:1 |
| Pestaña activa y etiqueta «Actual» | 6.41:1 | 9.11:1 |
| Fuente bloqueada, etiqueta / valor | 17.85 / 17.06:1 | 14.15 / 15.51:1 |
| Valores de selectores habilitados | 17.06–17.85:1 | 14.15–15.51:1 |
| Pulgar del interruptor apagado | 3.62:1 | 3.83:1 |
| Borde del interruptor enfocado en claro | 3.95:1 | 5.00:1 |
| Borde del botón Exportar | 4.55:1 | 5.48:1 |
| Foco del interruptor con teclado | 5.57:1 | 8.31:1 |

Las ayudas comparten tamaño de 14 px y heredan el color del tema con una atenuación del 26%. La etiqueta y el valor de la fuente bloqueada usan el color principal. La medición incluye el fondo efectivo y la opacidad de cada elemento en los estados estables. El triángulo del pico usa opacidad completa. El interruptor usa un borde visible y el pulgar se distingue en ambos estados. El mínimo de 4.5:1 para texto sigue el [criterio de contraste de WCAG](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

## Tipografía y números

**IBM Plex Sans** en interfaz, títulos, importes, porcentajes y contadores; **IBM Plex Mono** solo en identificadores de feature, customer y modelo. La misma familia Sans mantiene continuidad entre etiquetas y cifras; Mono distingue los identificadores del lenguaje de la interfaz. Familias y licencia: [IBM Plex, OFL](https://github.com/IBM/plex). Servir WOFF2 oficiales locales, sin modificar, en pesos estáticos 400/500/600, subconjunto Latin1 y licencia OFL. Comprobación binaria de cmap, hmtx, OS/2 y GSUB: los diez dígitos Sans tienen avance nativo de 600 unidades en los tres pesos; no existe etiqueta OpenType tnum. El dueño aprobó conservar estas cifras tabulares y activar tabular-nums en CSS. Latin1 incluye $, − (U+2212) y á é í ó ú ü ñ ¿ ¡; faltan ↑ y ↓. Los subconjuntos oficiales Sans Pi, mismos pesos y familia, sí incluyen ambas flechas: se servirán solo para U+2191/U+2193, sin recurrir a otra familia ni descargar fuentes al abrir la app.

Fallback: `system-ui, sans-serif` y `ui-monospace, monospace`. Activar `font-variant-numeric: tabular-nums lining-nums` en importes y contadores. Base 16/24 px, ayudas 14/24, secciones 24/32 y título/KPI 32/40; pesos 400, 500 y 600. No reducir la letra para encajar etiquetas largas.

USD en toda la pantalla: miles con coma y decimal con punto. Totales y etiquetas: `$1,234.5678`; costo por llamada: `$0.000123`; detalle y tooltip monetario: ocho decimales; porcentajes: uno. Importes, porcentajes, llamadas y tokens alineados a la derecha. Los valores subyacentes mantienen Decimal; float solo al dibujar gráficos.

## Distribución y controles

```text
Filtros (256 px)        TokenLedger / Costos de LLM       Exportar
Fuente y periodo       Periodo activo y anterior        Tema: menú nativo
Comparación            Datos sintéticos de demostración (solo demo)
Aplicar                Gasto | Llamadas | Costo/llamada | Feature | Cliente
                       Tendencia diaria + acceso a su tabla
                       Por feature | Por customer | Por modelo
                       Detalle: pestañas + búsqueda + CSV
                       Observaciones
```

En escritorio, contenido fluido `wide`, márgenes de 32 px y separación de 24 px. Tarjetas KPI en rejilla CSS adaptable al espacio disponible. Cada tarjeta usa una rejilla de tres filas. La etiqueta reserva 48 px y muestra hasta dos líneas. Los valores comparten la línea base de la primera línea y los identificadores o importes largos pueden ocupar más líneas sin desplazar su inicio. Se verificó con datos largos a 1440, 1024 y 390 px. Las distribuciones aceptan el apilado nativo de columnas de Streamlit; no hay ruptura especial a 768 px. En móvil, filtros plegables, exportación debajo del título y tablas con desplazamiento horizontal contenido, sin desplazar toda la página. Validar 1440, 1024 y 390 px y zoom 200%.

Las distribuciones tienen un alto calculado por número de filas y líneas por etiqueta. La prueba de renderizado comprueba el paso para etiquetas de una y dos líneas. En pantalla, a 1440, 1024 y 390 px en ambos temas, el modelo de etiqueta larga ocupa dos líneas y queda un espacio de 16 px antes de «Detalle».

Sidebar: fuente «API / Demo», periodos «7 días / 14 días / 30 días / Personalizado» (14 por defecto), dos fechas si es personalizado, comparación activada por defecto y botón «Aplicar». Cambiar un control no cambia los datos publicados hasta aplicar; estado conservado solo en la sesión. Cambiar de fuente exige recarga, sin mezclar datos. Fechas inclusivas y sin futuro; avisar que hoy es parcial.

Cabecera: título, periodo y fuente visibles, acción «Exportar» con libro completo y CSV de cada tabla. Etiquetas de negocio en español; conservar los identificadores originales de feature/customer/modelo. Cabecera, eje y tooltips usan fechas cortas en español, como «17 oct». Si el rango de cabecera cruza de año, ambos extremos incluyen el año. La tabla diaria muestra «17 oct 2026» y permite buscar por la fecha visible. CSV y Excel conservan el formato ISO. No mostrar claves ni detalles internos de conexión.

## Indicadores y comparación

| KPI | Valor | Contexto comparable |
|---|---|---|
| Gasto total | Suma exacta de USD | Flecha, signo, variación porcentual y gasto anterior |
| Llamadas | Todos los eventos, incluidos errores | Cambio porcentual neutro, sin juicio de costo |
| Costo medio por llamada | Gasto / llamadas | Cambio del promedio ponderado |
| Feature más cara | Nombre y gasto | Participación en el gasto del periodo, sin comparar identidades |
| Cliente más caro | Nombre y gasto | Participación en el gasto del periodo, con el mismo formato que la feature |

Para N días inclusivos, periodo anterior = N días inmediatamente anteriores al inicio. Variación = `(actual - anterior) / anterior * 100`. Con gasto anterior cero y gasto actual positivo se muestra «Sin base comparable». Si ambos son cero, la variación es 0%. El costo medio requiere llamadas. Al desactivar la comparación se ocultan las variaciones. La feature y el cliente líderes muestran su participación actual. Las comparaciones numéricas salen de la serie diaria. Empates de líder: clave en orden lexicográfico.

Respetar el intervalo admitido por la API (2000-01-01 a 2100-12-31). Si comparación o historial previo salen de él, informar «Historial insuficiente» sin consultar fechas inválidas ni fabricar valores comparables.

Una subida de costo muestra `↑ +12.3%` y rojo; una bajada `↓ -12.3%` y verde; igualdad `0.0%` neutro. Flecha y signo son texto, no emojis ni información transmitida solo por color. No interpretar más llamadas como algo malo.

## Gráficos, tablas y observaciones

- Tendencia: línea azul de costo diario, eje monetario desde cero, fechas ascendentes y días sin eventos completados con cero. La línea actual termina con «Actual». Con comparación disponible y activa, la línea neutra discontinua se alinea por posición del día y termina con «Periodo anterior». El tooltip conserva ambas fechas reales. La cuadrícula horizontal es tenue y se omite la vertical. Cada pico marcado lleva un triángulo de acento y la etiqueta «Pico».
- Para marcar un pico, el gasto diario debe superar estrictamente 1,5 veces la media positiva de los siete días anteriores. El exceso sobre esa media debe alcanzar al menos el 5% del gasto del periodo seleccionado. Se marcan hasta tres días por exceso descendente, con fecha ascendente en empates. Se consultan siete días adicionales de historial y solo se rellenan ceros tras respuestas correctas. Una media cero o un historial incompleto impiden marcar el día. La tabla diaria conserva la media de referencia y muestra «Sí» en la columna Pico solo para los días marcados.
- Tres barras horizontales: dimensiones feature, customer y modelo, costo descendente, mismo cero y etiquetas directas con nombre, importe y % del gasto total del periodo. Destacar únicamente el líder con acento. Nunca depender del hover para leer la cifra. Etiquetas largas se envuelven y el nombre completo permanece en tabla.
- Pestañas «Por feature», «Por customer», «Por modelo» y «Tendencia diaria». Cada gráfico tiene su tabla equivalente identificada. Columnas de dimensión: nombre, costo, % del total, llamadas, costo por llamada, tokens entrada/salida; porcentaje con barra de proporción y número. Tablas HTML semánticas, caption y encabezados con scope; controles nativos de búsqueda, columna de orden y dirección. Orden inicial por costo; fechas ascendentes en tendencia. Orden numérico real y búsqueda literal sin distinguir mayúsculas, sin interpretar expresiones regulares.
- La búsqueda solo filtra filas de la tabla; no cambia KPI, denominadores, gráficos ni observaciones. Dibujar como máximo 100 filas y avisar «Mostrando 100 de N» cuando corresponda; N es el número de coincidencias de búsqueda. El CSV exporta todas las coincidencias, sin límite de 100, con el orden activo. Cada tabla termina con «Total del periodo (incluye filas no visibles)», calculado sobre todas las filas originales: costo exacto igual al KPI de gasto total. Regla simple encima y doble debajo de esa fila, único distintivo visual. No hacer pasar el total del periodo por subtotal de búsqueda. El libro completo exporta todo el periodo, sin búsqueda, con aviso explícito en el menú.
- Hasta tres observaciones calculadas describen la concentración de la feature y el cliente líderes y el exceso del mayor pico sobre su media previa. Las participaciones se calculan sobre el gasto exacto del periodo. Con gasto cero se informa que no hubo gasto. Si ningún día cumple los umbrales, se indica en las observaciones.

## Estados y accesibilidad

| Estado | Comportamiento |
|---|---|
| Carga | Esqueletos de geometría estable con texto «Consultando costos…»; decorativos ocultos a lectores de pantalla. Respetar movimiento reducido y bloquear exportaciones hasta terminar. |
| Demo | Banda persistente «Datos sintéticos de demostración» y fuente visible también durante carga, error y vacío. Nunca activarlo silenciosamente por fallo de API. |
| Base sin eventos | Ayuda con `uv run python -m scripts.seed_demo` en API; en demo, informar dataset vacío sin sugerir una escritura en base. |
| Rango sin eventos | «Sin gasto en este rango» y acción para ampliar/restablecer periodo; distinguirlo de ausencia global. |
| Error de API o JSON | Mensaje seguro y Reintentar; no sustituir datos por ceros ni mostrar estado vacío. Error de comparación tampoco equivale a variación cero. |
| Configuración o 401 | Explicar qué configuración revisar sin revelar valores; conservar acción de reintento. |

Orden de tabulación: filtros, aplicar, cabecera/exportación, gráficos/tablas y observaciones; encabezados semánticos y etiquetas visibles. No crear tabindex positivos ni ocultar controles nativos de teclado. Tabla textual accesible equivalente a cada gráfico; etiquetas completas y foco visible en ambos temas. Todos los textos, incluidos secundarios, requieren al menos 4.5:1; revisar con teclado, lector de pantalla y zoom.

## Datos y límites de la API

El único cambio de API previsto es `group_by=day`: misma forma de `/v1/costs`, clave `YYYY-MM-DD` del día UTC de created_at y orden cronológico ascendente. Las otras dimensiones siguen por costo descendente; autenticación, fechas y errores unificados se conservan. Implementar test-first en repositorio, servicio y endpoint; documentar sección 6 de SPEC y schema en el segundo commit, no adelantarlo aquí.

`DASHBOARD_DATA_SOURCE=api` por defecto; selector de sesión permite demo explícita y refleja la fuente efectiva. Si faltan API_BASE_URL o API_KEY, solo se ofrece demo. Si el entorno fija DASHBOARD_DATA_SOURCE=demo, bloquear el selector en demo y ocultar API. Demo lee `dashboard/demo_data/events.json`, 400 eventos sintéticos generados de forma determinista mediante `scripts/generate_dashboard_demo.py`, usando `generate_demo_events`, CostCalculator y precios de ejemplo leídos como texto. Ese script no abre sesiones ni accede a una base.

Fixture versionada: metadatos sintéticos de uso, costo como string decimal y days_ago entero relativo al día actual UTC; reloj inyectable en tests. La agregación local replica filtros inclusivos, customer nulo como unassigned y contrato/orden por dimensión. Los cinco periodos de 14 días tienen 62, 70, 79, 89 y 100 llamadas del más antiguo al más reciente. Cada salto es del 12% al 13%. El generador redistribuye llamadas enteras para variar el gasto diario sin alterar los totales de cada ventana. La comparación de 14 días va de −22,85% a +23,91% respecto a su media, sin días marcados como pico. El pico único sigue en el periodo actual, tres días antes de hoy. Los importes exactos son $1.89550540 y $1.12196095, y siguen liderando `traduccion` y `globex`. El dashboard en ejecución no importa app/ ni SDK: solo HTTP o JSON local. Ninguna petición HTTP ni API_KEY es necesaria en demo.

Consulta de datos: una sola petición group_by=day desde el inicio del periodo anterior menos siete días hasta el fin actual alimenta tendencia, comparación y picos. Las dimensiones actuales se consultan por separado; una comprobación global por feature solo se usa para distinguir rango vacío de base sin eventos. Caché st.cache_data de 60 segundos, por sesión, sin persistencia; argumento _api_key excluido del hash y de logs. Un cambio de configuración de credencial invalida la caché de sesión; Reintentar también la limpia. Referencia: [cache_data 1.65.0](https://docs.streamlit.io/1.65.0/develop/api-reference/caching-and-state/st.cache_data).

## Exportaciones seguras

- `dashboard/exports.py`: funciones puras que devuelven bytes. CSV UTF-8 con BOM por tabla; las columnas monetarias conservan su representación decimal exacta. Usar la misma selección y orden que se muestran, sin incluir la clave API ni URLs internas.
- XLSX: hojas **Resumen**, **Por feature**, **Por customer**, **Por modelo**, **Tendencia diaria** y **Metadatos**. En Resumen incluir «Si ve celdas vacías, pulse Habilitar edición para calcular los totales» y junto a la opción «Exportar Excel» dentro del menú Exportar. Encabezados congelados (A2), anchos por columna, autofiltro en detalles, importes a ocho decimales, tasas a seis, conteos enteros y porcentajes numéricos. Nombres estáticos de hojas y columnas.
- Totales con SUM y costo medio mediante división de gasto total entre llamadas totales, nunca promedio de promedios. Resumen enlaza las fórmulas de detalle; no suma las tres dimensiones entre sí. Vacíos y divisiones por cero protegidos; un libro sin filas no crea referencias circulares. Fórmulas propias calculables al abrir Excel; preservar Decimal hasta escribir las celdas numéricas.
- Metadatos: periodo, fecha de generación en UTC, fuente efectiva api/demo y alcance «periodo completo, sin búsqueda». Sin secretos ni rutas locales. El mismo snapshot alimenta pantalla y exports; un fallo de datos bloquea ambas salidas.
- Toda etiqueta de origen API (feature, customer o modelo), aunque parezca numérica, se escribe como texto. Si empieza por `=`, `+`, `-`, `@` o tabulador, neutralizar con apóstrofo antes de CSV/XLSX; detectar también el prefijo tras espacios o saltos de línea. Costos validados y contadores se escriben como números; solo las fórmulas generadas por código confiable pueden ser fórmulas.
- Única dependencia nueva prevista: **openpyxl**, en el grupo dashboard, porque permite crear y reabrir XLSX con fórmulas y formatos sin otra librería gráfica. En ese mismo commit actualizar uv.lock y CI a `uv sync --frozen --group dashboard`. No instalarla durante este brief.

## Implementación prevista y validación

Streamlit instalado 1.65.0 y Altair 6.3.0: firmas locales comprobadas para layout wide, segmented_control, toggle, popover, download_button, tabs, dataframe, metric y empty; opciones light/dark/fontFaces disponibles. Contrastar cada API nuevamente al implementarla. Referencias: [temas](https://docs.streamlit.io/develop/concepts/configuration/theming), [fuentes](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-fonts) y [dataframe 1.65.0](https://docs.streamlit.io/1.65.0/develop/api-reference/data/st.dataframe).

Se prefieren tablas semánticas a la grilla: orden y búsqueda explícitos alimentan el mismo snapshot para pantalla y CSV, sin depender de ordenaciones internas de st.dataframe ni ofrecer su descarga alternativa sin neutralización. Barras de proporción mediante CSS y porcentaje textual, sin JavaScript ni librería adicional.

Separación: app.py compone UI; data.py valida HTTP; analytics.py calcula periodos/comparación/picos/observaciones; demo.py agrega JSON; exports.py serializa; theme.py contiene CSS y las fuentes. Los gráficos usan los colores por nombre de `.streamlit/config.toml`. Usar placeholders de st.empty para esqueletos, no inventar st.skeleton. CSS acotado a clases propias y al contenedor que aporta el esquema de color, sin scripts inyectados. Tabla contable con footer de doble regla; todo lo demás sin ornamentos. Texto sentence case, sin etiquetas en mayúsculas ni encabezados decorativos. Acciones coherentes: Aplicar y Exportar. Telemetría desactivada con browser.gatherUsageStats=false, opción verificada en 1.65.0; fuentes en dashboard/static/fonts y server.enableStaticServing=true, servido en app/static/fonts, verificado en fuente instalada y por HTTP antes del commit de interfaz.

Antes de insertar cualquier valor dinámico en HTML con unsafe_allow_html, aplicar **html.escape(..., quote=True)**, incluidos nombres en KPI, ayudas y observaciones. No registrar cuerpos, headers ni claves. Prefijar y escapar texto para CSV/Excel es una protección distinta, también obligatoria. Limitar el texto de fuentes a «api»/«demo», no a credenciales.

Pruebas de aceptación posteriores: API diaria con cambio de día UTC y límites inclusivos; demo sin red/BD ni imports de app/; periodos iguales y base cero; pico en igualdad no marcado y en exceso marcado; conciliación de sumas; HTML malicioso y prefijos de fórmula; XLSX reabierto comprobando texto de fórmulas, nota de edición, hojas y formatos; M8; ambos temas, teclado y capturas a tres anchos. Cobertura app+sdk superior al 80% y suite/lint/formato en verde antes de cada commit. Docker no se inicia en este paso.

Antes del commit de interfaz: crítica explícita de elementos prescindibles y eliminación de los que no aporten información. Estados y errores explican qué pasó y cómo arreglarlo.

La revisión de la interfaz se hizo sobre el trabajo de `feat: modern dashboard interface`. El pulido posterior incorpora los cambios solicitados tras esa revisión. El commit documental final queda pendiente.

Skills revisadas disponibles relacionadas: find-skills, visualize, spreadsheets, api-patterns, testing-patterns y computer-use. No hay skill UI/UX especializada instalada. El dueño pidió no instalar frontend-design; referencia leída: [frontend-design de Anthropic](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md), para dirección visual y crítica de interfaz. Las instrucciones de este brief tienen prioridad; instalarla requiere aprobación independiente y no bloquea su revisión.
