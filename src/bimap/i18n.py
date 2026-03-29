"""Simple EN/ES translation support for BIMAP.

Usage
-----
    from bimap.i18n import t, set_language, get_language

    set_language("es")   # or "en"
    label = t("Save")    # → "Guardar"
"""

from __future__ import annotations

_ES: dict[str, str] = {
    # ── Menu bar ────────────────────────────────────────────────────────────
    "File": "Archivo",
    "Edit": "Editar",
    "View": "Vista",
    "Map": "Mapa",
    "Data": "Datos",
    "Help": "Ayuda",

    # ── File menu ────────────────────────────────────────────────────────────
    "New Project": "Nuevo Proyecto",
    "Open…": "Abrir…",
    "Recent Projects": "Proyectos Recientes",
    "Save": "Guardar",
    "Save As…": "Guardar Como…",
    "Import GeoJSON…": "Importar GeoJSON…",
    "📤  Export Data Backup…": "📤  Exportar Copia de Seguridad…",
    "📥  Import Data Backup…": "📥  Importar Copia de Seguridad…",
    "Print / Export PDF…": "Imprimir / Exportar PDF…",
    "Quit": "Salir",

    # ── Unsaved-changes / exit dialogs ──────────────────────────────────────
    "Unsaved Changes": "Cambios sin guardar",
    "You have unsaved changes. Discard them?": "Hay cambios sin guardar. ¿Descartarlos?",
    "Replace Project?": "¿Reemplazar proyecto?",
    "This will replace the current project with the backup.\nUnsaved changes will be lost. Continue?": "Esto reemplazará el proyecto actual con la copia de seguridad.\nSe perderán los cambios sin guardar. ¿Continuar?",

    # ── Edit menu ────────────────────────────────────────────────────────────
    "Undo": "Deshacer",
    "Redo": "Rehacer",
    "Delete Selected": "Eliminar Seleccionado",
    "Draw Polygon Zone": "Dibujar Zona Polígono",
    "Draw Rectangle Zone": "Dibujar Zona Rectángulo",
    "Draw Circle Zone": "Dibujar Zona Círculo",
    "Place Keypoint": "Colocar Punto Clave",
    "Place Text Annotation": "Colocar Anotación de Texto",

    # ── View menu ────────────────────────────────────────────────────────────
    "Save Bookmark…": "Guardar Marcador…",
    "Bookmarks": "Marcadores",

    # ── Map menu ─────────────────────────────────────────────────────────────
    "Search Location…": "Buscar Ubicación…",
    "Zoom In": "Acercar",
    "Zoom Out": "Alejar",
    "Set Delimitation…": "Establecer Delimitación…",
    "Clear Delimitation": "Borrar Delimitación",
    "Place by Coordinates…": "Colocar por Coordenadas…",

    # ── Data menu ────────────────────────────────────────────────────────────
    "Add Data Source…": "Agregar Fuente de Datos…",
    "Refresh All Sources": "Actualizar Todas las Fuentes",

    # ── Measurement menu ─────────────────────────────────────────────────────
    "Measurement": "Medición",
    "Start Measuring": "Iniciar Medición",
    "Clear Measurement": "Limpiar Medición",

    # ── Help menu ────────────────────────────────────────────────────────────
    "About BIMAP": "Acerca de BIMAP",
    "Language": "Idioma",
    "English": "English",
    "Spanish": "Español",
    "Restart required": "Reinicio requerido",
    "Language changed. Please restart BIMAP to apply.": (
        "Idioma cambiado. Por favor reinicie BIMAP para aplicar."
    ),

    # ── Toolbar tooltips ─────────────────────────────────────────────────────
    "Select / move elements": "Seleccionar / mover elementos",
    "Pan the map": "Desplazar el mapa",
    "Dynamic Selector": "Selector Dinámico",
    "Rotate zone (click zone, then ↑/↓ to rotate 1° at a time)": (
        "Rotar zona (clic en zona, luego ↑/↓ para rotar 1° a la vez)"
    ),
    "Move element (click to pick, click to drop)": "Mover elemento (clic para seleccionar, clic para soltar)",
    "Rotation angle — type a value or use ↑/↓ on the map": (
        "Ángulo de rotación — escriba un valor o use ↑/↓ en el mapa"
    ),
    "Measure distance on map (click points, Esc to clear)": (
        "Medir distancia en el mapa (clic para agregar puntos, Esc para borrar)"
    ),
    "Lasso: area-select to batch remove": "Zona Dinámica: selección de área para eliminar en lote",
    "Draw polygon zone": "Dibujar zona polígono",
    "Draw rectangle zone": "Dibujar zona rectángulo",
    "Draw circle zone": "Dibujar zona círculo",
    "Place keypoint marker": "Colocar marcador de punto clave",
    "Place text annotation": "Colocar anotación de texto",

    # ── Search bar ───────────────────────────────────────────────────────────
    "Search location…": "Buscar ubicación…",
    "Search location (Enter)": "Buscar ubicación (Enter)",
    "Search": "Buscar",
    "  Map: ": "  Mapa: ",
    "Tile provider": "Proveedor de mosaicos",
    "Zoom in  [ + ]": "Acercar  [ + ]",
    "Zoom out  [ - ]": "Alejar  [ - ]",

    # ── Dock widget titles ───────────────────────────────────────────────────
    "Layers": "Capas",
    "Properties": "Propiedades",
    "Keynotes": "Notas Clave",
    "Data Sources": "Fuentes de Datos",

    # ── Geocode dialog ───────────────────────────────────────────────────────
    "Search Location": "Buscar Ubicación",
    "Enter address or place name:": "Introduzca una dirección o nombre de lugar:",
    "e.g. Madrid, Spain": "Ej: Madrid, España",
    "Searching…": "Buscando…",
    "No results found.": "No se encontraron resultados.",

    # ── Place by Coordinates dialog ──────────────────────────────────────────
    "Place by Coordinates": "Colocar por Coordenadas",
    "Keypoint (single point)": "Punto clave (un punto)",
    "Zone (polygon vertices)": "Zona (vértices de polígono)",
    "Enter one vertex per line as:  lat, lon\n(minimum 3 vertices to create a zone)": (
        "Introduzca un vértice por línea como:  lat, lon\n(mínimo 3 vértices para crear una zona)"
    ),
    "At least 3 vertices are required to create a zone.": (
        "Se necesitan al menos 3 vértices para crear una zona."
    ),
    "No forms match this element type. Select from all available forms:": (
        "No hay formularios para este tipo de elemento. Seleccione de los disponibles:"
    ),

    # ── Export dialog ────────────────────────────────────────────────────────
    "Export PDF": "Exportar PDF",
    "Page Settings": "Configuración de Página",
    "Page Size": "Tamaño de Página",
    "Orientation": "Orientación",
    "DPI": "DPI",
    "Output file path…": "Ruta del archivo de salida…",
    "Browse…": "Examinar…",
    "Output File:": "Archivo de Salida:",
    "Save PDF": "Guardar PDF",
    "PDF Files (*.pdf)": "Archivos PDF (*.pdf)",

    # ── Properties panel tabs ────────────────────────────────────────────────
    "Style": "Estilo",
    "Metadata": "Metadatos",
    "Extension": "Extensión",
    "Select an element to view its metadata.": "Seleccione un elemento para ver sus metadatos.",

    # ── Extension editor / viewer ────────────────────────────────────────────
    "Edit Extension…": "Editar Extensión…",
    "Create Extension…": "Crear Extensión…",
    "Launch Viewer": "Abrir Visor",
    "No extension configured for this element.": "Sin extensión configurada para este elemento.",
    "Extension Editor": "Editor de Extensión",
    "Load Template": "Cargar Plantilla",
    "Hello World (starter)": "Hola Mundo (plantilla inicial)",
    "From Library\u2026": "De la Biblioteca\u2026",
    "Extension Library": "Biblioteca de Extensiones",
    "Choose from Library": "Elegir de la Biblioteca",
    "Select a template to load into the editor:": "Selecciona una plantilla para cargar en el editor:",
    "Bar Chart (metadata values)": "Gráfico de Barras (valores metadata)",
    "Gauge (single value)": "Medidor (valor único)",
    "Table (all metadata)": "Tabla (toda la metadata)",
    "Open in Browser": "Abrir en Navegador",
    "Save": "Guardar",
    "HTML content is required.": "Se requiere contenido HTML.",
    "No element selected.": "Ningún elemento seleccionado.",

    # ── Properties panel form labels ─────────────────────────────────────────
    "Properties": "Propiedades",
    "Zone": "Zona",
    "New Zone": "Nueva Zona",
    "New Circle": "Nuevo Círculo",
    "Refresh map tiles": "Actualizar teselas del mapa",
    "Keypoint": "Punto de Interés",
    "Annotation": "Anotación",
    "Preset": "Preajuste",
    "Name": "Nombre",
    "Group": "Grupo",
    "Fill": "Relleno",
    "Color": "Color",
    "Opacity": "Opacidad",
    "Border": "Borde",
    "Width": "Ancho",
    "Label": "Etiqueta",
    "Text": "Texto",
    "Font": "Fuente",
    "Size": "Tamaño",
    "Bold": "Negrita",
    "Italic": "Cursiva",
    "Bg Color": "Color Fondo",
    "Offset X": "Desp. X",
    "Offset Y": "Desp. Y",
    "Geometry": "Geometría",
    "Radius (m)": "Radio (m)",
    "Width (m)": "Ancho (m)",
    "Height (m)": "Alto (m)",
    "Rotation": "Rotación",
    "SVG Fill": "Relleno SVG",
    "Browse\u2026": "Examinar\u2026",
    "Clear": "Limpiar",
    "No file selected": "Sin archivo seleccionado",
    "Toggle coordinate grid (precision move)": "Activar cuadrícula de coordenadas (mover con precisión)",
    "Rotate zone (click zone, then \u2191/\u2193 to rotate 1\u00b0 at a time)": "Rotar zona (clic en zona, luego \u2191/\u2193 para rotar 1\u00b0)",
    "Form Designer": "Diseñador de Formularios",
    "Form Designer\u2026": "Diseñador de Formularios\u2026",
    "Forms": "Formularios",
    "Form": "Formulario",
    "Design": "Diseño",
    "--- none ---": "--- ninguno ---",
    "Fill Form...": "Rellenar Formulario...",
    "Fill Form…": "Rellenar Formulario…",
    "Open Form Designer...": "Abrir Diseñador de Formularios...",
    "No forms defined. Use Data > Form Designer to create one.": (
        "Sin formularios definidos. Use Datos > Diseñador de Formularios para crear uno."
    ),
    "+ General Info": "+ Info General",
    "Insert a pre-built General Information form with common fields": (
        "Insertar un formulario de Información General predefinido con campos comunes"
    ),
    "General Information": "Información General",
    "Standard general-purpose information form for zones and keypoints.": (
        "Formulario de información general para zonas y puntos clave."
    ),
    "Active": "Activo",
    "Inactive": "Inactivo",
    "Pending": "Pendiente",
    "Under Review": "En Revisión",
    "Low": "Bajo",
    "Medium": "Medio",
    "High": "Alto",
    "Critical": "Crítico",
    "Tags": "Etiquetas",
    "\ud83d\udcdd  Edit Info\u2026": "\ud83d\udcdd  Editar Info\u2026",
    "Edit Info": "Editar Info",
    "Select form:": "Seleccionar formulario:",
    "Icon": "Icono",
    "Pin": "Pin",
    "Circle": "Círculo",
    "Square": "Cuadrado",
    "Diamond": "Diamante",
    "Star": "Estrella",
    "Custom\u2026": "Personalizado\u2026",
    "Choose Icon": "Elegir Icono",
    "New Form": "Nuevo Formulario",
    "Add Field": "Añadir Campo",
    "+ Add Field": "+ Añadir Campo",
    "New Field": "Nuevo Campo",
    "Remove Field": "Eliminar Campo",
    "Field Label": "Etiqueta del Campo",
    "Field Type": "Tipo de Campo",
    "Type": "Tipo",
    "Status": "Estado",
    "Priority": "Prioridad",
    "Fields": "Campos",
    "Default value": "Valor por defecto",
    "Options (one per line):": "Opciones (una por línea):",
    "Required": "Obligatorio",
    "Default Value": "Valor por Defecto",
    "Target": "Destino",
    "Zone & Keypoint": "Zona y Punto de Interés",
    "Form Properties": "Propiedades del Formulario",
    "Field Editor": "Editor de Campo",
    "Default": "Por Defecto",
    "Move field up": "Subir campo",
    "Move field down": "Bajar campo",
    "Confirm Delete": "Confirmar Eliminación",
    "Delete form '{name}'? This cannot be undone.": "¿Eliminar formulario '{name}'? No se puede deshacer.",
    "Required Field": "Campo Obligatorio",
    "Field '{label}' is required.": "El campo '{label}' es obligatorio.",
    "* Required fields": "* Campos obligatorios",
    "+ New Form": "+ Nuevo Formulario",
    "Delete": "Eliminar",
    "Title": "Título",
    "Subtitle": "Subtítulo",
    "Notes": "Notas",
    "URL": "URL",
    "Pin Color": "Color Pin",
    "Pin Size": "Tamaño Pin",
    "Latitude": "Latitud",
    "Longitude": "Longitud",
    "Font Size": "Tamaño Fuente",
    "Text Color": "Color Texto",
    "Background": "Fondo",
    "Key": "Clave",
    "Value": "Valor",
    "+ Add": "+ Añadir",
    "Remove Selected": "Eliminar Selección",
    "Source": "Fuente",
    "Bind Metadata Key": "Vincular Clave de Metadato",
    "Data Source": "Fuente de Datos",
    "Column": "Columna",
    "Filter Field": "Campo Filtro",
    "Filter Value": "Valor Filtro",
    "Aggregate": "Agregar",
    "Clear Binding": "Eliminar Vínculo",
    "— none —": "— ninguno —",
    "(optional) e.g. zone_name": "(opcional) ej. nombre_zona",
    "Use {{element.name}} or {{element.id}} as dynamic filter values.": "Usa {{element.name}} o {{element.id}} como valores de filtro dinámicos.",
    "Double-click Source column to bind a key to a data source": "Doble clic en columna Fuente para vincular una clave a un origen de datos",
    "Select from library or choose Custom:": "Seleccionar de biblioteca o elegir Personalizado:",
    "Choose Color": "Elegir color",
    "➕ New Data Source…": "➕ Nueva fuente de datos…",
    "Select an element to view its extension.": "Seleccione un elemento para ver su extensión.",

    # ── Context menu (tile_widget) ───────────────────────────────────────────
    "📝  Add Text here": "📝  Agregar Texto aquí",
    "✏  Edit…": "✏  Editar…",
    "↔  Move": "↔  Mover",
    "📋  View Metadata…": "📋  Ver Metadatos…",
    "🗑  Remove…": "🗑  Eliminar…",
    "🔗  Open Extension…": "🔗  Abrir Extensión…",

    # ── Data source dialog ───────────────────────────────────────────────────
    "Add Data Source": "Agregar Fuente de Datos",
    "Refresh": "Actualizar",
    "Mode": "Modo",
    "Interval": "Intervalo",
    "File Path": "Ruta de Archivo",
    "Sheet": "Hoja",
    "Connection": "Conexión",
    "Query": "Consulta",
    "Auth Token": "Token de Autenticación",
    "Data Path": "Ruta de Datos",
    "Host": "Host",
    "Port": "Puerto",
    "Database": "Base de datos",
    "User": "Usuario",
    "Password": "Contraseña",
    "Table": "Tabla",
    "Filter": "Filtro",
    "Sheet name or index (default: 0)": "Nombre de hoja o índice (por defecto: 0)",

    # ── Layers panel ─────────────────────────────────────────────────────────
    "+ Layer": "+ Capa",
    "Add a new layer": "Añadir nueva capa",
    "Export Layer CSV…": "Exportar Capa a CSV…",
    "Export elements of the selected layer to CSV": "Exportar elementos de la capa seleccionada a CSV",
    "🗑  Remove Layer…": "🗑  Eliminar Capa…",
    "Cannot Remove": "No se puede eliminar",
    "The 'Default' layer cannot be removed.": "La capa 'Default' no se puede eliminar.",
    "🎯  Go to": "🎯  Ir a",
    "🔄  Update": "🔄  Actualizar",

    # ── Delimitation dialog ──────────────────────────────────────────────────
    "Set Delimitation": "Fijar Delimitación",
    "Current delimitation:": "Delimitación actual:",
    "Search for a city, province, country, etc.:": "Buscar ciudad, provincia, país, etc.:",

    "Please select a result first.": "Seleccione primero un resultado.",

    # ── Dynamic Zone / multi-select ────────────────────────────────────────────────
    "Dynamic Zone": "Zona Dinámica",
    "No elements found inside Dynamic Zone.": "No se encontraron elementos dentro de la Zona Dinámica.",
    "{n} element(s) inside the Dynamic Zone.": "{n} elemento(s) dentro de la Zona Dinámica.",

    # ── GeoJSON / CSV export ────────────────────────────────────────────────────
    "Export GeoJSON": "Exportar GeoJSON",
    "Export GeoJSON…": "Exportar GeoJSON…",
    "Export Elements CSV": "Exportar Elementos a CSV",
    "CSV Exported": "CSV exportado",
    "Exported": "Exportados",
    "zone(s)": "zona(s)",
    "keypoint(s)": "punto(s) de interés",
    "and": "y",
    "to": "en",

    # ── main_window.py dialog titles / messages ──────────────────────────────
    "Open Project": "Abrir proyecto",
    "Save Project As": "Guardar proyecto como",
    "Open Failed": "Error al abrir",
    "Save Failed": "Error al guardar",
    "Import GeoJSON": "Importar GeoJSON",
    "Import Failed": "Error al importar",
    "Export Data Backup": "Exportar copia de seguridad",
    "Backup Exported": "Copia exportada",
    "Backup saved to:\n{path}\n\nCopy this file to transfer your project to another PC.": (
        "Copia guardada en:\n{path}\n\nCopie este archivo para transferir su proyecto a otro PC."
    ),
    "Export Failed": "Error al exportar",
    "Import Data Backup": "Importar copia de seguridad",
    "Backup imported successfully.": "Copia importada correctamente.",
    "Print Error": "Error al imprimir",
    "Save Bookmark": "Guardar marcador",
    "Bookmark name:": "Nombre del marcador:",
    "Add Layer": "Añadir capa",
    "Layer name:": "Nombre de la capa:",
    "Duplicate Layer": "Capa duplicada",
    "A layer named '{name}' already exists.": "Ya existe una capa llamada '{name}'.",
    "Delimitation cleared.": "Delimitación eliminada.",
    "Confirm Remove": "Confirmar eliminación",
    "Remove '{name}'?": "¿Eliminar '{name}'?",
    "🗑  Delete {n} element(s)": "🗑  Eliminar {n} elemento(s)",
    "⬠  Create Polygon Zone": "⬠  Crear zona polígono",

    # ── Metadata view dialog ─────────────────────────────────────────────────
    "No metadata entries for this element.": "Sin entradas de metadatos para este elemento.",
    "Close": "Cerrar",
    "Copy All": "Copiar Todo",
    "Copied to clipboard.": "Copiado al portapapeles.",

    # ── Map Composer dialog ──────────────────────────────────────────────────
    "Map Composer": "Compositor de Mapa",
    "Page && Zoom": "Página y Zoom",
    "Legend": "Leyenda",
    "Title Block": "Bloque de Título",
    "Info Box": "Cuadro de Info",
    "Cancel": "Cancelar",
    "🖶  Print…": "🖶  Imprimir…",
    "📄  Export PDF": "📄  Exportar PDF",
    "Capture Zoom": "Zoom Captura",
    "Show legend overlay on output": "Mostrar leyenda en salida",
    "Legend Title": "Título de Leyenda",
    "Zones (uncheck to hide, edit Display Label to rename):": "Zonas (desmarcar para ocultar, editar Etiqueta para renombrar):",
    "Layer": "Capa",
    "Display Label": "Etiqueta Mostrada",
    "Show architectural title block on output": "Mostrar bloque de título arquitectónico en salida",
    "Project Name": "Nombre del Proyecto",
    "Description": "Descripción",
    "Drawn by": "Dibujado por",
    "Checked by": "Verificado por",
    "Revision": "Revisión",
    "Scale": "Escala",
    "Show info box overlay on output": "Mostrar cuadro de info en salida",
    "Text block (appears in the info box):": "Bloque de texto (aparece en el cuadro de info):",
    "Author": "Autor",
    "Date": "Fecha",
    "Output File  (required for Export PDF)": "Archivo de Salida  (requerido para Exportar PDF)",
    "Choose output .pdf path…": "Elegir ruta del archivo .pdf de salida…",
    "landscape": "horizontal",
    "portrait": "vertical",

    # ── Extension library / manager ──────────────────────────────────────────
    "Extension Library": "Biblioteca de Extensiones",
    "Manage Extensions": "Gestionar Extensiones",
    "New Extension": "Nueva Extensión",
    "Extension Name": "Nombre de Extensión",
    "Extension Description": "Descripción de Extensión",
    "Delete Extension": "Eliminar Extensión",
    "Apply from Library": "Aplicar desde Biblioteca",
    "From Library…": "Desde Biblioteca…",
    "Select Extension": "Seleccionar Extensión",
    "No extensions in library.": "Sin extensiones en la biblioteca.",
    "View Extension": "Ver Extensión",
    "Open Extension…": "Abrir Extensión…",
    "Confirm Delete": "Confirmar Eliminación",
    "Delete extension '{name}'? This cannot be undone.": "¿Eliminar extensión '{name}'? Esta acción no se puede deshacer.",
    "Set Extension": "Establecer Extensión",
    "Set Extension…": "Establecer Extensión…",
    "✏\u2002Custom (open editor)": "✏\u2002Personalizado (abrir editor)",
    "Open Viewer": "Abrir Visor",
    "Reload": "Recargar",
    "— Apply Preset —": "— Aplicar Preajuste —",

    # ── Preferences dialog ───────────────────────────────────────────────────
    "Preferences…": "Preferencias…",
    "Preferences": "Preferencias",
    "General": "General",
    "Map": "Mapa",
    "Cache": "Caché",
    "Appearance": "Apariencia",
    "Advanced": "Avanzado",
    "Autosave interval": "Intervalo de autoguardado",
    "Autosave interval in seconds (10–600)": "Intervalo de autoguardado en segundos (10–600)",
    "Undo stack limit": "Límite de historial deshacer",
    "Maximum number of undo steps (10–500)": "Número máximo de pasos deshacer (10–500)",
    "On startup": "Al iniciar",
    "Empty project": "Proyecto vacío",
    "Reopen last project": "Reabrir último proyecto",
    "Default zoom": "Zoom predeterminado",
    "Default latitude": "Latitud predeterminada",
    "Default longitude": "Longitud predeterminada",
    "Show Keynotes": "Mostrar Notas Clave",
    "Show Data Sources": "Mostrar Fuentes de Datos",
    "Show scale bar": "Mostrar barra de escala",
    "Show north arrow": "Mostrar flecha norte",
    "Grid size": "Tamaño de cuadrícula",
    "Fine (0.5×)": "Fina (0.5×)",
    "Normal (1×)": "Normal (1×)",
    "Coarse (2×)": "Gruesa (2×)",
    "Very Coarse (4×)": "Muy gruesa (4×)",
    "Max tile cache size": "Tamaño máximo de caché",
    "Tile expiry": "Caducidad de mosaicos",
    " days": " días",
    "Cache size and expiry take effect on next launch.": "El tamaño y caducidad de caché se aplican al próximo inicio.",
    "Clear cache now": "Limpiar caché ahora",
    "Current size": "Tamaño actual",
    "Theme settings are not yet available.\nThis page is reserved for a future release.": (
        "Los ajustes de tema aún no están disponibles.\nEsta página está reservada para una versión futura."
    ),
    "Projects folder": "Carpeta de proyectos",
    "(default)": "(predeterminado)",
    "Choose folder": "Elegir carpeta",
    "Reset all to defaults": "Restablecer todo a valores predeterminados",
    "Reset all preferences to their default values?": "¿Restablecer todas las preferencias a sus valores predeterminados?",

    # ── Live Feeds — Preferences page ───────────────────────────────────────
    "Live Feeds": "Feeds en Vivo",
    "live_network_timeout": "Tiempo de espera de red",
    "live_timeout_tip": "Segundos antes de que falle una solicitud de feed (1–60)",
    "live_max_markers": "Marcadores máximos",
    "live_trail_default": "Longitud de historial predeterminada",
    "live_follow_fastest": "Centrar mapa en el marcador más rápido",
    "live_show_error_badge": "Mostrar errores de feed en la barra de estado",
    "trail_off": "Desactivado",

    # ── Live Feed layer dialog ───────────────────────────────────────────────
    "add_live_feed": "Agregar Feed en Vivo",
    "edit_live_feed": "Editar Feed en Vivo",
    "manage_live_feeds": "Gestionar Feeds en Vivo",
    "tab_feed": "Feed",
    "tab_style": "Estilo",
    "quick_start": "Inicio rápido",
    "preset_choose": "— Elegir preset —",
    "feed_name": "Nombre",
    "feed_name_placeholder": "p.ej. Autobuses en tiempo real",
    "feed_url": "URL del Feed",
    "poll_interval": "Intervalo de actualización",
    "auth_header": "Cabecera de autenticación",
    "lat_field": "Campo latitud",
    "lon_field": "Campo longitud",
    "label_field": "Campo etiqueta",
    "test_connection": "Probar conexión",
    "test_preview_placeholder": "El JSON de respuesta aparecerá aquí…",
    "preview": "Vista previa",
    "icon_type": "Tipo de icono",
    "icon_color": "Color del icono",
    "icon_size": "Tamaño del icono",
    "trail_length": "Longitud del rastro",
    "visible": "Visible",
    "enter_url_first": "Ingrese primero la URL del feed.",
    "connecting": "Conectando…",
    "network_unavailable": "Módulo de red no disponible.",
    "unnamed_feed": "Feed sin nombre",
    "pick_color": "Elegir color",
    "Invalid URL": "URL no válida",
    "URL must start with http:// or https://": "La URL debe comenzar con http:// o https://",

    # ── Live Layers panel ────────────────────────────────────────────────────
    "edit": "Editar",
    "pause": "Pausar",
    "resume": "Reanudar",
    "remove": "Eliminar",
    "remove_live_feed": "Eliminar Feed en Vivo",
    "confirm_remove_live_feed": "¿Eliminar este feed en vivo?",
    # ── Keypoint → Zone conversion ──────────────────────────────────────────
    "\u2b21  Convert to Zone by Color\u2026": "\u2b21  Convertir a Zona por Color\u2026",
    "Convert to Zone by Color": "Convertir a Zona por Color",
    "Color tolerance (0 = exact match, 100 = all colors):": (
        "Tolerancia de color (0 = exacto, 100 = todos los colores):"
    ),

    # ── Offline map dialog ───────────────────────────────────────────────────
    "Offline Map…": "Mapa sin conexión…",
    "🗺  Work Offline — Save Map Region…": "🗺  Trabajar sin conexión — Guardar región del mapa…",
    "Work Offline — Save Map Region": "Trabajar sin conexión — Guardar región del mapa",
    "Bounding Box": "Área de cobertura",
    "Lat min (South):": "Lat mín (Sur):",
    "Lat max (North):": "Lat máx (Norte):",
    "Lon min (West):": "Lon mín (Oeste):",
    "Lon max (East):": "Lon máx (Este):",
    "Use Current View": "Usar vista actual",
    "Zoom Levels": "Niveles de zoom",
    "Min zoom:": "Zoom mín:",
    "Max zoom:": "Zoom máx:",
    "Estimate Tile Count": "Estimar número de teselas",
    "Invalid bounds or zoom range": "Límites o rango de zoom no válidos",
    " ⚠ exceeds limit — reduce zoom or area": " ⚠ supera el límite — reduzca el zoom o el área",
    " (large — may take a while)": " (grande — puede tardar un momento)",
    "tiles": "teselas",
    "⬇  Download && Cache Tiles": "⬇  Descargar y guardar teselas",
    "Cancel Download": "Cancelar descarga",
    "Invalid Region": "Región no válida",
    "Please check bounds and zoom levels.": "Compruebe los límites y niveles de zoom.",
    "Region Too Large": "Región demasiado grande",
    "This region requires {count} tiles, which exceeds the safety limit of {limit}.\n"
    "Reduce the area or zoom range and try again.": (
        "Esta región requiere {count} teselas, lo que supera el límite de {limit}.\n"
        "Reduzca el área o el rango de zoom e inténtelo de nuevo."
    ),
    "Start Download?": "¿Iniciar descarga?",
    "Download {count} tiles for offline use?\n\nTiles already in cache will be skipped.": (
        "¿Descargar {count} teselas para uso sin conexión?\n\nLas teselas ya en caché se omitirán."
    ),
    "Downloading {done} / {total} tiles…": "Descargando {done} / {total} teselas…",
    "Cancelling…": "Cancelando…",
    "Done — {downloaded} tiles downloaded, {skipped} already cached / skipped.": (
        "Listo — {downloaded} teselas descargadas, {skipped} ya en caché / omitidas."
    ),
}

_current_lang: str = "en"


def set_language(lang: str) -> None:
    """Set the active language.  Supported: ``'en'``, ``'es'``."""
    global _current_lang
    if lang in ("en", "es"):
        _current_lang = lang


def get_language() -> str:
    """Return the current language code (``'en'`` or ``'es'``)."""
    return _current_lang


def t(key: str) -> str:
    """Translate *key* to the current language.  Returns *key* unchanged when
    running in English or when no translation is found."""
    if _current_lang == "en":
        return key
    return _ES.get(key, key)
