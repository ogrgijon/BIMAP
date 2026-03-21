"""
Interaction handler — translates mouse/keyboard events into map actions.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPolygonF,
)

from bimap.models.annotation import Annotation, AnnotationType, AnnotationStyle, CanvasPosition
from bimap.models.keypoint import InfoCard, Keypoint
from bimap.models.zone import LatLon, Zone, ZoneType

if TYPE_CHECKING:
    from bimap.ui.map_canvas.tile_widget import TileWidget


class ToolMode(StrEnum):
    SELECT = "select"
    PAN = "pan"
    DRAW_POLYGON = "draw_polygon"
    DRAW_RECTANGLE = "draw_rectangle"
    DRAW_CIRCLE = "draw_circle"
    DRAW_KEYPOINT = "draw_keypoint"
    DRAW_TEXT = "draw_text"
    MAGIC_WAND = "magic_wand"
    MOVE_ELEMENT = "move_element"


class InteractionHandler(QObject):
    """Manages drawing state and emits signals when elements are created."""

    request_repaint = pyqtSignal()
    draw_finished = pyqtSignal(str, object)           # element_type, model_object
    element_selected = pyqtSignal(str, str)           # element_type, id string
    multi_select_finished = pyqtSignal(list)          # list[(etype, eid)]
    element_move_dropped = pyqtSignal(str, str, float, float)  # etype, eid, lat, lon

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tool: ToolMode = ToolMode.PAN
        # In-progress polygon vertices (canvas-pixel QPointF list)
        self._polygon_pts: list[QPointF] = []
        # Rectangle drag state
        self._rect_start: QPointF | None = None
        self._rect_end: QPointF | None = None
        # Circle drag state
        self._circle_center: QPointF | None = None
        self._circle_edge: QPointF | None = None
        # Current mouse position
        self._mouse_pos: QPointF = QPointF(0, 0)
        # Currently selected element
        self._selected_type: str | None = None
        self._selected_id: str | None = None
        # Magic-wand lasso state
        self._lasso_pts: list[QPointF] = []
        self._lasso_active: bool = False
        self._multi_selected: list[tuple[str, str]] = []
        self._lasso_zone: "Zone | None" = None  # polygon built from last lasso
        # Move-element state
        self._move_element_type: str | None = None
        self._move_element_id: str | None = None

    @property
    def tool(self) -> ToolMode:
        return self._tool

    @property
    def selected_type(self) -> str | None:
        return self._selected_type

    @property
    def selected_id(self) -> str | None:
        return self._selected_id

    def set_selected(self, element_type: str, element_id: str) -> None:
        """Programmatically select an element and request a repaint."""
        self._selected_type = element_type
        self._selected_id = element_id
        self.request_repaint.emit()

    def set_tool(self, mode: ToolMode) -> None:
        self._tool = mode
        self._reset_draw_state()

    @property
    def multi_selected(self) -> list[tuple[str, str]]:
        return self._multi_selected

    def _reset_draw_state(self) -> None:
        self._polygon_pts.clear()
        self._rect_start = None
        self._rect_end = None
        self._circle_center = None
        self._circle_edge = None
        self._lasso_pts.clear()
        self._lasso_active = False
        self._multi_selected.clear()
        self._lasso_zone = None
        self._move_element_type = None
        self._move_element_id = None

    # ── Mouse events ───────────────────────────────────────────────────────────

    def mouse_press(self, event: QMouseEvent, canvas: "TileWidget") -> None:
        pos = event.position()
        btn = event.button()
        if btn != Qt.MouseButton.LeftButton:
            return

        match self._tool:
            case ToolMode.DRAW_POLYGON:
                self._polygon_pts.append(QPointF(pos))
                self.request_repaint.emit()

            case ToolMode.DRAW_RECTANGLE:
                self._rect_start = QPointF(pos)
                self._rect_end = QPointF(pos)

            case ToolMode.DRAW_CIRCLE:
                self._circle_center = QPointF(pos)
                self._circle_edge = QPointF(pos)

            case ToolMode.DRAW_KEYPOINT:
                lat, lon = canvas.px_to_lat_lon(pos.x(), pos.y())
                kp = Keypoint(lat=lat, lon=lon)
                kp.info_card.title = "New Point"
                self.draw_finished.emit("keypoint", kp)

            case ToolMode.DRAW_TEXT:
                lat, lon = canvas.px_to_lat_lon(pos.x(), pos.y())
                ann = Annotation(
                    ann_type=AnnotationType.TEXT_BOX,
                    anchor_lat=lat,
                    anchor_lon=lon,
                    content="Text",
                )
                ann.position = CanvasPosition(x=pos.x(), y=pos.y(), width=120, height=40)
                self.draw_finished.emit("annotation", ann)

            case ToolMode.SELECT:
                self._try_select(pos, canvas)

            case ToolMode.MAGIC_WAND:
                self._lasso_pts = [QPointF(pos)]
                self._lasso_active = True
                self._multi_selected.clear()

            case ToolMode.MOVE_ELEMENT if self._move_element_type:
                lat, lon = canvas.px_to_lat_lon(pos.x(), pos.y())
                self.element_move_dropped.emit(
                    self._move_element_type, self._move_element_id, lat, lon
                )
                self._move_element_type = None
                self._move_element_id = None
                # Keep MOVE_ELEMENT active so the user can move more elements
                self.request_repaint.emit()

            case ToolMode.MOVE_ELEMENT:
                # No element tracked yet — hit-test to pick one to move
                self._pick_element_for_move(pos, canvas)

    def mouse_move(self, event: QMouseEvent, canvas: "TileWidget") -> None:
        self._mouse_pos = event.position()
        match self._tool:
            case ToolMode.DRAW_RECTANGLE if self._rect_start:
                self._rect_end = QPointF(event.position())
                self.request_repaint.emit()
            case ToolMode.DRAW_CIRCLE if self._circle_center:
                self._circle_edge = QPointF(event.position())
                self.request_repaint.emit()
            case ToolMode.DRAW_POLYGON if self._polygon_pts:
                self.request_repaint.emit()
            case ToolMode.MAGIC_WAND if self._lasso_active:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    self._lasso_pts.append(QPointF(event.position()))
                self.request_repaint.emit()
            case ToolMode.MOVE_ELEMENT:
                self.request_repaint.emit()

    def mouse_release(self, event: QMouseEvent, canvas: "TileWidget") -> None:
        pos = event.position()
        match self._tool:
            case ToolMode.DRAW_RECTANGLE if self._rect_start and self._rect_end:
                self._finish_rectangle(canvas)
            case ToolMode.DRAW_CIRCLE if self._circle_center and self._circle_edge:
                self._finish_circle(canvas)
            case ToolMode.MAGIC_WAND if self._lasso_active:
                self._lasso_active = False
                self._finish_lasso(canvas)

    def mouse_double_click(self, event: QMouseEvent, canvas: "TileWidget") -> None:
        if self._tool == ToolMode.DRAW_POLYGON and len(self._polygon_pts) >= 3:
            self._finish_polygon(canvas)

    def key_press(self, event: QKeyEvent, canvas: "TileWidget") -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._reset_draw_state()
            self.request_repaint.emit()
        elif event.key() == Qt.Key.Key_Return and self._tool == ToolMode.DRAW_POLYGON:
            if len(self._polygon_pts) >= 3:
                self._finish_polygon(canvas)

    # ── Finish drawing helpers ─────────────────────────────────────────────────

    def _finish_polygon(self, canvas: "TileWidget") -> None:
        coords = []
        for p in self._polygon_pts:
            lat, lon = canvas.px_to_lat_lon(p.x(), p.y())
            coords.append(LatLon(lat=lat, lon=lon))
        self._polygon_pts.clear()
        zone = Zone(zone_type=ZoneType.POLYGON, coordinates=coords, name="New Zone")
        zone.label.text = zone.name
        self.draw_finished.emit("zone", zone)
        self.request_repaint.emit()

    def _finish_rectangle(self, canvas: "TileWidget") -> None:
        s, e = self._rect_start, self._rect_end
        corners = []
        for cx, cy in [(s.x(), s.y()), (e.x(), s.y()), (e.x(), e.y()), (s.x(), e.y())]:
            lat, lon = canvas.px_to_lat_lon(cx, cy)
            corners.append(LatLon(lat=lat, lon=lon))
        zone = Zone(zone_type=ZoneType.RECTANGLE, coordinates=corners, name="New Zone")
        zone.label.text = zone.name
        self._rect_start = self._rect_end = None
        self.draw_finished.emit("zone", zone)
        self.request_repaint.emit()

    def _finish_circle(self, canvas: "TileWidget") -> None:
        c = self._circle_center
        e = self._circle_edge
        lat, lon = canvas.px_to_lat_lon(c.x(), c.y())
        dx = e.x() - c.x()
        dy = e.y() - c.y()
        radius_px = math.sqrt(dx * dx + dy * dy)
        from bimap.engine.tile_math import meters_per_pixel
        mpp = meters_per_pixel(lat, canvas.zoom)
        radius_m = radius_px * mpp
        zone = Zone(
            zone_type=ZoneType.CIRCLE,
            coordinates=[LatLon(lat=lat, lon=lon)],
            radius_m=max(1.0, radius_m),
            name="New Circle",
        )
        zone.label.text = zone.name
        self._circle_center = self._circle_edge = None
        self.draw_finished.emit("zone", zone)
        self.request_repaint.emit()

    def _finish_lasso(self, canvas: "TileWidget") -> None:
        """Close the magic-wand lasso, multi-select enclosed elements, and build a polygon zone."""
        if len(self._lasso_pts) < 3 or not canvas._project:
            self._lasso_pts.clear()
            self._lasso_zone = None
            self.request_repaint.emit()
            return

        found: list[tuple[str, str]] = []
        project = canvas._project

        for zone in project.zones:
            if not zone.coordinates:
                continue
            if zone.zone_type == ZoneType.CIRCLE:
                c = zone.coordinates[0]
            else:
                c_lat = sum(p.lat for p in zone.coordinates) / len(zone.coordinates)
                c_lon = sum(p.lon for p in zone.coordinates) / len(zone.coordinates)

                class _P:
                    lat = c_lat
                    lon = c_lon
                c = _P()
            px = canvas.lat_lon_to_px(c.lat, c.lon)
            if self._point_in_lasso(px.x(), px.y()):
                found.append(("zone", str(zone.id)))

        for kp in project.keypoints:
            px = canvas.lat_lon_to_px(kp.lat, kp.lon)
            if self._point_in_lasso(px.x(), px.y()):
                found.append(("keypoint", str(kp.id)))

        # Build a polygon Zone from the lasso outline
        zone_coords = []
        for p in self._lasso_pts:
            lat, lon = canvas.px_to_lat_lon(p.x(), p.y())
            zone_coords.append(LatLon(lat=lat, lon=lon))
        lasso_zone = Zone(
            zone_type=ZoneType.POLYGON,
            coordinates=zone_coords,
            name="Lasso Zone",
        )
        lasso_zone.label.text = lasso_zone.name
        self._lasso_zone = lasso_zone

        self._multi_selected = found
        self._lasso_pts.clear()
        # Always emit so the handler can offer both delete and create-polygon
        self.multi_select_finished.emit(found)
        self.request_repaint.emit()

    def _point_in_lasso(self, x: float, y: float) -> bool:
        """Ray-casting point-in-polygon test against the lasso path."""
        pts = self._lasso_pts
        inside = False
        j = len(pts) - 1
        for i in range(len(pts)):
            xi, yi = pts[i].x(), pts[i].y()
            xj, yj = pts[j].x(), pts[j].y()
            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
            ):
                inside = not inside
            j = i
        return inside

    def start_move_element(self, element_type: str, element_id: str) -> None:
        """Enter move mode: next left-click will drop the element at that position."""
        self._move_element_type = element_type
        self._move_element_id = element_id
        self._tool = ToolMode.MOVE_ELEMENT
        self.request_repaint.emit()

    def _pick_element_for_move(self, pos: QPointF, canvas: "TileWidget") -> None:
        """Hit-test to pick an element so it can be moved on the next click."""
        if not canvas._project:
            return
        lat, lon = canvas.px_to_lat_lon(pos.x(), pos.y())
        for kp in canvas._project.keypoints:
            kp_px = canvas.lat_lon_to_px(kp.lat, kp.lon)
            dx = kp_px.x() - pos.x()
            dy = kp_px.y() - pos.y()
            if math.sqrt(dx * dx + dy * dy) <= kp.icon_size + 4:
                self._move_element_type = "keypoint"
                self._move_element_id = str(kp.id)
                self.request_repaint.emit()
                return
        for zone in canvas._project.zones:
            if getattr(zone, "locked", False):
                continue
            if self._point_in_zone(lat, lon, zone, canvas):
                self._move_element_type = "zone"
                self._move_element_id = str(zone.id)
                self.request_repaint.emit()
                return

    # ── Selection ──────────────────────────────────────────────────────────────

    def _try_select(self, pos: QPointF, canvas: "TileWidget") -> None:
        if not canvas._project:
            return
        lat, lon = canvas.px_to_lat_lon(pos.x(), pos.y())

        # Check keypoints first (small target)
        for kp in canvas._project.keypoints:
            kp_px = canvas.lat_lon_to_px(kp.lat, kp.lon)
            dx = kp_px.x() - pos.x()
            dy = kp_px.y() - pos.y()
            if math.sqrt(dx * dx + dy * dy) <= kp.icon_size + 4:
                self._selected_type = "keypoint"
                self._selected_id = str(kp.id)
                self.element_selected.emit("keypoint", str(kp.id))
                return

        # Check zones (skip locked zones)
        for zone in canvas._project.zones:
            if getattr(zone, 'locked', False):
                continue
            if self._point_in_zone(lat, lon, zone, canvas):
                self._selected_type = "zone"
                self._selected_id = str(zone.id)
                self.element_selected.emit("zone", str(zone.id))
                return

    def _point_in_zone(self, lat: float, lon: float, zone: "Zone", canvas: "TileWidget") -> bool:
        """Simple polygon point-in-polygon test using canvas pixels."""
        if not zone.coordinates:
            return False
        if zone.zone_type == ZoneType.CIRCLE and zone.coordinates:
            c = zone.coordinates[0]
            from bimap.engine.tile_math import meters_per_pixel, lat_lon_to_tile_float
            import math as _math
            dlat = (lat - c.lat) * 111_320
            dlon = (lon - c.lon) * 111_320 * _math.cos(_math.radians(c.lat))
            dist = _math.sqrt(dlat * dlat + dlon * dlon)
            return dist <= zone.radius_m

        # Ray-casting for polygons
        pts = zone.coordinates
        inside = False
        j = len(pts) - 1
        for i in range(len(pts)):
            xi, yi = pts[i].lat, pts[i].lon
            xj, yj = pts[j].lat, pts[j].lon
            if ((yi > lon) != (yj > lon)) and (lat < (xj - xi) * (lon - yi) / (yj - yi + 1e-12) + xi):
                inside = not inside
            j = i
        return inside

    # ── Preview painting ───────────────────────────────────────────────────────

    def paint_preview(self, painter: QPainter, canvas: "TileWidget") -> None:
        """Draw in-progress shape preview on the canvas painter."""
        match self._tool:
            case ToolMode.DRAW_POLYGON if self._polygon_pts:
                self._preview_polygon(painter)
            case ToolMode.DRAW_RECTANGLE if self._rect_start and self._rect_end:
                self._preview_rectangle(painter)
            case ToolMode.DRAW_CIRCLE if self._circle_center and self._circle_edge:
                self._preview_circle(painter)
            case ToolMode.MAGIC_WAND if len(self._lasso_pts) >= 2:
                self._preview_lasso(painter)
            case ToolMode.MOVE_ELEMENT if self._move_element_type:
                self._preview_move_crosshair(painter)

    def _preview_polygon(self, painter: QPainter) -> None:
        pts = self._polygon_pts + [self._mouse_pos]
        pen = QPen(QColor(51, 136, 255), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        for i in range(1, len(pts)):
            painter.drawLine(pts[i - 1], pts[i])
        # Vertex dots
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(51, 136, 255), 1))
        for pt in self._polygon_pts:
            painter.drawEllipse(pt, 4.0, 4.0)

    def _preview_rectangle(self, painter: QPainter) -> None:
        s, e = self._rect_start, self._rect_end
        rect = QRectF(
            min(s.x(), e.x()), min(s.y(), e.y()),
            abs(e.x() - s.x()), abs(e.y() - s.y())
        )
        pen = QPen(QColor(51, 136, 255), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        fill = QColor(51, 136, 255, 40)
        painter.setBrush(fill)
        painter.drawRect(rect)

    def _preview_circle(self, painter: QPainter) -> None:
        c, e = self._circle_center, self._circle_edge
        dx = e.x() - c.x()
        dy = e.y() - c.y()
        r = math.sqrt(dx * dx + dy * dy)
        pen = QPen(QColor(51, 136, 255), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        fill = QColor(51, 136, 255, 40)
        painter.setBrush(fill)
        painter.drawEllipse(QRectF(c.x() - r, c.y() - r, r * 2, r * 2))

    def _preview_lasso(self, painter: QPainter) -> None:
        pen = QPen(QColor(255, 140, 0), 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QColor(255, 140, 0, 30))
        painter.drawPolygon(QPolygonF(self._lasso_pts))

    def _preview_move_crosshair(self, painter: QPainter) -> None:
        x, y = self._mouse_pos.x(), self._mouse_pos.y()
        pen = QPen(QColor(0, 200, 100), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(x - 12, y), QPointF(x + 12, y))
        painter.drawLine(QPointF(x, y - 12), QPointF(x, y + 12))
        painter.drawEllipse(QRectF(x - 7, y - 7, 14, 14))
