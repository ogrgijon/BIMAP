# BIMAP — Business Intelligence Map Designer

> **⚠️ RESEARCH & DEVELOPMENT DISCLAIMER**
>
> This project is an **experimental research prototype** under active development.
> It is shared publicly for learning, exploration, and collaboration purposes only.
>
> - **Not production-ready.** Features may be incomplete, unstable, or change without notice.
> - **No warranty.** The software is provided "as is" without guarantees of correctness, reliability, or fitness for any purpose.
> - **Not for critical use.** Do not use this tool for safety-critical, legal, financial, or medical decision-making.
> - **The authors accept no liability** for any damages, data loss, or consequences arising from the use of this software.
> - Data source credentials (SQL connection strings, API tokens) are stored in plaintext inside `.bimap` project files. **Do not put production credentials into BIMAP projects.**
>
> By using or contributing to this project you acknowledge it is an investigation prototype and accept these terms.

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
10. [Security Notes](#10-security-notes)
11. [License](#11-license)

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

### Portable EXE (recommended — no install required)

```powershell
# Install PyInstaller into the project venv
pip install pyinstaller pyinstaller-hooks-contrib

# Build — produces installer\dist\BIMAP.exe (~60 MB, fully self-contained)
pyinstaller installer\bimap_portable.spec `
    --distpath installer\dist `
    --workpath installer\build `
    --noconfirm

# Or use the build script (renames exe with version number)
.\installer\build_installer.ps1 -Version 0.2.0 -PortableOnly
```

Output: `BIMAP-v0.2.0-windows-x64-portable.exe` — double-click to run, no Python needed.

### Onedir build (for Inno Setup installer)

```powershell
pyinstaller installer\bimap.spec `
    --distpath installer\dist `
    --workpath installer\build `
    --noconfirm
# Output: installer\dist\BIMAP\  (folder)
```

### GitHub Release (automatic)

Push a version tag to trigger the release workflow:

```bash
git tag v0.2.0
git push origin v0.2.0
# GitHub Actions builds and attaches BIMAP-v0.2.0-windows-x64-portable.exe to the Release page
```

---

## 9. Contributing

1. Fork the repository and create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes and add tests where appropriate.
3. Run `python -m pytest tests/ -q` — all tests must pass.
4. Open a Pull Request with a clear description of what changed and why.

Please follow the existing code style (PEP 8, type hints, Pydantic models for domain objects).

---

## 10. Security Notes

### Credential storage
`DataSource` connection parameters (SQL connection strings, API tokens, bearer tokens) are stored **in plaintext** inside `.bimap` project files.

- **Do not commit `.bimap` files containing real credentials** to version control.
- Add your project files to `.gitignore` if they reference production databases or APIs.
- For production use, a secrets-manager integration (e.g. environment variables, Vault) would be required — this is not yet implemented.

### SQL query execution
The SQL connector enforces a `SELECT`-only guard (rejects queries not starting with `SELECT`) and passes queries through SQLAlchemy's `text()` parameterisation. However, **the user constructs the query string** — treat any query from an untrusted source with appropriate caution.

### Network requests
BIMAP fetches map tiles from external providers (OpenStreetMap, CartoDB, etc.) and performs geocoding via Nominatim. Your IP address will be visible to those services. See [OSM Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/) and [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/).

### Expression evaluation
The data-binding transform field uses a **safe AST evaluator** (no `eval()`). Only numeric operators and a whitelist of builtins (`str`, `int`, `float`, `round`, `abs`) are permitted.

---

## 11. License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/).

