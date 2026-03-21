# BIMAP — Business Intelligence Map Designer

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Tests](https://img.shields.io/badge/tests-39%20passed-brightgreen)

> **Python + PyQt6 + OpenStreetMap** desktop application for designing rich, data-driven PDF maps with coloured zones, geographic keypoints, live data connections and a professional architectural title block export.

![BIMAP Screenshot](bimap_splash.png)

---

## Table of Contents

1. [Vision & Purpose](#1-vision--purpose)
2. [Features](#2-features)
3. [Quick Start](#3-quick-start)
4. [Architecture](#4-architecture)
5. [Tech Stack](#5-tech-stack)
6. [Project Structure](#6-project-structure)
7. [Running Tests](#7-running-tests)
8. [Building a Standalone Executable](#8-building-a-standalone-executable)
9. [Contributing](#9-contributing)
10. [License](#10-license)

---

## 1. Vision & Purpose

BIMAP is a desktop tool that lets analysts, consultants, and decision-makers **design presentation-quality PDF maps** enriched with business data. It unifies the workflow:

1. **Select** a geographic area via OpenStreetMap tile layers.
2. **Draw** coloured zones (polygons, circles, rectangles, freehand shapes) representing territories, risk areas, or market segments.
3. **Place** geographic keypoints (pins) with rich info cards holding metrics, links, and notes.
4. **Annotate** with text boxes, callout arrows, and numbered keynotes.
5. **Connect** to external sources (SQL, REST API, CSV/Excel) so the map refreshes automatically when data changes.
6. **Export** as a high-quality PDF with a professional architectural title block — or send directly to a printer.

### Target Users

| Role | Use Case |
|---|---|
| Business Analyst | Sales territory maps, market-penetration heat zones |
| Consultant | Client-facing keynote maps with KPI overlays |
| Operations Manager | Logistics routes, warehouse coverage zones |
| Real Estate | Property portfolios, zoning overlays |
| Marketing | Campaign reach maps, demographic zones |

---

## 2. Features

### Map Canvas
- OSM tile rendering with multi-provider support (OSM, CartoDB, Stamen, custom TMS)
- Pan, zoom-to-cursor, tile caching (LRU, 300 tiles)
- Address geocoding via Nominatim
- Named viewport bookmarks
- Right-click context menu on map elements

### Zone & Keypoint Drawing
- Tools: Polygon, Rectangle, Circle, Keypoint, Text annotation
- Freehand lasso multi-select (magic-wand tool)
- Per-element style: fill colour + alpha, border colour/width/style, font
- Style presets palette
- Lock/unlock zones
- GeoJSON import/export

### Data Integration
- CSV / Excel auto-reload on file change
- SQL (PostgreSQL, MySQL, SQLite) with SELECT-only guard
- REST API (GET + JSONPath field mapping)
- Background refresh scheduler
- Full undo/redo stack for all mutations

### PDF Export
- **Page sizes**: A4, A3, Letter, Legal — Portrait & Landscape
- **DPI**: 72 – 600 configurable
- **Architectural title block**: project name, description, Drawn by / Checked by / Revision / Scale / Sheet — auto-height scales with page size
- **Legend**: embedded in title block (enabled) or standalone floating box (title block disabled)
- **Info box**: floating annotated box above the title block
- **Keynote table**: auto-generated from numbered keypoints
- Live **WYSIWYG preview** in Map Composer dialog with drag-to-pan and zoom
- Send to system printer or export `.pdf`

### Administration
- `.bimap` JSON project files
- Auto-save (configurable interval)
- Undo/Redo (unlimited stack)
- Recent files & quick-reopen
- Version bump script (`bump_version.py`)
- GitHub Actions CI pipeline (`.github/workflows/ci.yml`)

---

## 3. Quick Start

### Prerequisites

- **Python 3.11+**
- A virtual environment (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/bimap.git
cd bimap
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e .
```

### Run

```bash
python -m bimap.app
# or, after pip install -e .:
bimap
```

### Development dependencies (linting, testing)

```bash
pip install -r requirements-dev.txt
```

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        BIMAP Application                        │
├────────────┬──────────────┬──────────────┬──────────────────────┤
│  UI Layer  │  Map Engine  │  Data Layer  │   Export Engine      │
│  (PyQt6)   │  (Tiles +    │ (Sources +   │  (QPdfWriter /       │
│            │   Overlays)  │  Bindings)   │   QPainter)          │
├────────────┴──────────────┴──────────────┴──────────────────────┤
│                       Core Domain Model                         │
│  Project ─┬─ MapState ─ Zones[] ─ Keypoints[] ─ Annotations[]  │
│           ├─ DataSources[] ── FieldMappings[]                   │
│           └─ PDFLayout ── LayoutItems[]                         │
├─────────────────────────────────────────────────────────────────┤
│                       Infrastructure                            │
│   Tile Cache │ Geocoding │ SQLAlchemy │ HTTP Client │ File I/O  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | **No WebEngine** | Render OSM tiles directly on a custom `QWidget` — full overlay control, no heavy dependency |
| 2 | **QPdfWriter (not ReportLab)** | Zero extra dependency; native Qt vector PDF output at any DPI |
| 3 | **Command pattern** | Every user action is a reversible `QUndoCommand` object — unlimited undo |
| 4 | **Pydantic models** | Domain objects are Pydantic `BaseModel`; automatic JSON serialization/validation |
| 5 | **Async tile fetch** | `QThreadPool` workers keep UI responsive during tile loads |

---

## 5. Tech Stack

| Category | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+ | Core language |
| GUI | PyQt6 ≥ 6.6 | Desktop UI, map canvas, PDF output |
| PDF | QPdfWriter (built-in Qt) | Vector PDF — no extra library needed |
| Map Tiles | OpenStreetMap / TMS | Base map imagery |
| Geocoding | geopy (Nominatim) | Address → coordinates |
| Data: SQL | SQLAlchemy ≥ 2.0 | Database connectivity |
| Data: Excel | openpyxl ≥ 3.1 | Excel file reading |
| Data: HTTP | requests | REST API calls |
| Caching | diskcache ≥ 5.6 | Tile & data LRU cache |
| Models | pydantic ≥ 2.5 | Validation, JSON serialization |
| Images | Pillow ≥ 10.0 | Icon/image manipulation |
| Credentials | keyring ≥ 24.3 | Secure token storage |
| Testing | pytest + pytest-qt | Unit & integration tests |
| Packaging | PyInstaller | Standalone `.exe` / app bundle |

---

## 6. Project Structure

```
BIMAP/
├── readme.md
├── pyproject.toml           # Project metadata & entry point
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Dev / test dependencies
├── bump_version.py          # Sync version across pyproject.toml + config.py
├── bimap_splash.png
│
├── src/bimap/
│   ├── app.py               # QApplication entry point
│   ├── config.py            # App-wide constants
│   ├── models/              # Pydantic domain models
│   │   ├── project.py
│   │   ├── map_state.py
│   │   ├── zone.py
│   │   ├── keypoint.py
│   │   ├── annotation.py
│   │   ├── data_source.py
│   │   ├── pdf_layout.py
│   │   └── style.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── toolbar.py
│   │   ├── map_canvas/      # Tile widget, overlay renderer, interaction
│   │   ├── panels/          # Layers, Properties, Data, Keynotes panels
│   │   └── dialogs/         # Map Composer, Data Source, Delimitation …
│   ├── engine/
│   │   ├── commands.py      # Undo/redo command objects
│   │   ├── project_io.py    # .bimap save/load
│   │   ├── pdf_renderer.py  # QPdfWriter render pipeline
│   │   ├── tile_math.py     # Lat/lon ↔ tile pixel math
│   │   ├── geocoding.py
│   │   └── delimitation.py  # Nominatim boundary fetcher
│   └── data/                # Data source connectors
│       ├── csv_source.py
│       ├── sql_source.py
│       ├── api_source.py
│       └── refresh.py
│
├── tests/
│   ├── conftest.py
│   ├── test_models/
│   ├── test_engine/
│   └── test_ui/
│
├── installer/
│   ├── bimap.spec           # PyInstaller spec
│   ├── setup.iss            # Inno Setup installer script
│   └── create_icon.py       # Generate .ico at multiple resolutions
│
└── .github/workflows/
    └── ci.yml               # GitHub Actions: lint + pytest on push/PR
```

---

## 7. Running Tests

```bash
python -m pytest tests/ -q
```

Expected output: **39 passed**.

To run with coverage:

```bash
pip install pytest-cov
python -m pytest tests/ --cov=src/bimap --cov-report=term-missing
```

---

## 8. Building a Standalone Executable

```bash
pip install pyinstaller
python installer/create_icon.py   # generate bimap.ico if missing
pyinstaller installer/bimap.spec
# Output: dist/bimap/bimap.exe  (Windows)
```

For a Windows installer, run `installer/setup.iss` with [Inno Setup](https://jrsoftware.org/isinfo.php).

---

## 9. Contributing

1. Fork the repository and create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes and add tests where appropriate.
3. Run `python -m pytest tests/ -q` — all tests must pass.
4. Open a Pull Request with a clear description of what changed and why.

Please follow the existing code style (PEP 8, type hints, Pydantic models for domain objects).

---

## 10. License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.


BIMAP is a desktop tool that lets analysts, consultants, and decision-makers **design presentation-quality PDF maps** enriched with business intelligence data. Instead of switching between GIS software, BI dashboards, and presentation tools, BIMAP unifies the workflow:

1. **Select** a geographic area via OpenStreetMap.
2. **Draw** colored zones (polygons, circles, custom shapes) representing business territories, risk areas, market segments, etc.
3. **Place** geographic keypoints (pins) with rich information cards (metrics, images, links).
4. **Annotate** with names, labels, keynotes, legends, and free text.
5. **Connect** to external sources (databases, REST APIs, CSV/Excel files) so the map automatically refreshes when data changes.
6. **Export** the finished map as a high-quality PDF ready for reports and keynotes.

### Target Users

| Role | Use Case |
|---|---|
| Business Analyst | Sales territory maps, market penetration heat zones |
| Consultant | Client-facing keynote maps with KPI overlays |
| Operations Manager | Logistics routes, warehouse coverage zones |
| Real Estate | Property portfolios, zoning overlays |
| Marketing | Campaign reach maps, demographic zones |

---

## 2. Core Feature Specifications

### 2.1 Map Canvas (OpenStreetMap)

- **Tile Renderer**: Render OSM tiles offline-capable (cache) and online.
- **Navigation**: Pan, zoom, rotation on the map canvas.
- **Tile Styles**: Support multiple tile providers (OSM standard, CartoDB, Stamen Toner, Stamen Watercolor, custom TMS/WMTS).
- **Coordinate System**: WGS84 (EPSG:4326) internally; display lat/lon and allow search by address (geocoding via Nominatim).
- **Map Viewport Bookmarks**: Save/restore named viewports for quick navigation.

### 2.2 Colored Zones

- **Zone Types**: Polygon, rectangle, circle, freehand shape.
- **Drawing Tools**: Click-to-place vertices, drag handles, snap to roads/features.
- **Styling**: Fill color (with alpha/transparency), border color, border width, border style (solid, dashed, dotted), hatch patterns.
- **Labels**: Each zone can have a name label (font, size, color, position auto/manual).
- **Data Binding**: A zone's color/style can be driven by a data field (e.g., revenue → green gradient).
- **Grouping**: Zones can belong to named groups/layers for visibility toggling.
- **GeoJSON Import/Export**: Import zone definitions from GeoJSON; export zones to GeoJSON.

### 2.3 Geographic Keypoints (Pins / Markers)

- **Placement**: Click on map or enter coordinates / address.
- **Icon Library**: Built-in icon set (pin, star, flag, building, factory, store…); support custom SVG/PNG icons.
- **Info Card**: Each keypoint carries a rich info card:
  - Title, subtitle
  - Key-value fields (e.g., "Revenue: $1.2M")
  - Small image/logo
  - URL link
  - Free-text notes
- **Tooltip / Popup**: On hover or click, display the info card on the canvas.
- **Data Binding**: Fields can be mapped to external data columns for auto-update.
- **Clustering**: When zoomed out, nearby keypoints cluster with a count badge.

### 2.4 Annotations & Keynotes

- **Text Boxes**: Place free text anywhere on the map with rich formatting (font, size, bold, italic, color, background).
- **Callout Arrows**: Arrow from a text box pointing to a map feature.
- **Legend Box**: Auto-generated or manual legend explaining zone colors, icons, etc.
- **Title Block**: Configurable title, subtitle, date, author, logo area (typically top or bottom of the PDF).
- **Scale Bar & North Arrow**: Optional cartographic elements.
- **Numbered Keynotes**: Auto-numbered keynote markers (①②③…) with a keynote table (number → description) printed alongside the map.

### 2.5 External Data Sources

| Source Type | Details |
|---|---|
| **CSV / Excel** | Import tabular data; map columns to keypoint fields or zone metrics. File watcher for auto-reload. |
| **SQL Database** | PostgreSQL, MySQL, SQLite via SQLAlchemy. Define query; schedule refresh interval. |
| **REST API** | GET endpoint returning JSON; JSONPath mapping to fields; OAuth2 / API key auth. |
| **Google Sheets** | Read-only via Sheets API v4; auto-refresh on interval. |
| **GeoJSON URL** | Fetch remote GeoJSON for zones/keypoints. |

- **Data Manager UI**: A panel to list, add, edit, test, and remove data sources.
- **Refresh Modes**: Manual, on-open, interval (e.g., every 5 min), webhook trigger.
- **Field Mapping**: Visual mapper linking source columns → map element properties.

### 2.6 PDF Export

- **Page Sizes**: A4, A3, Letter, Legal, custom dimensions.
- **Orientation**: Portrait / Landscape.
- **DPI**: 150 / 300 / 600 for print quality.
- **Layout Composer**: WYSIWYG page layout where the user places:
  - Map frame (with specific viewport/zoom)
  - Title block
  - Legend
  - Keynote table
  - Additional text blocks, images, logos
  - Multiple map frames per page (overview + detail insets)
- **Rendering Engine**: `reportlab` or `QPrinter`/`QPainter` for vector-quality output.
- **Batch Export**: Export multiple maps (e.g., one per region) from a template + data source.

### 2.7 Project System

- **Project File** (`.bimap`): JSON-based project file bundling:
  - Map viewport state
  - All zones, keypoints, annotations
  - Data source configurations (credentials stored separately/encrypted)
  - PDF layout template
  - Style presets
- **Auto-save & Undo/Redo**: Unlimited undo stack; periodic auto-save.
- **Template System**: Save/load reusable templates (layout + styles without data).

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        BIMAP Application                        │
├────────────┬──────────────┬──────────────┬──────────────────────┤
│   UI Layer │  Map Engine  │ Data Layer   │  Export Engine       │
│  (PyQt6)   │  (Tiles +    │ (Sources +   │  (PDF Generation)   │
│            │   Overlays)  │  Bindings)   │                     │
├────────────┴──────────────┴──────────────┴──────────────────────┤
│                      Core Domain Model                          │
│   Project ─┬─ MapState ─┬─ Zones[] ─┬─ Keypoints[]             │
│            │            ├─ Annotations[]                        │
│            ├─ DataSources[] ─── FieldMappings[]                 │
│            └─ PDFLayout ─── LayoutElements[]                    │
├─────────────────────────────────────────────────────────────────┤
│                      Infrastructure                             │
│   Tile Cache │ Geocoding │ SQLAlchemy │ HTTP Client │ File I/O  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 Layer Breakdown

| Layer | Responsibility | Key Libraries |
|---|---|---|
| **UI** | Windows, panels, toolbars, dialogs, user interaction | `PyQt6`, `PyQt6.QtWidgets`, `PyQt6.QtGui` |
| **Map Engine** | Tile fetching/caching, coordinate transforms, overlay rendering | Custom tile widget, `pyproj`, `Pillow` |
| **Data Layer** | Connect to external sources, refresh data, field mapping | `SQLAlchemy`, `requests`, `openpyxl`, `gspread` |
| **Export Engine** | Compose PDF pages, render map + overlays to vector PDF | `reportlab` or `QPrinter/QPainter` |
| **Core Model** | Domain objects, serialization, undo/redo commands | `dataclasses`, `pydantic`, JSON |
| **Infrastructure** | Caching, geocoding, file I/O, config | `diskcache`, `geopy`, `pathlib` |

### 3.2 Key Design Decisions

1. **No Web Browser Embedding** — Render OSM tiles directly on a `QGraphicsView` / custom `QWidget` using tile math. This gives full control over overlays and PDF export, avoids heavy WebEngine dependency.
2. **Command Pattern for Undo/Redo** — Every user action (add zone, move keypoint, change color) is a reversible command object.
3. **MVC-ish Separation** — Models are pure Python dataclasses; views are PyQt6 widgets; controllers handle interaction logic. Avoids coupling UI to data.
4. **Async Data Refresh** — External source fetching runs in `QThread` / `asyncio` to keep UI responsive.
5. **Plugin-Ready Architecture** — Data source connectors implement a common interface, making it easy to add new source types later.

---

## 4. Tech Stack

| Category | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | ≥ 3.11 | Core language |
| GUI Framework | PyQt6 | ≥ 6.6 | Desktop UI |
| Map Tiles | OpenStreetMap / Tile Servers | — | Base map imagery |
| PDF Generation | ReportLab | ≥ 4.0 | High-quality PDF output |
| Geocoding | geopy (Nominatim) | ≥ 2.4 | Address → coordinates |
| Coordinate Math | pyproj | ≥ 3.6 | CRS transforms |
| Data: SQL | SQLAlchemy | ≥ 2.0 | Database connectivity |
| Data: Excel | openpyxl | ≥ 3.1 | Excel file reading |
| Data: HTTP | requests / httpx | latest | REST API calls |
| Data: Google | gspread + oauth2client | latest | Google Sheets |
| Serialization | pydantic | ≥ 2.0 | Model validation & JSON |
| Image Processing | Pillow | ≥ 10.0 | Icon/image manipulation |
| Caching | diskcache | ≥ 5.6 | Tile & data caching |
| Testing | pytest + pytest-qt | latest | Unit & integration tests |
| Packaging | PyInstaller | latest | Standalone executable |

---

## 5. Project Structure

```
BIMAP/
├── readme.md                  # This file
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Project metadata & build config
├── setup.cfg                  # Package config
│
├── src/
│   └── bimap/
│       ├── __init__.py
│       ├── app.py             # Application entry point, QApplication setup
│       ├── config.py          # App-wide configuration & constants
│       │
│       ├── models/            # Core domain models (pure Python)
│       │   ├── __init__.py
│       │   ├── project.py     # Project root model
│       │   ├── map_state.py   # Viewport, zoom, center
│       │   ├── zone.py        # Zone (polygon) model
│       │   ├── keypoint.py    # Keypoint (marker) model
│       │   ├── annotation.py  # Text boxes, callouts, keynotes
│       │   ├── data_source.py # Data source config & field mapping
│       │   ├── pdf_layout.py  # PDF page layout model
│       │   └── style.py       # Color palettes, presets
│       │
│       ├── ui/                # PyQt6 UI layer
│       │   ├── __init__.py
│       │   ├── main_window.py # Main application window
│       │   ├── map_canvas/    # Custom map rendering widget
│       │   │   ├── __init__.py
│       │   │   ├── tile_widget.py    # OSM tile fetcher & renderer
│       │   │   ├── overlay_renderer.py # Draw zones/keypoints/annotations
│       │   │   ├── interaction.py    # Mouse/keyboard tools (pan, draw, select)
│       │   │   └── tile_cache.py     # Local tile cache manager
│       │   ├── panels/        # Side panels / dock widgets
│       │   │   ├── __init__.py
│       │   │   ├── layers_panel.py   # Zone/keypoint/annotation layers
│       │   │   ├── properties_panel.py # Edit selected element properties
│       │   │   ├── data_panel.py     # Data source manager
│       │   │   └── keynotes_panel.py # Keynote list & editor
│       │   ├── dialogs/       # Modal dialogs
│       │   │   ├── __init__.py
│       │   │   ├── export_dialog.py  # PDF export settings
│       │   │   ├── data_source_dialog.py # Add/edit data source
│       │   │   ├── style_dialog.py   # Zone/keypoint style editor
│       │   │   └── geocode_dialog.py # Search by address
│       │   ├── toolbar.py     # Main toolbar & drawing tools
│       │   └── pdf_composer/  # WYSIWYG PDF layout editor
│       │       ├── __init__.py
│       │       ├── composer_view.py  # Page layout canvas
│       │       └── layout_items.py   # Map frame, legend, text, image items
│       │
│       ├── engine/            # Business logic & services
│       │   ├── __init__.py
│       │   ├── commands.py    # Undo/Redo command objects
│       │   ├── project_io.py  # Save/load .bimap files
│       │   ├── geocoding.py   # Address lookup service
│       │   ├── tile_math.py   # Lat/lon ↔ tile coordinates
│       │   └── pdf_renderer.py # Render project → PDF
│       │
│       ├── data/              # Data source connectors
│       │   ├── __init__.py
│       │   ├── base.py        # Abstract data source interface
│       │   ├── csv_source.py  # CSV / Excel connector
│       │   ├── sql_source.py  # SQL database connector
│       │   ├── api_source.py  # REST API connector
│       │   ├── gsheets_source.py # Google Sheets connector
│       │   ├── geojson_source.py # GeoJSON file/URL connector
│       │   └── refresh.py     # Background refresh scheduler
│       │
│       └── resources/         # Static assets
│           ├── icons/         # App & map icons (SVG)
│           ├── styles/        # Default color palettes / themes
│           └── templates/     # Built-in PDF layout templates
│
├── tests/
│   ├── conftest.py
│   ├── test_models/
│   ├── test_engine/
│   ├── test_data/
│   └── test_ui/
│
└── docs/
    ├── architecture.md        # Detailed architecture notes
    ├── data_sources.md        # How to configure each source type
    └── user_guide.md          # End-user documentation
```

---

## 6. Data Model (Simplified)

```python
# models/project.py
class Project:
    name: str
    file_path: Path | None
    map_state: MapState
    zones: list[Zone]
    keypoints: list[Keypoint]
    annotations: list[Annotation]
    data_sources: list[DataSource]
    pdf_layout: PDFLayout
    style_presets: list[StylePreset]
    created_at: datetime
    modified_at: datetime

# models/map_state.py
class MapState:
    center_lat: float
    center_lon: float
    zoom: int
    rotation: float
    tile_provider: str       # e.g. "osm_standard", "cartodb_light"
    bookmarks: list[ViewportBookmark]

# models/zone.py
class Zone:
    id: UUID
    name: str
    zone_type: ZoneType          # polygon | rectangle | circle | freehand
    coordinates: list[LatLon]    # vertex list (or center+radius for circle)
    group: str | None
    style: ZoneStyle             # fill_color, border_color, alpha, pattern…
    label: ZoneLabel | None      # text, font, position
    data_binding: DataBinding | None
    metadata: dict               # arbitrary key-value info

# models/keypoint.py
class Keypoint:
    id: UUID
    lat: float
    lon: float
    icon: str                    # icon name or path to custom SVG/PNG
    info_card: InfoCard          # title, subtitle, fields[], image, url, notes
    data_binding: DataBinding | None
    visible: bool

# models/annotation.py
class Annotation:
    id: UUID
    ann_type: AnnotationType     # text_box | callout | legend | title_block | scale_bar | keynote
    position: CanvasPosition     # x, y in canvas coords or lat/lon
    content: str
    style: AnnotationStyle       # font, color, background, border
    target_point: LatLon | None  # for callout arrows

# models/data_source.py
class DataSource:
    id: UUID
    name: str
    source_type: SourceType      # csv | excel | sql | rest_api | gsheets | geojson
    connection: dict             # type-specific connection params
    refresh_mode: RefreshMode    # manual | on_open | interval | webhook
    refresh_interval_sec: int | None
    field_mappings: list[FieldMapping]

class FieldMapping:
    source_column: str
    target_element_type: str     # "zone" | "keypoint"
    target_field: str            # e.g. "style.fill_color", "info_card.fields.revenue"
    transform: str | None        # optional expression like "value / 1000"
```

---

## 7. UI Layout Wireframe

```
┌──────────────────────────────────────────────────────────────────────┐
│  File   Edit   View   Map   Data   Export   Help         [BIMAP]    │
├──────────┬───────────────────────────────────────────┬───────────────┤
│ TOOLBAR  │                                           │               │
│ ──────── │                                           │  PROPERTIES   │
│ [Select] │                                           │  PANEL        │
│ [Pan]    │                                           │ ────────────  │
│ [Polygon]│          MAP CANVAS                       │ Name: [____]  │
│ [Rect]   │       (OpenStreetMap tiles                │ Color: [■]    │
│ [Circle] │        + zone overlays                    │ Alpha: [___]  │
│ [Pin]    │        + keypoint markers                 │ Border: [___] │
│ [Text]   │        + annotations)                     │ Label: [____] │
│ [Callout]│                                           │               │
│ [Keynote]│                                           │ DATA BINDING  │
│          │                                           │ Source: [___] │
│          │                                           │ Field:  [___] │
│          │                                           │               │
├──────────┤                                           ├───────────────┤
│ LAYERS   │                                           │ KEYNOTES      │
│ ──────── │                                           │ ────────────  │
│ □ Zones  │                                           │ ① Store A     │
│   ├ Z1   │                                           │ ② Warehouse   │
│   └ Z2   │                                           │ ③ Risk Area   │
│ □ Points │                                           │               │
│   ├ P1   │                                           │               │
│ □ Notes  │                                           │               │
├──────────┴───────────────────────────────────────────┴───────────────┤
│ Status: Ready  │ Lat: 40.4168  Lon: -3.7038  │ Zoom: 12  │ Sources: 2 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 8. Development Roadmap

### Phase 0 — Foundation (Sprint 1–2)

| # | Task | Description |
|---|---|---|
| 0.1 | Project scaffolding | Set up repo, `pyproject.toml`, virtual env, linting, pre-commit |
| 0.2 | Core models | Implement `Project`, `MapState`, `Zone`, `Keypoint`, `Annotation` with Pydantic |
| 0.3 | Project I/O | Save/load `.bimap` JSON files |
| 0.4 | Main window shell | PyQt6 `QMainWindow` with menu bar, status bar, empty central widget |
| 0.5 | Unit test harness | pytest + pytest-qt fixtures |

**Deliverable**: App launches, creates/saves/loads empty projects.

---

### Phase 1 — Map Canvas (Sprint 3–4)

| # | Task | Description |
|---|---|---|
| 1.1 | Tile math | Lat/lon ↔ tile X/Y conversion, viewport calculations |
| 1.2 | Tile fetcher | Download OSM tiles with HTTP, respect usage policy, rate limit |
| 1.3 | Tile cache | On-disk tile cache with expiry |
| 1.4 | Map widget | Custom `QWidget` painting tiles, handling pan & zoom |
| 1.5 | Geocoding | Search bar → Nominatim → center map on result |
| 1.6 | Multiple tile providers | Switch between OSM, CartoDB, Stamen, etc. |

**Deliverable**: Interactive slippy map in the app window.

---

### Phase 2 — Zones & Drawing Tools (Sprint 5–6)

| # | Task | Description |
|---|---|---|
| 2.1 | Drawing mode manager | Tool state machine (select, draw polygon, draw rect, draw circle) |
| 2.2 | Polygon drawing | Click-to-add-vertex, double-click to close, render overlay |
| 2.3 | Rectangle & circle | Click-drag creation |
| 2.4 | Zone rendering | Paint filled/stroked zones on the map canvas with transparency |
| 2.5 | Zone selection & editing | Click to select, drag handles to reshape, delete |
| 2.6 | Zone properties panel | Edit name, colors, border, label in the side panel |
| 2.7 | Undo/Redo | Command objects for create, move, edit, delete zone |
| 2.8 | GeoJSON import/export | Load/save zone geometries |

**Deliverable**: Draw, style, and edit colored zones on the map.

---

### Phase 3 — Keypoints & Annotations (Sprint 7–8)

| # | Task | Description |
|---|---|---|
| 3.1 | Keypoint placement | Click on map to place; enter coordinates / address |
| 3.2 | Icon rendering | Render SVG/PNG icons at map positions |
| 3.3 | Info card editor | Properties panel fields for title, subtitle, key-values, image, URL |
| 3.4 | Tooltip/popup display | Show info card on hover/click |
| 3.5 | Text box annotations | Place, move, edit rich text on the canvas |
| 3.6 | Callout arrows | Draw arrow from annotation to map point |
| 3.7 | Keynote system | Auto-numbered markers + keynote table |
| 3.8 | Legend generation | Auto-build legend from zones & keypoints |
| 3.9 | Keypoint clustering | Group nearby pins at low zoom |

**Deliverable**: Full annotation capabilities on the map.

---

### Phase 4 — External Data Sources (Sprint 9–11)

| # | Task | Description |
|---|---|---|
| 4.1 | Data source interface | Abstract base class with `connect()`, `fetch()`, `get_columns()` |
| 4.2 | CSV/Excel connector | Read files, detect columns, preview data |
| 4.3 | SQL connector | SQLAlchemy engine, query editor, preview |
| 4.4 | REST API connector | URL, headers, auth config, JSONPath field extraction |
| 4.5 | Google Sheets connector | OAuth2 flow, sheet selection |
| 4.6 | GeoJSON connector | File or URL ingest |
| 4.7 | Data Manager panel | UI to add/edit/test/remove sources |
| 4.8 | Field mapping UI | Visual drag-and-drop column → element property |
| 4.9 | Background refresh | QThread-based scheduler, status indicators |
| 4.10 | Data-driven styling | Zone color/size from data values (gradient, thresholds) |

**Deliverable**: Maps update from live external data.

---

### Phase 5 — PDF Export (Sprint 12–14)

| # | Task | Description |
|---|---|---|
| 5.1 | PDF composer view | Separate tab/window with page canvas (like a print layout) |
| 5.2 | Map frame item | Render map viewport into a positioned rectangle on the page |
| 5.3 | Title block item | Editable title, subtitle, date, author, logo |
| 5.4 | Legend item | Render legend on the page |
| 5.5 | Keynote table item | Numbered list of keynotes |
| 5.6 | Text & image items | Arbitrary text blocks and images on the page |
| 5.7 | PDF rendering engine | Composite all items → ReportLab → PDF |
| 5.8 | Export dialog | Page size, orientation, DPI, filename |
| 5.9 | Multi-page & insets | Support detail inset maps, multi-page reports |
| 5.10 | Batch export | Template × data source → generate N PDFs |

**Deliverable**: Export polished PDF maps.

---

### Phase 6 — Polish & Packaging (Sprint 15–16)

| # | Task | Description |
|---|---|---|
| 6.1 | Template system | Save/load layout + style templates |
| 6.2 | Theme support | Light/dark UI themes |
| 6.3 | Keyboard shortcuts | Full hotkey map |
| 6.4 | Performance | Tile pre-fetching, rendering optimization, large dataset handling |
| 6.5 | Error handling | Graceful errors for network failures, bad data, etc. |
| 6.6 | User guide docs | In-app help + markdown docs |
| 6.7 | PyInstaller build | Single-file Windows executable |
| 6.8 | CI/CD pipeline | GitHub Actions for tests + build |

**Deliverable**: Production-ready distributable application.

---

## 9. Prompt Engineering Guide for AI Coders

> This section helps AI coding assistants (Copilot, Claude, etc.) maintain context and produce consistent code when working on this project.

### 9.1 Context Rules

When starting a new coding session, the AI should:

1. **Read this README first** to understand architecture, naming, and conventions.
2. **Check the current phase** — only implement features for the active phase.
3. **Follow the project structure** in Section 5 exactly — do not invent new directories or flatten the hierarchy.
4. **Use the data models** from Section 6 as the source of truth. If a model needs changes, update the model file first, then propagate.

### 9.2 Coding Conventions

```
- Python 3.11+ features allowed (match/case, tomllib, StrEnum, etc.)
- Type hints on ALL function signatures and class attributes
- Pydantic v2 models for all domain objects (BaseModel with model_config)
- PyQt6 signals/slots for UI ↔ engine communication (never direct calls)
- snake_case for functions/variables, PascalCase for classes
- Constants in UPPER_SNAKE_CASE in config.py
- Imports: stdlib → third-party → local, separated by blank lines
- Max line length: 100 characters
- Docstrings: Google style, only for public methods
- No global mutable state — pass dependencies via constructor injection
```

### 9.3 Prompt Templates

**When implementing a new model:**
```
Implement the [ModelName] Pydantic model in src/bimap/models/[file].py.
Refer to the data model spec in README Section 6. Include:
- All fields with types and defaults
- model_config for JSON serialization
- Any validation logic
- Unit tests in tests/test_models/test_[file].py
```

**When implementing a UI panel:**
```
Implement [PanelName] as a QDockWidget in src/bimap/ui/panels/[file].py.
It should:
- Display [what it shows]
- Allow [user interactions]
- Emit signals when [events happen]
- Connect to the Project model via [controller/signal pattern]
Refer to the UI wireframe in README Section 7 for layout guidance.
```

**When adding a data source connector:**
```
Implement the [SourceType] data source connector in src/bimap/data/[file].py.
It must implement the DataSourceBase interface (see src/bimap/data/base.py):
- connect() → validate connection params
- fetch() → return list of dicts (rows)
- get_columns() → return column names and types
- disconnect() → clean up resources
Add unit tests with mocked external calls.
```

**When implementing a command (undo/redo):**
```
Add a new command class [CommandName] in src/bimap/engine/commands.py.
It must implement:
- execute() → perform the action, update the project model
- undo() → reverse the action exactly
- description() → human-readable string for the Edit menu
Register it in the CommandHistory stack.
```

### 9.4 Anti-Patterns to Avoid

| Don't | Do Instead |
|---|---|
| Embed business logic in QWidget subclasses | Put logic in `engine/` modules; UI only calls engine methods |
| Use `QThread` with `run()` override | Use `QThread` + worker `QObject` with `moveToThread()` pattern |
| Store state in global variables | Store all state in the `Project` model instance |
| Hardcode tile URLs in the widget | Define tile providers in `config.py` as named presets |
| Use `print()` for debugging | Use Python `logging` module with named loggers |
| Catch bare `except:` | Catch specific exceptions; let unexpected errors propagate |
| Import `PyQt6` in model or engine layers | Models and engine must be pure Python — no Qt dependency |

### 9.5 Testing Strategy

- **Unit tests**: All models, engine functions, data connectors (mocked I/O).
- **Widget tests**: Use `pytest-qt` and `qtbot` for UI interaction tests.
- **Integration tests**: Full round-trip: create project → add elements → save → load → verify.
- **Snapshot tests**: PDF output compared to reference images (perceptual diff).
- **Coverage target**: ≥ 80% for models and engine; ≥ 60% for UI.

### 9.6 Dependency Injection Points

To keep code testable and decoupled:

```python
# Tile fetcher — inject to mock in tests
class MapCanvas:
    def __init__(self, tile_fetcher: TileFetcher, ...): ...

# Data source — inject to test without real DB
class DataRefreshWorker:
    def __init__(self, source: DataSourceBase, ...): ...

# PDF renderer — inject to test without file I/O
class PDFExporter:
    def __init__(self, renderer: PDFRenderer, output_path: Path, ...): ...
```

---

## 10. Key Technical Challenges & Solutions

| Challenge | Approach |
|---|---|
| **Smooth tile rendering** | Double-buffered painting; load tiles async in QThread; show placeholder while loading |
| **Accurate zone overlay at all zoom levels** | Convert lat/lon vertices to pixel coords on every repaint using Mercator projection math |
| **PDF fidelity** | Render zones/keypoints as vector graphics (QPainter paths), not raster screenshots |
| **Large datasets** | Virtualized lists in panels; spatial index (R-tree) for visible-element culling |
| **Credential security** | Store DB passwords / API keys in OS keyring (`keyring` library), never in .bimap file |
| **Offline mode** | Cache tiles + last-fetched data; work offline, sync when reconnected |
| **Cross-platform** | PyQt6 is cross-platform; avoid Windows-specific APIs; test on macOS/Linux CI |

---

## 11. Getting Started (Developer Setup)

```bash
# 1. Clone the repository
git clone <repo-url> && cd BIMAP

# 2. Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python -m bimap.app

# 5. Run tests
pytest tests/ -v

# 6. Build executable
pyinstaller --onefile --windowed src/bimap/app.py
```

---

## 12. License & Contributing

- **License**: TBD (recommend MIT or Apache 2.0 for open source)
- **Contributions**: Fork → feature branch → PR with tests → review

---

## 13. Glossary

| Term | Definition |
|---|---|
| **Zone** | A colored polygon/shape on the map representing a geographic area |
| **Keypoint** | A map marker (pin) with an attached information card |
| **Keynote** | A numbered reference marker linked to a description in a separate table |
| **Info Card** | Structured data (title, fields, image) attached to a keypoint |
| **Data Binding** | A link from an external data column to a map element's property |
| **Tile** | A 256×256 px image slice of the map at a given zoom/x/y coordinate |
| **Viewport** | The visible area of the map (center + zoom + rotation) |
| **Composer** | The PDF layout editor where map frames and elements are arranged on a page |
| **`.bimap`** | The project file format (JSON internally) |

---

*This README is the single source of truth for the BIMAP project. Keep it updated as the architecture evolves.*
