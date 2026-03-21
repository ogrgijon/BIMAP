"""
Main application window.

Wires together:
  - TileWidget (map canvas)
  - LayersPanel, PropertiesPanel, DataPanel, KeynotesPanel (dock widgets)
  - MapToolbar
  - Menu bar (File, Edit, View, Map, Data, Export, Help)
  - QUndoStack (Edit → Undo/Redo)
  - DataRefreshManager
  - Project state management (new, open, save, autosave)
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from PyQt6.QtCore import QSettings, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QUndoStack
from PyQt6.QtPrintSupport import QPrintPreviewDialog, QPrinter, QPrinter
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QStatusBar,
    QWidget,
)

import ast
import operator as _op

from bimap.config import APP_NAME, APP_VERSION, AUTOSAVE_INTERVAL_MS, PROJECT_FILE_EXTENSION
from bimap.data import DataRefreshManager, build_connector
from bimap.engine.commands import (
    AddAnnotationCommand,
    AddDataSourceCommand,
    AddKeypointCommand,
    AddZoneCommand,
    EditAnnotationCommand,
    EditKeypointCommand,
    EditZoneCommand,
    MoveElementCommand,
    RemoveAnnotationCommand,
    RemoveDataSourceCommand,
    RemoveKeypointCommand,
    RemoveMultipleCommand,
    RemoveZoneCommand,
)
from bimap.engine.project_io import ProjectIOError, export_backup, import_backup, load_project, save_project
from bimap.models.data_source import DataSource, RefreshMode
from bimap.models.keypoint import Keypoint
from bimap.models.project import Project
from bimap.models.zone import LatLon, Zone, ZoneType
from bimap.ui.dialogs import DataSourceDialog, DelimitationDialog, ExportDialog, GeocodeDialog, MapComposerDialog, MetadataViewDialog
from bimap.ui.map_canvas import TileWidget, ToolMode
from bimap.ui.panels import DataPanel, KeynotesPanel, LayersPanel, PropertiesPanel
from bimap.ui.toolbar import MapToolbar, SearchBar

_RECENT_FILES_KEY = "recentFiles"
_MAX_RECENT = 10

# ── Safe expression evaluator for field-mapping transforms ─────────────────────

_SAFE_BINOPS: dict = {
    ast.Add: _op.add,
    ast.Sub: _op.sub,
    ast.Mult: _op.mul,
    ast.Div: _op.truediv,
    ast.FloorDiv: _op.floordiv,
    ast.Mod: _op.mod,
    ast.Pow: _op.pow,
}
_SAFE_UNARYOPS: dict = {ast.USub: _op.neg, ast.UAdd: _op.pos}
_SAFE_CALLS: dict = {"str": str, "int": int, "float": float, "round": round, "abs": abs}


def _safe_eval_transform(expr: str, value: Any) -> Any:
    """Evaluate an arithmetic transform expression with ``value`` as the input.

    Supported: numeric/string literals, the name ``value``, arithmetic
    operators (+, -, *, /, //, %, **), and a whitelist of built-in calls
    (str, int, float, round, abs).  Everything else raises ``ValueError``.
    """
    tree = ast.parse(expr, mode="eval")

    def _eval(node: ast.AST) -> Any:
        match node:
            case ast.Constant():
                return node.value
            case ast.Name(id="value"):
                return value
            case ast.BinOp():
                fn = _SAFE_BINOPS.get(type(node.op))
                if fn is None:
                    raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
                return fn(_eval(node.left), _eval(node.right))
            case ast.UnaryOp():
                fn = _SAFE_UNARYOPS.get(type(node.op))
                if fn is None:
                    raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
                return fn(_eval(node.operand))
            case ast.Call():
                if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_CALLS:
                    raise ValueError("Only whitelisted calls are allowed: str/int/float/round/abs")
                return _SAFE_CALLS[node.func.id](*(_eval(a) for a in node.args))
            case _:
                raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

    return _eval(tree.body)


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self._project: Project = Project()
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(100)
        self._refresh_manager = DataRefreshManager(self)
        self._selected: tuple[str, str] | None = None   # (element_type, id_str)
        self._settings = QSettings(APP_NAME, APP_NAME)

        self._setup_ui()
        self._setup_menus()
        self._setup_autosave()
        self._connect_signals()
        self._refresh_all()

        self.setWindowTitle(f"{APP_NAME} — {self._project.name}")
        self.resize(1280, 800)

    # ── UI Setup ───────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        # Tool toolbar (top)
        self._toolbar = MapToolbar(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

        # Search bar (second row in top area)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self._search_bar = SearchBar(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._search_bar)

        # Central map canvas
        self._canvas = TileWidget(self)
        self._canvas.set_project(self._project)
        self.setCentralWidget(self._canvas)

        # Dock: Layers (left)
        self._layers_panel = LayersPanel()
        layers_dock = QDockWidget("Layers", self)
        layers_dock.setWidget(self._layers_panel)
        layers_dock.setMinimumWidth(180)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, layers_dock)

        # Dock: Properties (right)
        self._props_panel = PropertiesPanel()
        self._props_dock = QDockWidget("Properties", self)
        self._props_dock.setWidget(self._props_panel)
        self._props_dock.setMinimumWidth(220)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._props_dock)

        # Dock: Keynotes (right, below properties)
        self._keynotes_panel = KeynotesPanel()
        keynotes_dock = QDockWidget("Keynotes", self)
        keynotes_dock.setWidget(self._keynotes_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, keynotes_dock)

        # Dock: Data Sources (right bottom)
        self._data_panel = DataPanel()
        data_dock = QDockWidget("Data Sources", self)
        data_dock.setWidget(self._data_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, data_dock)

        # Tabify right-side docks
        self.tabifyDockWidget(self._props_dock, keynotes_dock)
        self.tabifyDockWidget(keynotes_dock, data_dock)
        self._props_dock.raise_()

        # Status bar
        self._status_bar = self.statusBar()
        self._coord_label = QLabel("Lat: — Lon: —")
        self._zoom_label = QLabel("Zoom: —")
        self._source_label = QLabel("Sources: 0")
        self._status_bar.addPermanentWidget(self._coord_label)
        self._status_bar.addPermanentWidget(QLabel(" | "))
        self._status_bar.addPermanentWidget(self._zoom_label)
        self._status_bar.addPermanentWidget(QLabel(" | "))
        self._status_bar.addPermanentWidget(self._source_label)

    def _setup_menus(self) -> None:
        mb = self.menuBar()

        # ── File ────────────────────────────────
        file_menu = mb.addMenu("File")
        act_new = QAction("New Project", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._cmd_new)
        file_menu.addAction(act_new)

        act_open = QAction("Open…", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._cmd_open)
        file_menu.addAction(act_open)

        # Recent files sub-menu
        self._recent_menu = file_menu.addMenu("Recent Projects")
        self._rebuild_recent_menu()

        file_menu.addSeparator()

        act_save = QAction("Save", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._cmd_save)
        file_menu.addAction(act_save)

        act_save_as = QAction("Save As…", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.triggered.connect(self._cmd_save_as)
        file_menu.addAction(act_save_as)

        file_menu.addSeparator()
        act_import = QAction("Import GeoJSON…", self)
        act_import.triggered.connect(self._cmd_import_geojson)
        file_menu.addAction(act_import)

        file_menu.addSeparator()
        act_backup_exp = QAction("📤  Export Data Backup…", self)
        act_backup_exp.setToolTip("Save a portable backup file you can transfer to another PC")
        act_backup_exp.triggered.connect(self._cmd_export_backup)
        file_menu.addAction(act_backup_exp)
        act_backup_imp = QAction("📥  Import Data Backup…", self)
        act_backup_imp.setToolTip("Load a backup or .bimap file and replace the current project")
        act_backup_imp.triggered.connect(self._cmd_import_backup)
        file_menu.addAction(act_backup_imp)

        file_menu.addSeparator()
        act_export = QAction("Print / Export PDF…", self)
        act_export.setShortcut(QKeySequence("Ctrl+P"))
        act_export.triggered.connect(self._cmd_print_export)
        file_menu.addAction(act_export)

        file_menu.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(QApplication.quit)
        file_menu.addAction(act_quit)

        # ── Edit ────────────────────────────────
        edit_menu = mb.addMenu("Edit")
        act_undo = self._undo_stack.createUndoAction(self, "Undo")
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(act_undo)

        act_redo = self._undo_stack.createRedoAction(self, "Redo")
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(act_redo)

        edit_menu.addSeparator()
        act_del = QAction("Delete Selected", self)
        act_del.setShortcut(QKeySequence.StandardKey.Delete)
        act_del.triggered.connect(self._cmd_delete_selected)
        edit_menu.addAction(act_del)

        # ── Create (quick access for new users) ──
        edit_menu.addSeparator()
        _create_tools = [
            ("Draw Polygon Zone",    "Ctrl+Shift+P", ToolMode.DRAW_POLYGON),
            ("Draw Rectangle Zone",  "Ctrl+Shift+R", ToolMode.DRAW_RECTANGLE),
            ("Draw Circle Zone",     "Ctrl+Shift+C", ToolMode.DRAW_CIRCLE),
            ("Place Keypoint",       "Ctrl+Shift+K", ToolMode.DRAW_KEYPOINT),
            ("Place Text Annotation","Ctrl+Shift+T", ToolMode.DRAW_TEXT),
        ]
        for label, shortcut, mode in _create_tools:
            act = QAction(label, self)
            act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(lambda _checked=False, m=mode: self._canvas.set_tool(m))
            edit_menu.addAction(act)

        # ── View ────────────────────────────────
        view_menu = mb.addMenu("View")
        act_save_bm = QAction("Save Bookmark…", self)
        act_save_bm.setShortcut(QKeySequence("Ctrl+B"))
        act_save_bm.triggered.connect(self._cmd_save_bookmark)
        view_menu.addAction(act_save_bm)

        self._bookmarks_menu = view_menu.addMenu("Bookmarks")
        self._rebuild_bookmarks_menu()

        # ── Map ─────────────────────────────────
        map_menu = mb.addMenu("Map")
        act_search = QAction("Search Location…", self)
        act_search.setShortcut(QKeySequence("Ctrl+F"))
        act_search.triggered.connect(self._cmd_search_location)
        map_menu.addAction(act_search)

        act_zoom_in = QAction("Zoom In", self)
        act_zoom_in.setShortcut(QKeySequence("+"))
        act_zoom_in.triggered.connect(self._cmd_zoom_in)
        map_menu.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom Out", self)
        act_zoom_out.setShortcut(QKeySequence("-"))
        act_zoom_out.triggered.connect(self._cmd_zoom_out)
        map_menu.addAction(act_zoom_out)

        map_menu.addSeparator()
        act_delimit = QAction("Set Delimitation…", self)
        act_delimit.triggered.connect(self._cmd_set_delimitation)
        map_menu.addAction(act_delimit)

        act_clear_delimit = QAction("Clear Delimitation", self)
        act_clear_delimit.triggered.connect(self._cmd_clear_delimitation)
        map_menu.addAction(act_clear_delimit)

        # ── Data ────────────────────────────────
        data_menu = mb.addMenu("Data")
        act_add_src = QAction("Add Data Source…", self)
        act_add_src.triggered.connect(self._cmd_add_data_source)
        data_menu.addAction(act_add_src)

        act_refresh_all = QAction("Refresh All Sources", self)
        act_refresh_all.triggered.connect(self._cmd_refresh_all_sources)
        data_menu.addAction(act_refresh_all)

        # ── Help ────────────────────────────────
        help_menu = mb.addMenu("Help")
        act_about = QAction(f"About {APP_NAME}", self)
        act_about.triggered.connect(self._cmd_about)
        help_menu.addAction(act_about)

    def _setup_autosave(self) -> None:
        timer = QTimer(self)
        timer.setInterval(AUTOSAVE_INTERVAL_MS)
        timer.timeout.connect(self._autosave)
        timer.start()

    # ── Signal connections ─────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        # Toolbar
        self._toolbar.tool_selected.connect(self._on_tool_selected)
        self._toolbar.import_requested.connect(self._cmd_import_geojson)
        self._toolbar.print_requested.connect(self._cmd_print_export)
        # Search bar
        self._search_bar.tile_provider_changed.connect(self._on_provider_changed)
        self._search_bar.zoom_in_requested.connect(self._cmd_zoom_in)
        self._search_bar.zoom_out_requested.connect(self._cmd_zoom_out)
        self._search_bar.search_requested.connect(self._on_search_requested)

        # Map canvas
        self._canvas.viewport_changed.connect(self._on_viewport_changed)
        self._canvas.draw_finished.connect(self._on_draw_finished)
        self._canvas.element_selected.connect(self._on_element_selected)
        self._canvas.coordinates_changed.connect(self._on_coords_changed)
        self._canvas.context_action_requested.connect(self._on_context_action)
        self._canvas.multi_select_finished.connect(self._on_multi_select)
        self._canvas.element_move_dropped.connect(self._on_element_move_dropped)
        self._canvas.add_annotation_requested.connect(self._on_add_annotation_at)

        # Layers panel
        self._layers_panel.element_selected.connect(self._on_element_selected)
        self._layers_panel.element_visibility_changed.connect(self._on_visibility_changed)
        self._layers_panel.element_delete_requested.connect(
            lambda et, eid: self._delete_element(et, eid)
        )
        self._layers_panel.layer_visibility_changed.connect(self._on_layer_visibility_changed)
        self._layers_panel.layer_add_requested.connect(self._on_layer_add_requested)
        self._layers_panel.layer_remove_requested.connect(self._on_layer_remove_requested)
        self._layers_panel.element_action_requested.connect(self._on_layer_element_action)
        self._layers_panel.element_layer_changed.connect(self._on_element_layer_changed)

        # Properties panel
        self._props_panel.element_changed.connect(self._on_property_changed)
        self._props_panel.preset_applied.connect(self._on_preset_applied)
        self._props_panel.metadata_changed.connect(self._on_metadata_changed)

        # Keynotes panel
        self._keynotes_panel.assign_keynote_requested.connect(self._assign_keynote)
        self._keynotes_panel.clear_keynote_requested.connect(self._clear_keynote)
        self._keynotes_panel.keynote_selected.connect(
            lambda eid: self._on_element_selected("keypoint", eid)
        )

        # Data panel
        self._data_panel.add_requested.connect(self._cmd_add_data_source)
        self._data_panel.edit_requested.connect(self._cmd_edit_data_source)
        self._data_panel.remove_requested.connect(self._cmd_remove_data_source)
        self._data_panel.refresh_requested.connect(self._refresh_manager.refresh_now)

        # Refresh manager
        self._refresh_manager.data_refreshed.connect(self._on_data_refreshed)
        self._refresh_manager.refresh_error.connect(self._on_refresh_error)

    # ── Refresh / update helpers ───────────────────────────────────────────────

    def _refresh_all(self) -> None:
        self._layers_panel.refresh(self._project)
        self._keynotes_panel.refresh(self._project)
        self._data_panel.refresh(self._project)
        self._canvas.update()
        self._zoom_label.setText(f"Zoom: {self._project.map_state.zoom}")
        self._source_label.setText(f"Sources: {len(self._project.data_sources)}")

    def _set_project(self, project: Project) -> None:
        self._project = project
        self._undo_stack.clear()
        self._canvas.set_project(project)
        self._props_panel.set_project(project)
        self._search_bar.set_tile_provider(project.map_state.tile_provider)
        self._refresh_all()
        self._rebuild_bookmarks_menu()
        self.setWindowTitle(f"{APP_NAME} — {project.name}")

    # ── Commands (menu / toolbar actions) ─────────────────────────────────────

    def _cmd_new(self) -> None:
        if not self._confirm_discard():
            return
        self._set_project(Project())

    def _cmd_open(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "",
            f"BIMAP Projects (*{PROJECT_FILE_EXTENSION});;All Files (*.*)"
        )
        if not path:
            return
        try:
            project = load_project(Path(path))
            self._set_project(project)
            self._add_recent(path)
        except ProjectIOError as exc:
            QMessageBox.critical(self, "Open Failed", str(exc))

    def _cmd_save(self) -> None:
        if self._project.file_path:
            self._save_to(Path(self._project.file_path))
        else:
            self._cmd_save_as()

    def _cmd_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", self._project.name,
            f"BIMAP Projects (*{PROJECT_FILE_EXTENSION})"
        )
        if path:
            self._save_to(Path(path))

    def _save_to(self, path: Path) -> None:
        # Sync canvas viewport back to project
        self._project.map_state.center_lat = self._canvas.center_lat
        self._project.map_state.center_lon = self._canvas.center_lon
        self._project.map_state.zoom = self._canvas.zoom
        try:
            save_project(self._project, path)
            self._add_recent(str(path))
            self.setWindowTitle(f"{APP_NAME} — {self._project.name}")
            self.statusBar().showMessage(f"Saved: {path}", 3000)
        except ProjectIOError as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    def _autosave(self) -> None:
        if self._project.file_path and not self._undo_stack.isClean():
            self._save_to(Path(self._project.file_path))

    def _cmd_print_export(self) -> None:
        """Open Map Composer — user can then choose Export PDF or Print."""
        layer_names = [z.name for z in self._project.zones]
        dlg = MapComposerDialog(
            layout=self._project.pdf_layout,
            current_zoom=self._project.map_state.zoom,
            layer_names=layer_names,
            parent=self,
            canvas_widget=self._canvas,
            project_layers=self._project.zones,
            project_name=getattr(self._project, "name", ""),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if dlg.accepted_as == "export":
            from bimap.engine.pdf_renderer import render_pdf
            try:
                render_pdf(self._project, dlg.output_path)
                self.statusBar().showMessage(f"PDF exported → {dlg.output_path}", 6000)
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", str(exc))
        else:
            try:
                preview = QPrintPreviewDialog(self)
                preview.resize(900, 700)
                preview.paintRequested.connect(self._print_map)
                preview.exec()
            except Exception as exc:
                QMessageBox.critical(self, "Print Error", str(exc))

    def _print_map(self, printer: "QPrinter") -> None:
        from PyQt6.QtGui import QPainter
        from bimap.engine.pdf_renderer import _render_page
        pr = printer.pageRect(QPrinter.Unit.DevicePixel).toRect()
        painter = QPainter(printer)
        _render_page(painter, self._project, pr.width(), pr.height(), printer.resolution())
        painter.end()

    def _cmd_import_geojson(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import GeoJSON", "", "GeoJSON Files (*.geojson *.json);;All Files (*.*)"
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            features = data.get("features", []) if data.get("type") == "FeatureCollection" else []
            imported = 0
            for feat in features:
                geom = feat.get("geometry", {})
                props = feat.get("properties") or {}
                name = (props.get("name") or props.get("title")
                        or props.get("Name") or "Zone")
                coords_raw = geom.get("coordinates", [])
                gtype = geom.get("type", "")
                if gtype == "Polygon" and coords_raw:
                    ring = coords_raw[0]
                    coords = [LatLon(lat=c[1], lon=c[0]) for c in ring]
                    zone = Zone(name=name, zone_type=ZoneType.POLYGON, coordinates=coords)
                    zone.label.text = name
                    cmd = AddZoneCommand(self._project, zone, self._refresh_all)
                    self._undo_stack.push(cmd)
                    imported += 1
                elif gtype == "MultiPolygon" and coords_raw:
                    for poly in coords_raw:
                        ring = poly[0]
                        coords = [LatLon(lat=c[1], lon=c[0]) for c in ring]
                        zone = Zone(name=name, zone_type=ZoneType.POLYGON, coordinates=coords)
                        zone.label.text = name
                        cmd = AddZoneCommand(self._project, zone, self._refresh_all)
                        self._undo_stack.push(cmd)
                        imported += 1
            self.statusBar().showMessage(f"GeoJSON: imported {imported} zone(s).", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))

    def _cmd_export_backup(self) -> None:
        """Export the current project as a portable ZIP backup file."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Data Backup", "", "BIMAP Backup (*.bimap.zip);;All Files (*.*)"
        )
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"
        try:
            export_backup(self._project, Path(path))
            QMessageBox.information(
                self, "Backup Exported",
                f"Backup saved to:\n{path}\n\nCopy this file to transfer your project to another PC."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _cmd_import_backup(self) -> None:
        """Load a project from a ZIP backup or .bimap file, replacing the current project."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Data Backup",
            "", "Backup / Project files (*.bimap.zip *.zip *.bimap);;All Files (*.*)"
        )
        if not path:
            return
        reply = QMessageBox.question(
            self, "Replace Project?",
            "This will replace the current project with the backup.\n"
            "Unsaved changes will be lost. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            project = import_backup(Path(path))
            self._set_project(project)
            self.statusBar().showMessage("Backup imported successfully.", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))

    def _cmd_save_bookmark(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Bookmark", "Bookmark name:")
        if ok and name.strip():
            bm = {
                "name": name.strip(),
                "lat": self._canvas.center_lat,
                "lon": self._canvas.center_lon,
                "zoom": self._canvas.zoom,
            }
            if not hasattr(self._project.map_state, "bookmarks"):
                self._project.map_state.__dict__.setdefault("bookmarks", [])
            bookmarks = getattr(self._project.map_state, "bookmarks", [])
            bookmarks.append(bm)
            self._project.mark_modified()
            self._rebuild_bookmarks_menu()

    def _rebuild_bookmarks_menu(self) -> None:
        self._bookmarks_menu.clear()
        bookmarks = getattr(self._project.map_state, "bookmarks", [])
        if not bookmarks:
            no_action = QAction("(no bookmarks)", self)
            no_action.setEnabled(False)
            self._bookmarks_menu.addAction(no_action)
            return
        for bm in bookmarks:
            act = QAction(bm["name"], self)
            lat, lon, zoom = bm["lat"], bm["lon"], bm["zoom"]
            act.triggered.connect(lambda _=False, la=lat, lo=lon, z=zoom:
                                  self._canvas.set_viewport(la, lo, z))
            self._bookmarks_menu.addAction(act)

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        paths = self._settings.value(_RECENT_FILES_KEY, []) or []
        if not paths:
            act = QAction("(no recent files)", self)
            act.setEnabled(False)
            self._recent_menu.addAction(act)
            return
        for p in paths:
            act = QAction(p, self)
            act.triggered.connect(lambda _=False, path=p: self._open_recent(path))
            self._recent_menu.addAction(act)
        self._recent_menu.addSeparator()
        clr = QAction("Clear Recent", self)
        clr.triggered.connect(self._clear_recent)
        self._recent_menu.addAction(clr)

    def _add_recent(self, path: str) -> None:
        paths = list(self._settings.value(_RECENT_FILES_KEY, []) or [])
        if path in paths:
            paths.remove(path)
        paths.insert(0, path)
        paths = paths[:_MAX_RECENT]
        self._settings.setValue(_RECENT_FILES_KEY, paths)
        self._rebuild_recent_menu()

    def _clear_recent(self) -> None:
        self._settings.remove(_RECENT_FILES_KEY)
        self._rebuild_recent_menu()

    def _open_recent(self, path: str) -> None:
        if not self._confirm_discard():
            return
        try:
            project = load_project(Path(path))
            self._set_project(project)
            self._add_recent(path)
        except (ProjectIOError, FileNotFoundError) as exc:
            QMessageBox.critical(self, "Open Failed", str(exc))

    def _cmd_delete_selected(self) -> None:
        if self._selected:
            self._delete_element(*self._selected)

    def _cmd_search_location(self) -> None:
        dlg = GeocodeDialog(self)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.result:
            r = dlg.result
            self._canvas.set_viewport(r.lat, r.lon, self._canvas.zoom)

    def _on_search_requested(self, query: str) -> None:
        """Run a geocode query from the toolbar search bar in a background thread."""
        from PyQt6.QtCore import QThreadPool
        from bimap.engine.geocoding import GeocoderWorker
        worker = GeocoderWorker(query)
        worker.signals.result.connect(
            lambda r: self._canvas.set_viewport(r.lat, r.lon, self._canvas.zoom)
        )
        worker.signals.error.connect(
            lambda msg: self.statusBar().showMessage(msg, 3000)
        )
        QThreadPool.globalInstance().start(worker)

    def _cmd_zoom_in(self) -> None:
        self._canvas.set_viewport(
            self._canvas.center_lat,
            self._canvas.center_lon,
            self._canvas.zoom + 1,
        )

    def _cmd_zoom_out(self) -> None:
        self._canvas.set_viewport(
            self._canvas.center_lat,
            self._canvas.center_lon,
            self._canvas.zoom - 1,
        )

    def _cmd_add_data_source(self) -> None:
        dlg = DataSourceDialog(parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            ds = dlg.source
            try:
                connector = build_connector(ds)
                connector.connect()
            except ValueError as exc:
                ds.last_error = str(exc)
                connector = None
            notify = lambda: (
                self._data_panel.refresh(self._project),
                self._source_label.setText(f"Sources: {len(self._project.data_sources)}"),
            )
            cmd = AddDataSourceCommand(
                self._project, ds, self._refresh_manager, connector, notify
            )
            self._undo_stack.push(cmd)

    def _cmd_edit_data_source(self, source_id: str) -> None:
        ds = self._find_source(source_id)
        if not ds:
            return
        dlg = DataSourceDialog(copy.deepcopy(ds), parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            idx = next(i for i, s in enumerate(self._project.data_sources)
                       if str(s.id) == source_id)
            self._project.data_sources[idx] = dlg.source
            self._project.mark_modified()
            self._data_panel.refresh(self._project)

    def _cmd_remove_data_source(self, source_id: str) -> None:
        notify = lambda: (
            self._data_panel.refresh(self._project),
            self._source_label.setText(f"Sources: {len(self._project.data_sources)}"),
        )
        cmd = RemoveDataSourceCommand(
            self._project, source_id, self._refresh_manager, notify
        )
        self._undo_stack.push(cmd)

    def _cmd_refresh_all_sources(self) -> None:
        for ds in self._project.data_sources:
            if ds.enabled:
                self._refresh_manager.refresh_now(str(ds.id))

    def _cmd_about(self) -> None:
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            "<p>Business Intelligence Map Designer</p>"
            "<p>Open Source Based: Python, PyQt6 and OpenStreetMap.</p>"
            "<p>Developed with love by OGRGijón for the community.</p>",
        )

    def _cmd_set_delimitation(self) -> None:
        current = getattr(self._project.map_state, "delimitation_name", "")
        dlg = DelimitationDialog(current_name=current, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        if dlg.clear_mode:
            self._cmd_clear_delimitation()
            return
        result = dlg.result_item
        if not result:
            return
        poly = result.polygon if result.polygon else result.bbox_polygon()
        self._project.map_state.delimitation_name = result.name
        self._project.map_state.delimitation_polygon = poly
        self._project.mark_modified()
        self._canvas.set_viewport(result.lat, result.lon, self._canvas.zoom)
        self._canvas.update()
        self.statusBar().showMessage(f"Delimitation set: {result.name}", 4000)

    def _cmd_clear_delimitation(self) -> None:
        self._project.map_state.delimitation_polygon = None
        self._project.map_state.delimitation_name = ""
        self._project.mark_modified()
        self._canvas.update()
        self.statusBar().showMessage("Delimitation cleared.", 3000)

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _on_tool_selected(self, mode: str) -> None:
        self._canvas.set_tool(ToolMode(mode))

    def _on_provider_changed(self, key: str) -> None:
        self._canvas.set_tile_provider(key)
        self._project.map_state.tile_provider = key

    def _on_viewport_changed(self, lat: float, lon: float, zoom: int) -> None:
        self._project.map_state.center_lat = lat
        self._project.map_state.center_lon = lon
        self._project.map_state.zoom = zoom
        self._zoom_label.setText(f"Zoom: {zoom}")

    def _on_coords_changed(self, lat: float, lon: float) -> None:
        self._coord_label.setText(f"Lat: {lat:.5f}  Lon: {lon:.5f}")

    def _on_draw_finished(self, element_type: str, element: Any) -> None:
        # Auto-populate metadata with computed spatial fields
        if element_type == "zone" and element.coordinates:
            coords = element.coordinates
            clat = sum(c.lat for c in coords) / len(coords)
            clon = sum(c.lon for c in coords) / len(coords)
            import math as _math
            # Shoelace area in deg² → approx m²
            n = len(coords)
            deg2_area = abs(sum(
                coords[i].lon * coords[(i + 1) % n].lat
                - coords[(i + 1) % n].lon * coords[i].lat
                for i in range(n)
            )) / 2.0
            m2 = deg2_area * (111_320 ** 2) * _math.cos(_math.radians(clat))
            element.metadata.setdefault("area_m2", str(round(m2, 1)))
            element.metadata.setdefault("center_lat", str(round(clat, 6)))
            element.metadata.setdefault("center_lon", str(round(clon, 6)))
        elif element_type == "keypoint":
            element.metadata.setdefault("lat", str(round(element.lat, 6)))
            element.metadata.setdefault("lon", str(round(element.lon, 6)))

        notify = self._refresh_all
        match element_type:
            case "zone":
                cmd = AddZoneCommand(self._project, element, notify)
            case "keypoint":
                cmd = AddKeypointCommand(self._project, element, notify)
            case "annotation":
                cmd = AddAnnotationCommand(self._project, element, notify)
            case _:
                return
        self._undo_stack.push(cmd)
        # Auto-select newly created element
        self._on_element_selected(element_type, str(element.id))

    def _on_element_selected(self, element_type: str, element_id: str) -> None:
        self._selected = (element_type, element_id)
        element = self._find_element(element_type, element_id)
        if element:
            self._props_panel.show_element(element, element_type)
        self._layers_panel.select_element(element_type, element_id)
        self._canvas.select_element(element_type, element_id)

    def _on_preset_applied(self, element_type: str, element_id: str, preset_name: str) -> None:
        """Apply a named style preset to the selected zone in one undoable step."""
        if element_type != "zone":
            return
        zone = self._find_element("zone", element_id)
        if not zone:
            return
        preset = next((p for p in self._project.style_presets if p.name == preset_name), None)
        if not preset:
            return
        old = copy.deepcopy(zone)
        zone.style = copy.deepcopy(preset.zone_style)
        zone.label.style = copy.deepcopy(preset.label_style)
        new = copy.deepcopy(zone)
        notify = lambda: (self._canvas.update(), self._layers_panel.refresh(self._project))
        self._undo_stack.push(EditZoneCommand(self._project, old, new, notify))
        self._project.mark_modified()

    def _on_metadata_changed(self, element_type: str, element_id: str,
                              key: str, value: object) -> None:
        """Push a SetMetadataCommand for any key-value edit from the properties panel."""
        from bimap.engine.commands import SetMetadataCommand
        notify = lambda: (self._canvas.update(), self._layers_panel.refresh(self._project))
        cmd = SetMetadataCommand(
            self._project, element_type, element_id,
            key, value if value is not None else None, notify
        )
        self._undo_stack.push(cmd)

    def _on_visibility_changed(self, element_type: str, element_id: str, visible: bool) -> None:
        element = self._find_element(element_type, element_id)
        if element and hasattr(element, "visible"):
            element.visible = visible
            self._project.mark_modified()
            self._canvas.update()

    def _on_layer_visibility_changed(self, layer_name: str, visible: bool) -> None:
        """Toggle visibility of a layer and all its elements."""
        for layer in self._project.layers:
            if layer.name == layer_name:
                layer.visible = visible
                break
        for elem in (*self._project.zones, *self._project.keypoints, *self._project.annotations):
            if getattr(elem, "layer", "Default") == layer_name:
                elem.visible = visible
        self._project.mark_modified()
        self._canvas.update()
        self._layers_panel.refresh(self._project)

    def _on_layer_add_requested(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Add Layer", "Layer name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if any(lyr.name == name for lyr in self._project.layers):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Duplicate Layer", f"A layer named '{name}' already exists.")
            return
        from bimap.models.layer import Layer
        self._project.layers.append(Layer(name=name))
        self._project.mark_modified()
        self._layers_panel.refresh(self._project)

    def _on_layer_remove_requested(self, layer_name: str) -> None:
        """Move all elements from *layer_name* to Default, then remove the layer."""
        for elem in (*self._project.zones, *self._project.keypoints, *self._project.annotations):
            if getattr(elem, "layer", "Default") == layer_name:
                elem.layer = "Default"
        self._project.layers = [lyr for lyr in self._project.layers if lyr.name != layer_name]
        self._project.mark_modified()
        self._layers_panel.refresh(self._project)
        self._canvas.update()

    def _on_property_changed(self, etype: str, eid: str, field: str, value: Any) -> None:
        """Apply a property edit to the element model."""
        element = self._find_element(etype, eid)
        if not element:
            return
        old = copy.deepcopy(element)
        try:
            _set_nested_attr(element, field, value)
        except (AttributeError, ValueError):
            return
        new = copy.deepcopy(element)
        # Push edit command
        notify = lambda: (self._canvas.update(), self._layers_panel.refresh(self._project))
        if etype == "zone":
            cmd = EditZoneCommand(self._project, old, new, notify)
        elif etype == "keypoint":
            cmd = EditKeypointCommand(self._project, old, new, notify)
        elif etype == "annotation":
            cmd = EditAnnotationCommand(self._project, old, new, notify)
        else:
            return
        self._undo_stack.push(cmd)

    def _on_data_refreshed(self, source_id: str, rows: list) -> None:
        # Apply field mappings
        for ds in self._project.data_sources:
            if str(ds.id) == source_id:
                self._apply_mappings(ds, rows)
                ds.last_refresh = str(__import__("datetime").datetime.now().isoformat())
                ds.last_error = ""
                break
        self._data_panel.update_source_status(source_id, "")
        self._canvas.update()

    def _on_refresh_error(self, source_id: str, message: str) -> None:
        for ds in self._project.data_sources:
            if str(ds.id) == source_id:
                ds.last_error = message
                break
        self._data_panel.update_source_status(source_id, message)
        self.statusBar().showMessage(f"Data refresh error: {message}", 5000)

    def _on_context_action(self, action: str, etype: str, eid: str) -> None:
        """Handle right-click context menu actions from the map canvas."""
        match action:
            case "remove":
                name = eid[:8]
                element = self._find_element(etype, eid)
                if element and hasattr(element, "name"):
                    name = element.name
                reply = QMessageBox.question(
                    self,
                    "Confirm Remove",
                    f"Remove '{name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._delete_element(etype, eid)
            case "edit":
                self._on_element_selected(etype, eid)
                self._props_dock.show()
                self._props_dock.raise_()
            case "move":
                self._canvas.set_tool(ToolMode.MOVE_ELEMENT)
                self._canvas._interaction.start_move_element(etype, eid)
            case "view_metadata":
                element = self._find_element(etype, eid)
                if element:
                    name = getattr(element, "name", None) or getattr(
                        element, "info_card", None
                    ) and element.info_card.title or eid[:8]
                    metadata = getattr(element, "metadata", {})
                    dlg = MetadataViewDialog(name, etype, metadata, self)
                    dlg.exec()

    def _on_multi_select(self, items: list) -> None:
        """Handle magic-wand lasso — offer batch delete and/or polygon creation."""
        n = len(items)
        lasso_zone = getattr(self._canvas._interaction, "_lasso_zone", None)

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Lasso Selection")
        if n > 0:
            msg_box.setText(f"{n} element(s) inside lasso.")
        else:
            msg_box.setText("No elements found inside lasso.")

        btn_delete = None
        if n > 0:
            btn_delete = msg_box.addButton(
                f"🗑  Delete {n} element(s)",
                QMessageBox.ButtonRole.DestructiveRole,
            )
        btn_zone = msg_box.addButton("⬠  Create Polygon Zone", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton(QMessageBox.StandardButton.Cancel)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == btn_delete:
            cmd = RemoveMultipleCommand(self._project, items, self._refresh_all)
            self._undo_stack.push(cmd)
        elif clicked == btn_zone and lasso_zone is not None:
            cmd = AddZoneCommand(self._project, lasso_zone, self._refresh_all)
            self._undo_stack.push(cmd)
            self._on_element_selected("zone", str(lasso_zone.id))

    def _on_element_move_dropped(self, etype: str, eid: str, lat: float, lon: float) -> None:
        """Push a MoveElementCommand when the user drops an element at the new position."""
        cmd = MoveElementCommand(self._project, etype, eid, lat, lon, self._refresh_all)
        self._undo_stack.push(cmd)

    def _on_add_annotation_at(self, ann_type: str, lat: float, lon: float) -> None:
        """Create a text annotation at the right-clicked map position."""
        from bimap.models.annotation import Annotation, AnnotationType, CanvasPosition
        px = self._canvas.lat_lon_to_px(lat, lon)
        ann = Annotation(
            ann_type=AnnotationType.TEXT_BOX,
            anchor_lat=lat,
            anchor_lon=lon,
            content="Text",
        )
        ann.position = CanvasPosition(x=px.x(), y=px.y(), width=120, height=40)
        cmd = AddAnnotationCommand(self._project, ann, self._refresh_all)
        self._undo_stack.push(cmd)
        self._on_element_selected("annotation", str(ann.id))

    def _on_layer_element_action(self, action: str, etype: str, eid: str) -> None:
        """Handle element actions triggered from the layers panel context menu."""
        match action:
            case "go_to":
                element = self._find_element(etype, eid)
                if element is None:
                    return
                lat = getattr(element, "lat", None)
                lon = getattr(element, "lon", None)
                if lat is None and hasattr(element, "coordinates") and element.coordinates:
                    lat = element.coordinates[0].lat
                    lon = element.coordinates[0].lon
                if lat is not None and lon is not None:
                    self._canvas.set_viewport(lat, lon, self._project.map_state.zoom)
            case "edit" | "remove":
                self._on_context_action(action, etype, eid)
            case "update":
                element = self._find_element(etype, eid)
                if element and getattr(element, "data_binding", None):
                    self._refresh_manager.refresh_now(str(element.data_binding.source_id))

    def _on_element_layer_changed(self, etype: str, eid: str, new_layer: str) -> None:
        """Move an element to a different layer after drag-drop in the layers panel."""
        element = self._find_element(etype, eid)
        if element:
            element.layer = new_layer
            self._project.mark_modified()
            self._layers_panel.refresh(self._project)
            self._canvas.update()

    # ── Element helpers ────────────────────────────────────────────────────────

    def _find_element(self, element_type: str, element_id: str) -> Any | None:
        try:
            uid = UUID(element_id)
        except (ValueError, AttributeError):
            return None
        match element_type:
            case "zone":
                return next((z for z in self._project.zones if z.id == uid), None)
            case "keypoint":
                return next((k for k in self._project.keypoints if k.id == uid), None)
            case "annotation":
                return next((a for a in self._project.annotations if a.id == uid), None)
        return None

    def _find_source(self, source_id: str) -> DataSource | None:
        return next((s for s in self._project.data_sources if str(s.id) == source_id), None)

    def _delete_element(self, element_type: str, element_id: str) -> None:
        try:
            uid = UUID(element_id)
        except (ValueError, AttributeError):
            return
        notify = self._refresh_all
        match element_type:
            case "zone":
                cmd = RemoveZoneCommand(self._project, uid, notify)
            case "keypoint":
                cmd = RemoveKeypointCommand(self._project, uid, notify)
            case "annotation":
                cmd = RemoveAnnotationCommand(self._project, uid, notify)
            case _:
                return
        self._undo_stack.push(cmd)
        self._selected = None
        self._props_panel.clear()

    def _register_source(self, ds: DataSource) -> None:
        try:
            connector = build_connector(ds)
            connector.connect()
            self._refresh_manager.register(ds, connector)
            if ds.refresh_mode == RefreshMode.ON_OPEN:
                self._refresh_manager.refresh_now(str(ds.id))
        except ValueError as exc:
            ds.last_error = str(exc)

    def _apply_mappings(self, ds: DataSource, rows: list[dict]) -> None:
        """Apply field mappings from *rows* to project elements."""
        for mapping in ds.field_mappings:
            try:
                uid = UUID(mapping.target_element_id)
            except (ValueError, AttributeError):
                continue
            element = self._find_element(mapping.target_element_type, str(uid))
            if not element or not rows:
                continue
            raw_value = rows[0].get(mapping.source_column)
            if mapping.transform:
                try:
                    raw_value = _safe_eval_transform(mapping.transform, raw_value)
                except Exception:
                    pass
            try:
                _set_nested_attr(element, mapping.target_property, raw_value)
            except (AttributeError, ValueError):
                pass

    def _assign_keynote(self, kp_id: str) -> None:
        existing = {k.keynote_number for k in self._project.keypoints
                    if k.keynote_number is not None}
        next_num = 1
        while next_num in existing:
            next_num += 1
        kp = self._find_element("keypoint", kp_id)
        if kp:
            kp.keynote_number = next_num
            self._project.mark_modified()
            self._keynotes_panel.refresh(self._project)
            self._canvas.update()

    def _clear_keynote(self, kp_id: str) -> None:
        kp = self._find_element("keypoint", kp_id)
        if kp:
            kp.keynote_number = None
            self._project.mark_modified()
            self._keynotes_panel.refresh(self._project)
            self._canvas.update()

    def _confirm_discard(self) -> bool:
        if self._undo_stack.isClean():
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        return reply == QMessageBox.StandardButton.Yes

    def closeEvent(self, event) -> None:
        if not self._confirm_discard():
            event.ignore()
        else:
            event.accept()


# ── Utility ────────────────────────────────────────────────────────────────────

def _set_nested_attr(obj: Any, dotted_path: str, value: Any) -> None:
    """Set a nested attribute like 'style.fill_color' on *obj*."""
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        if part == "info_card" and hasattr(obj, "info_card"):
            obj = obj.info_card
        elif part == "style" and hasattr(obj, "style"):
            obj = obj.style
        elif part == "label" and hasattr(obj, "label"):
            obj = obj.label
        elif part == "fields":
            return  # complex sub-list, skip for now
        else:
            obj = getattr(obj, part)
    setattr(obj, parts[-1], value)
