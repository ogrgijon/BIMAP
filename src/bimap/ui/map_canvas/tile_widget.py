"""
TileWidget — the central map canvas that renders tiles and all overlays.
"""

from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import (
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QContextMenuEvent,
    QCursor,
    QFont,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import QMenu, QWidget

from bimap.config import (
    MAX_ZOOM,
    MIN_ZOOM,
    TILE_PROVIDERS,
    TILE_SIZE,
)
from bimap.engine.tile_math import (
    lat_lon_to_pixel,
    pixel_to_lat_lon,
    visible_tiles,
)
from bimap.ui.map_canvas.tile_fetcher import TileFetchRunnable, get_tile_cache
from bimap.ui.map_canvas.overlay_renderer import OverlayRenderer
from bimap.ui.map_canvas.interaction import InteractionHandler, ToolMode


class TileWidget(QWidget):
    """
    The main interactive map canvas.

    Signals
    -------
    viewport_changed(lat, lon, zoom) - emitted on every pan/zoom
    element_selected(element_type, element_id) - user clicked a zone/keypoint
    draw_finished(element_type, data) - user finished drawing a new element
    coordinates_changed(lat, lon) - mouse-move coordinate update for status bar
    """

    viewport_changed = pyqtSignal(float, float, int)
    element_selected = pyqtSignal(str, str)
    draw_finished = pyqtSignal(str, object)
    coordinates_changed = pyqtSignal(float, float)
    context_action_requested = pyqtSignal(str, str, str)    # action, etype, eid
    multi_select_finished = pyqtSignal(list)
    element_move_dropped = pyqtSignal(str, str, float, float)
    add_annotation_requested = pyqtSignal(str, float, float)  # ann_type, lat, lon

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        # Viewport state
        self._center_lat: float = 40.4168
        self._center_lon: float = -3.7038
        self._zoom: int = 12
        self._tile_provider: str = "osm_standard"

        # Tile storage keyed by (x, y, z)
        self._tiles: dict[tuple[int, int, int], QPixmap] = {}
        self._pending: set[tuple[int, int, int]] = set()

        # Thread pool for tile fetching
        self._thread_pool = QThreadPool.globalInstance()
        self._thread_pool.setMaxThreadCount(6)

        # Debounce timer — fires _refresh_tiles() 50ms after last pan event
        self._pan_debounce_timer = QTimer(self)
        self._pan_debounce_timer.setSingleShot(True)
        self._pan_debounce_timer.setInterval(50)
        self._pan_debounce_timer.timeout.connect(self._refresh_tiles)

        # Overlay renderer — draws zones, keypoints, annotations
        self._overlay = OverlayRenderer()

        # Interaction handler — tool modes, drawing, selection
        self._interaction = InteractionHandler(self)
        self._interaction.request_repaint.connect(self.update)
        self._interaction.draw_finished.connect(self.draw_finished)
        self._interaction.element_selected.connect(self.element_selected)
        self._interaction.multi_select_finished.connect(self.multi_select_finished)
        self._interaction.element_move_dropped.connect(self.element_move_dropped)

        # Drag state
        self._drag_start: QPoint | None = None
        self._drag_center_lat: float = self._center_lat
        self._drag_center_lon: float = self._center_lon

        # Project reference (set externally)
        self._project = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_project(self, project: Any) -> None:
        self._project = project
        self.set_viewport(
            project.map_state.center_lat,
            project.map_state.center_lon,
            project.map_state.zoom,
        )
        self.set_tile_provider(project.map_state.tile_provider)

    def set_viewport(self, lat: float, lon: float, zoom: int) -> None:
        self._center_lat = lat
        self._center_lon = lon
        self._zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        self._refresh_tiles()
        self.update()
        self.viewport_changed.emit(self._center_lat, self._center_lon, self._zoom)

    def set_tile_provider(self, provider_key: str) -> None:
        if provider_key in TILE_PROVIDERS:
            self._tile_provider = provider_key
            self._tiles.clear()
            self._pending.clear()
            self._refresh_tiles()
            self.update()

    def set_tool(self, mode: ToolMode) -> None:
        self._interaction.set_tool(mode)
        cursor_map = {
            ToolMode.SELECT: Qt.CursorShape.ArrowCursor,
            ToolMode.PAN: Qt.CursorShape.OpenHandCursor,
            ToolMode.DRAW_POLYGON: Qt.CursorShape.CrossCursor,
            ToolMode.DRAW_RECTANGLE: Qt.CursorShape.CrossCursor,
            ToolMode.DRAW_CIRCLE: Qt.CursorShape.CrossCursor,
            ToolMode.DRAW_KEYPOINT: Qt.CursorShape.CrossCursor,
            ToolMode.DRAW_TEXT: Qt.CursorShape.IBeamCursor,
            ToolMode.MAGIC_WAND: Qt.CursorShape.CrossCursor,
            ToolMode.MOVE_ELEMENT: Qt.CursorShape.SizeAllCursor,
        }
        self.setCursor(QCursor(cursor_map.get(mode, Qt.CursorShape.ArrowCursor)))

    @property
    def center_lat(self) -> float:
        return self._center_lat

    @property
    def center_lon(self) -> float:
        return self._center_lon

    @property
    def zoom(self) -> int:
        return self._zoom

    @property
    def tile_provider(self) -> str:
        return self._tile_provider

    @property
    def interaction(self) -> InteractionHandler:
        return self._interaction

    def lat_lon_to_px(self, lat: float, lon: float) -> QPointF:
        p = lat_lon_to_pixel(lat, lon, self._center_lat, self._center_lon,
                             self._zoom, self.width(), self.height())
        return QPointF(p.px, p.py)

    def px_to_lat_lon(self, x: float, y: float) -> tuple[float, float]:
        return pixel_to_lat_lon(x, y, self._center_lat, self._center_lon,
                                self._zoom, self.width(), self.height())

    # ── Painting ───────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw tiles
        self._paint_tiles(painter)

        # 2. Draw zone/keypoint/annotation overlays
        if self._project:
            ctx_render = (
                self._center_lat,
                self._center_lon,
                self._zoom,
                self.width(),
                self.height(),
            )
            self._overlay.render(
                painter,
                self._project,
                *ctx_render,
                selected_type=self._interaction.selected_type or "",
                selected_id=self._interaction.selected_id or "",
                multi_selected=self._interaction.multi_selected,
                delimitation_polygon=self._project.map_state.delimitation_polygon,
            )

        # 3. Draw in-progress drawing preview
        self._interaction.paint_preview(painter, self)

        # 4. Attribution text
        self._paint_attribution(painter)

        painter.end()

    def _paint_tiles(self, painter: QPainter) -> None:
        tiles = visible_tiles(
            self._center_lat, self._center_lon, self._zoom,
            self.width(), self.height()
        )
        for tile_coord, px, py in tiles:
            key = (tile_coord.x, tile_coord.y, tile_coord.z)
            pm = self._tiles.get(key)
            if pm:
                painter.drawPixmap(px, py, pm)
            else:
                # Draw placeholder
                painter.fillRect(px, py, TILE_SIZE, TILE_SIZE, QColor(220, 220, 220))
                self._request_tile(tile_coord)

    def _paint_attribution(self, painter: QPainter) -> None:
        provider = TILE_PROVIDERS.get(self._tile_provider, {})
        attr = provider.get("attribution", "")
        if not attr:
            return
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QColor(60, 60, 60, 200))
        fm = painter.fontMetrics()
        rect = QRect(0, self.height() - 18, self.width() - 4, 16)
        painter.fillRect(rect, QColor(255, 255, 255, 150))
        painter.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, attr)

    # ── Tile fetching ──────────────────────────────────────────────────────────

    def _refresh_tiles(self) -> None:
        tiles = visible_tiles(
            self._center_lat, self._center_lon, self._zoom,
            self.width(), self.height()
        )
        for tile_coord, _, _ in tiles:
            key = (tile_coord.x, tile_coord.y, tile_coord.z)
            if key not in self._tiles:
                self._request_tile(tile_coord)

    def _request_tile(self, tile: "TileCoord") -> None:
        key = (tile.x, tile.y, tile.z)
        if key in self._pending or key in self._tiles:
            return
        self._pending.add(key)
        url_template = TILE_PROVIDERS[self._tile_provider]["url"]
        runnable = TileFetchRunnable(tile, url_template)
        runnable.signals.tile_ready.connect(self._on_tile_ready)
        runnable.signals.tile_error.connect(self._on_tile_error)
        self._thread_pool.start(runnable)

    def _on_tile_ready(self, x: int, y: int, z: int, pm: QPixmap) -> None:
        key = (x, y, z)
        self._pending.discard(key)
        if z == self._zoom:   # only store if still relevant zoom
            self._tiles[key] = pm
            # LRU eviction: keep at most 300 tiles in memory
            if len(self._tiles) > 300:
                for k in list(self._tiles.keys())[:100]:
                    del self._tiles[k]
            self.update()

    def _on_tile_error(self, x: int, y: int, z: int) -> None:
        self._pending.discard((x, y, z))

    # ── Mouse / Keyboard events ────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._interaction.mouse_press(event, self)
        if self._interaction.tool == ToolMode.PAN:
            self._drag_start = event.position().toPoint()
            self._drag_center_lat = self._center_lat
            self._drag_center_lon = self._center_lon
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        lat, lon = self.px_to_lat_lon(pos.x(), pos.y())
        self.coordinates_changed.emit(lat, lon)

        if self._drag_start and self._interaction.tool == ToolMode.PAN:
            delta = event.position().toPoint() - self._drag_start
            # Convert pixel delta back to new center lat/lon
            new_lat, new_lon = pixel_to_lat_lon(
                self.width() / 2 - delta.x(),
                self.height() / 2 - delta.y(),
                self._drag_center_lat,
                self._drag_center_lon,
                self._zoom,
                self.width(),
                self.height(),
            )
            self._center_lat = new_lat
            self._center_lon = new_lon
            self._pan_debounce_timer.start(50)
            self.update()
        else:
            self._interaction.mouse_move(event, self)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_start and self._interaction.tool == ToolMode.PAN:
            self._drag_start = None
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            self.viewport_changed.emit(self._center_lat, self._center_lon, self._zoom)
        else:
            self._interaction.mouse_release(event, self)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self._interaction.mouse_double_click(event, self)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta > 0:
            new_zoom = min(self._zoom + 1, MAX_ZOOM)
        else:
            new_zoom = max(self._zoom - 1, MIN_ZOOM)
        if new_zoom != self._zoom:
            # Compute lat/lon under cursor so we can keep it fixed after zoom
            pos = event.position()
            lat_at_cursor, lon_at_cursor = self.px_to_lat_lon(pos.x(), pos.y())
            self._zoom = new_zoom
            # Where does the same lat/lon appear in the new zoom?
            from bimap.engine.tile_math import lat_lon_to_pixel, pixel_to_lat_lon
            new_coord = lat_lon_to_pixel(
                lat_at_cursor, lon_at_cursor,
                self._center_lat, self._center_lon,
                new_zoom, self.width(), self.height()
            )
            # Shift the centre so the cursor lat/lon stays under the cursor
            shift_x = new_coord.px - pos.x()
            shift_y = new_coord.py - pos.y()
            new_lat, new_lon = pixel_to_lat_lon(
                self.width() / 2 + shift_x,
                self.height() / 2 + shift_y,
                self._center_lat, self._center_lon,
                new_zoom, self.width(), self.height()
            )
            self._center_lat = new_lat
            self._center_lon = new_lon
            self._tiles.clear()
            self._pending.clear()
            self._refresh_tiles()
            self.update()
            self.viewport_changed.emit(self._center_lat, self._center_lon, self._zoom)

    def zoom_in(self) -> None:
        """Zoom in one level, centred on the current viewport centre."""
        self.set_viewport(self._center_lat, self._center_lon,
                          min(self._zoom + 1, MAX_ZOOM))

    def zoom_out(self) -> None:
        """Zoom out one level, centred on the current viewport centre."""
        self.set_viewport(self._center_lat, self._center_lon,
                          max(self._zoom - 1, MIN_ZOOM))

    def select_element(self, element_type: str, element_id: str) -> None:
        """Highlight a specific element on the canvas (pass to interaction handler)."""
        if hasattr(self._interaction, 'set_selected'):
            self._interaction.set_selected(element_type, element_id)
        self.update()

    def _hit_test(self, px: float, py: float) -> tuple[str, str]:
        """Return (element_type, element_id) of the topmost element at canvas pixel."""
        if not self._project:
            return "", ""
        import math as _math
        # Keypoints first (small click target)
        for kp in self._project.keypoints:
            kp_px = self.lat_lon_to_px(kp.lat, kp.lon)
            dx = kp_px.x() - px
            dy = kp_px.y() - py
            if _math.sqrt(dx * dx + dy * dy) <= kp.icon_size + 4:
                return "keypoint", str(kp.id)
        # Then zones
        lat, lon = self.px_to_lat_lon(px, py)
        for zone in self._project.zones:
            if self._interaction._point_in_zone(lat, lon, zone, self):
                return "zone", str(zone.id)
        return "", ""

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        pos = event.pos()
        hit_type, hit_id = self._hit_test(float(pos.x()), float(pos.y()))
        menu = QMenu(self)
        if not hit_type:
            # Empty canvas — offer text annotation creation at this position
            act_text = menu.addAction("📝  Add Text here")
            chosen = menu.exec(event.globalPos())
            lat, lon = self.px_to_lat_lon(float(pos.x()), float(pos.y()))
            if chosen == act_text:
                self.add_annotation_requested.emit("text_box", lat, lon)
            return
        act_edit     = menu.addAction("✏  Edit…")
        act_move     = menu.addAction("↔  Move")
        act_metadata = menu.addAction("📋  View Metadata…")
        menu.addSeparator()
        act_remove   = menu.addAction("🗑  Remove…")
        chosen = menu.exec(event.globalPos())
        if chosen == act_remove:
            self.context_action_requested.emit("remove", hit_type, hit_id)
        elif chosen == act_edit:
            self.context_action_requested.emit("edit", hit_type, hit_id)
        elif chosen == act_move:
            self.context_action_requested.emit("move", hit_type, hit_id)
        elif chosen == act_metadata:
            self.context_action_requested.emit("view_metadata", hit_type, hit_id)

    def keyPressEvent(self, event) -> None:
        self._interaction.key_press(event, self)

    def closeEvent(self, event) -> None:
        """Clean up tile pixmaps before the widget is destroyed."""
        self._tiles.clear()
        self._pending.clear()
        self._thread_pool.waitForDone(2000)
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_tiles()
