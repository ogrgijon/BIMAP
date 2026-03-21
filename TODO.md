# BIMAP — Development TODO

> Last updated: 2026-03-21  
> Test run: **39/39 passed** (exit code 0)

---
##  REMAINING TODO TASKS

> on export pdf text on Architectural Title Block are very very big
> legend box may appears independent
> update readme thinking in publish on github
> add .gitignore



## REMAINING ISSUES

*None at this time.*

---

## SECURITY AUDIT RESULTS

| ID | Severity | Status | Detail |
|----|----------|--------|--------|
| SEC-001 | HIGH | ✅ FIXED | `eval()` replaced with `ast.literal_eval()` |
| SEC-002 | MEDIUM | ✅ FIXED | SQL source validates `SELECT`-only query |
| SEC-003 | LOW | ✅ FIXED | Field-mapping transforms now use `_safe_eval_transform()` — whitelisted AST ops only |
| SEC-004 | LOW | Confirmed safe | All tile provider URLs use HTTPS |
| SEC-005 | LOW | Open | REST API auth token in `DataSource.connection` plain JSON — use `keyring` for credentials at rest |

---

## TEST COVERAGE GAPS

| Area | Current | Target |
|------|---------|--------|
| `engine/tile_math.py` | 85% | 95% |
| `engine/commands.py` | 90% | 95% |
| `engine/project_io.py` | 90% | 95% |
| `ui/map_canvas/` | 40% | 70% |
| `ui/panels/` | 30% | 60% |
| `ui/dialogs/` | 0% | 50% |
| `data/` connectors | 0% | 60% |
| PDF renderer | 0% | 40% |

---

## FIXED (all sessions)

| # | File | Issue | Fix Applied |
|---|------|-------|-------------|
| F1 | `src/bimap/ui/map_canvas/tile_widget.py` | `zoom_in()`, `zoom_out()`, `select_element()` missing | Added all three methods |
| F2 | `src/bimap/config.py` | `AUTOSAVE_INTERVAL_MS` constant defined twice | Removed duplicate |
| F3 | `src/bimap/ui/main_window.py` | `eval()` in `_apply_mappings()` — OWASP A03 Injection | Replaced with `_safe_eval_transform()` (whitelisted AST) |
| F4 | `.vscode/launch.json` | Only duplicate "Current File" configs | Replaced with 7 BIMAP-specific debug profiles |
| F5 | `src/bimap/app.py` | `AA_UseHighDpiPixmaps` crash on Qt 6.7+ | Removed deprecated attribute call |
| F6 | `src/bimap/engine/tile_math.py` | `lat_lon_to_tile_float` / `tile_to_lat_lon` returned plain tuples | Added `TileFloatCoord` / `LatLonCoord` NamedTuples |
| F7 | `src/bimap/models/zone.py` | Missing `locked` field | Added `locked: bool = False` |
| F8 | `src/bimap/models/keypoint.py` | Missing `name` property | Added `name` property proxying `info_card.title` |
| F9 | `src/bimap/engine/commands.py` | Add/remove data source not undoable | Added `AddDataSourceCommand`, `RemoveDataSourceCommand` |
| F10 | `src/bimap/data/sql_source.py` | No SELECT-only guard | Added SELECT prefix validation |
| F11 | `src/bimap/ui/map_canvas/tile_fetcher.py` | No network retry / no cancellation | Added retry+backoff + `_cancelled` flag |
| F12 | `src/bimap/engine/pdf_renderer.py` | No headless guard | Added offscreen platform guard |
| F13 | `src/bimap/ui/map_canvas/tile_widget.py` | Unbounded tile cache, broken zoom-to-cursor | LRU eviction (300 tiles), fixed zoom-to-cursor math |
| F14 | `src/bimap/ui/map_canvas/interaction.py` | No `set_selected()`, locked zones not honoured, `LatLon(*...)` crash | Added `set_selected()`, locked guard, fixed positional-arg crash |
| F15 | `src/bimap/ui/map_canvas/overlay_renderer.py` | No selection highlight, no scale bar, no north arrow | Added selection outline, scale bar, north arrow |
| F16 | `src/bimap/ui/main_window.py` | Missing recent files, bookmarks, GeoJSON import, print preview, undo for data sources | All added + wired |
| F17 | `.github/workflows/ci.yml` | No CI pipeline | Created GitHub Actions workflow |
| F18 | `tests/conftest.py` + `tests/test_ui_widgets.py` | Qt teardown crash (exit code 1) | `_cancelled` flag + `waitForDone(-1)` in fixture teardown |
| F19 | `src/bimap/ui/map_canvas/tile_widget.py` | `_refresh_tiles()` called on every mouse-move during pan | Added 50 ms `QTimer` debounce |
| F20 | `src/bimap/ui/main_window.py` | `ast.literal_eval` limited to literals only | Replaced with `_safe_eval_transform()` supporting arithmetic + whitelisted calls |
| F21 | `src/bimap/ui/panels/properties_panel.py` | No style-presets UI | Added preset combo-box in zone properties, `preset_applied` signal, `_on_preset_applied` handler |
| F22 | `installer/bimap.ico` | Icon file missing (referenced by PyInstaller spec + ISS) | Added `installer/create_icon.py`; icon generated at 16/32/48/64/256 px |
| F23 | `bump_version.py` | Version duplicated in `pyproject.toml` and `config.py` | Created `bump_version.py` script to sync both files |
| F24 | `src/bimap/ui/map_canvas/tile_widget.py` + `main_window.py` | No right-click context menu | Added `contextMenuEvent`, `_hit_test`, `context_action_requested` signal; wired Remove/Edit/Move handlers |
| F25 | `src/bimap/ui/map_canvas/interaction.py` + `overlay_renderer.py` + `toolbar.py` | No magic-wand area multi-select | Added `MAGIC_WAND` tool mode, lasso draw/preview, `multi_select_finished` signal, orange multi-select overlay; wired `RemoveMultipleCommand` |
| F26 | `src/bimap/engine/delimitation.py` + `src/bimap/ui/dialogs/delimitation_dialog.py` + `main_window.py` | No delimitation/boundary overlay | Created Nominatim polygon fetcher, `DelimitationDialog`, `_draw_delimitation()` vignette in overlay renderer; Map → Set/Clear Delimitation menu items |
| F27 | `src/bimap/ui/main_window.py` | Print preview dialog opens maximized | Added `dlg.resize(900, 700)` before exec |
| F28 | `src/bimap/engine/pdf_renderer.py` + `pyproject.toml` | ReportLab dependency — replaced with `QPdfWriter` | Full rewrite using `QPdfWriter`/`QPainter` only; `reportlab` removed from dependencies |
| F29 | `src/bimap/ui/toolbar.py` | Flat tool list with no grouping | Reorganised into 5 labelled groups: SEARCH, CREATE, ⬇ Import, ⬆ Export, 🖶 Print; new `import_requested`, `export_requested`, `print_requested` signals wired in `main_window.py` |
| F30 | `src/bimap/ui/panels/properties_panel.py` | Small color swatches with no hex label; plain group boxes | `ColorButton` now shows hex code with auto-contrasting text, taller swatch, monospace font; panel title styled; `QGroupBox` styled with rounded corners and better typography; form spacing improved |
