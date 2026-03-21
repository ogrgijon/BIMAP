"""Toolbar components: VS Code-style vertical ActivityBar + slim top SearchBar."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget,
)

from bimap.config import TILE_PROVIDERS
from bimap.ui.map_canvas.interaction import ToolMode

# ── Stylesheets ──────────────────────────────────────────────────────────────

_TOOLBAR_QSS = """
QToolBar {
    background: #252526;
    border: none;
    border-bottom: 1px solid #3C3C3C;
    spacing: 2px;
    padding: 2px 6px;
}
QToolBar::separator {
    width: 1px;
    background: #3C3C3C;
    margin: 4px 3px;
}
QToolButton {
    background: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    color: #858585;
    font-size: 18px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    padding: 0px;
    margin: 0px;
    text-align: center;
}
QToolButton:hover {
    color: #CCCCCC;
    background: #2A2D2E;
}
QToolButton:checked {
    color: #FFFFFF;
    border-bottom: 3px solid #007ACC;
    background: rgba(0, 122, 204, 0.12);
}
QToolButton:pressed {
    background: #094771;
    color: #FFFFFF;
}
"""

_SEARCH_BAR_QSS = """
QToolBar {
    background: #2D2D2D;
    border-bottom: 1px solid #3C3C3C;
    spacing: 4px;
    padding: 3px 8px;
}
QToolButton {
    background: #3C3C3C;
    border: 1px solid #555555;
    color: #D4D4D4;
    border-radius: 3px;
    padding: 2px 8px;
    font-size: 11px;
}
QToolButton:hover {
    background: #4A4A4A;
    border-color: #007ACC;
}
"""

# ── SearchBar ────────────────────────────────────────────────────────────────


class SearchBar(QToolBar):
    """
    Slim top toolbar containing:
      • Geocoder search input + Search button
      • Tile provider selector
      • Zoom in / Zoom out

    Signals
    -------
    search_requested(str)
    tile_provider_changed(str)
    zoom_in_requested()
    zoom_out_requested()
    """

    search_requested = pyqtSignal(str)
    tile_provider_changed = pyqtSignal(str)
    zoom_in_requested = pyqtSignal()
    zoom_out_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Search & Map Controls", parent)
        self.setMovable(False)
        self.setFloatable(False)
        self.setStyleSheet(_SEARCH_BAR_QSS)

        # ── Geocoder ──────────────────────────────────────────────────────── #
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍  Search location…")
        self._search_edit.setMinimumWidth(240)
        self._search_edit.setMaximumWidth(400)
        self._search_edit.setStyleSheet(
            "font-size: 12px; padding: 4px 8px;"
            "background:#3C3C3C; color:#D4D4D4;"
            "border:1px solid #555; border-radius:3px;"
        )
        self._search_edit.returnPressed.connect(self._emit_search)
        self.addWidget(self._search_edit)

        btn_search = QToolButton(self)
        btn_search.setText("Search")
        btn_search.setToolTip("Search location (Enter)")
        btn_search.clicked.connect(self._emit_search)
        self.addWidget(btn_search)

        self.addSeparator()

        # ── Tile provider ─────────────────────────────────────────────────── #
        self.addWidget(QLabel("  Map: "))
        self._provider_combo = QComboBox()
        self._provider_combo.setToolTip("Tile provider")
        self._provider_combo.setStyleSheet(
            "background:#3C3C3C; color:#D4D4D4;"
            "border:1px solid #555; border-radius:3px; padding:2px 6px;"
        )
        for key, info in TILE_PROVIDERS.items():
            self._provider_combo.addItem(info["label"], key)
        self._provider_combo.currentIndexChanged.connect(
            lambda: self.tile_provider_changed.emit(self._provider_combo.currentData())
        )
        self.addWidget(self._provider_combo)

        self.addSeparator()

        # ── Zoom ──────────────────────────────────────────────────────────── #
        zi = QAction("＋", self)
        zi.setToolTip("Zoom in  [ + ]")
        zi.triggered.connect(self.zoom_in_requested)
        self.addAction(zi)

        zo = QAction("－", self)
        zo.setToolTip("Zoom out  [ - ]")
        zo.triggered.connect(self.zoom_out_requested)
        self.addAction(zo)

    def set_tile_provider(self, key: str) -> None:
        idx = self._provider_combo.findData(key)
        if idx >= 0:
            self._provider_combo.blockSignals(True)
            self._provider_combo.setCurrentIndex(idx)
            self._provider_combo.blockSignals(False)

    def _emit_search(self) -> None:
        query = self._search_edit.text().strip()
        if query:
            self.search_requested.emit(query)


# ── MapToolbar (VS Code Activity Bar) ────────────────────────────────────────


class MapToolbar(QToolBar):
    """
    VS Code-style narrow vertical activity bar (left side).

    Sections:
      • Navigate  — Select / Pan / Lasso
      • Create    — polygon, rectangle, circle, pin, text
      • (bottom)  — Import, Print/PDF

    Signals
    -------
    tool_selected(str)  — ToolMode value emitted on tool activation
    import_requested()
    print_requested()
    """

    tool_selected = pyqtSignal(str)
    import_requested = pyqtSignal()
    print_requested = pyqtSignal()

    _NAVIGATE_TOOLS: list[tuple[str, str, ToolMode]] = [
        ("⬡", "Select / move elements", ToolMode.SELECT),
        ("✋", "Pan the map", ToolMode.PAN),
        ("✦", "Lasso: area-select to batch remove", ToolMode.MAGIC_WAND),
    ]

    _CREATE_TOOLS: list[tuple[str, str, ToolMode]] = [
        ("⬠", "Draw polygon zone", ToolMode.DRAW_POLYGON),
        ("▭", "Draw rectangle zone", ToolMode.DRAW_RECTANGLE),
        ("◯", "Draw circle zone", ToolMode.DRAW_CIRCLE),
        ("📍", "Place keypoint marker", ToolMode.DRAW_KEYPOINT),
        ("T", "Place text annotation", ToolMode.DRAW_TEXT),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Activity", parent)
        self.setMovable(False)
        self.setFloatable(False)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setStyleSheet(_TOOLBAR_QSS)

        self._tool_actions: dict[ToolMode, QAction] = {}
        self._group = QActionGroup(self)
        self._group.setExclusive(True)

        # ── Navigate ──────────────────────────────────────────────────────── #
        for symbol, tooltip, mode in self._NAVIGATE_TOOLS:
            act = QAction(symbol, self)
            act.setToolTip(tooltip)
            act.setCheckable(True)
            act.setData(mode)
            act.triggered.connect(
                lambda checked, m=mode: self.tool_selected.emit(m)
            )
            self._group.addAction(act)
            self.addAction(act)
            self._tool_actions[mode] = act

        self.addSeparator()

        # ── Create ────────────────────────────────────────────────────────── #
        for symbol, tooltip, mode in self._CREATE_TOOLS:
            act = QAction(symbol, self)
            act.setToolTip(tooltip)
            act.setCheckable(True)
            act.setData(mode)
            act.triggered.connect(
                lambda checked, m=mode: self.tool_selected.emit(m)
            )
            self._group.addAction(act)
            self.addAction(act)
            self._tool_actions[mode] = act

        self.addSeparator()

        # ── Spacer — pushes right-side items to the right ────────────────── #
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.addWidget(spacer)

        # ── Bottom utility actions ─────────────────────────────────────────── #
        act_import = QAction("⬇", self)
        act_import.setToolTip("Import GeoJSON…")
        act_import.triggered.connect(self.import_requested)
        self.addAction(act_import)

        act_print = QAction("🖶", self)
        act_print.setToolTip("Print / Export PDF…")
        act_print.triggered.connect(self.print_requested)
        self.addAction(act_print)

        # Default tool
        self._tool_actions[ToolMode.PAN].setChecked(True)

    def set_tool(self, mode: ToolMode) -> None:
        action = self._tool_actions.get(mode)
        if action:
            action.setChecked(True)
