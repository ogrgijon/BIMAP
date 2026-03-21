"""
OverlayRenderer — paints zones, keypoints, and annotations on the map canvas.
"""

from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)

from bimap.engine.tile_math import lat_lon_to_pixel, meters_per_pixel
from bimap.models.annotation import Annotation, AnnotationType
from bimap.models.keypoint import Keypoint
from bimap.models.project import Project
from bimap.models.style import BorderStyle
from bimap.models.zone import Zone, ZoneType


class OverlayRenderer:
    """Stateless renderer — call render() on every paintEvent."""

    # ── Entry point ────────────────────────────────────────────────────────────

    def render(
        self,
        painter: QPainter,
        project: Project,
        center_lat: float,
        center_lon: float,
        zoom: int,
        w: int,
        h: int,
        selected_type: str = "",
        selected_id: str = "",
        multi_selected: list | None = None,
        delimitation_polygon: list | None = None,
    ) -> None:
        ctx = (center_lat, center_lon, zoom, w, h)
        _multi = set(multi_selected) if multi_selected else set()
        for zone in project.zones:
            if zone.visible:
                self._draw_zone(painter, zone, ctx)
                if selected_type == "zone" and selected_id == str(zone.id):
                    self._draw_selection_zone(painter, zone, ctx)
                elif ("zone", str(zone.id)) in _multi:
                    self._draw_multi_select_zone(painter, zone, ctx)
        for kp in project.keypoints:
            if kp.visible:
                self._draw_keypoint(painter, kp, ctx)
                if selected_type == "keypoint" and selected_id == str(kp.id):
                    self._draw_selection_keypoint(painter, kp, ctx)
                elif ("keypoint", str(kp.id)) in _multi:
                    self._draw_multi_select_keypoint(painter, kp, ctx)
        for ann in project.annotations:
            if ann.visible:
                self._draw_annotation(painter, ann, ctx)
        if delimitation_polygon:
            self._draw_delimitation(painter, delimitation_polygon, ctx, w, h)
        self._draw_scale_bar(painter, center_lat, zoom, w, h)
        self._draw_north_arrow(painter, w, h)

    # ── to-pixel helper ────────────────────────────────────────────────────────

    @staticmethod
    def _to_px(lat: float, lon: float, ctx: tuple) -> QPointF:
        center_lat, center_lon, zoom, w, h = ctx
        p = lat_lon_to_pixel(lat, lon, center_lat, center_lon, zoom, w, h)
        return QPointF(p.px, p.py)

    # ── Selection highlights ───────────────────────────────────────────────────

    def _draw_selection_zone(self, painter: QPainter, zone: Zone, ctx: tuple) -> None:
        """Draw dashed cyan selection outline over a selected zone."""
        pen = QPen(QColor(0, 180, 255), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if zone.zone_type == ZoneType.CIRCLE:
            if zone.coordinates:
                center_lat, center_lon, zoom, w, h = ctx
                c = zone.coordinates[0]
                px = self._to_px(c.lat, c.lon, ctx)
                mpp = meters_per_pixel(c.lat, zoom)
                r = zone.radius_m / mpp if mpp > 0 else 0
                painter.drawEllipse(QRectF(px.x() - r, px.y() - r, r * 2, r * 2))
        else:
            pts = [self._to_px(c.lat, c.lon, ctx) for c in zone.coordinates]
            if len(pts) >= 2:
                from PyQt6.QtGui import QPolygonF as _QPolygonF
                from PyQt6.QtGui import QPainterPath as _QPainterPath
                poly = _QPolygonF(pts)
                path = _QPainterPath()
                path.addPolygon(poly)
                path.closeSubpath()
                painter.drawPath(path)

    def _draw_selection_keypoint(self, painter: QPainter, kp, ctx: tuple) -> None:
        """Draw a cyan ring around a selected keypoint."""
        pos = self._to_px(kp.lat, kp.lon, ctx)
        r = kp.icon_size + 6
        pen = QPen(QColor(0, 180, 255), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(pos.x() - r, pos.y() - r * 1.5 - r * 0.5,
                                   r * 2, r * 2))

    # ── Multi-selection highlights ─────────────────────────────────────────────

    def _draw_multi_select_zone(self, painter: QPainter, zone: Zone, ctx: tuple) -> None:
        """Draw an orange dashed outline for zones in the magic-wand selection."""
        pen = QPen(QColor(255, 140, 0), 2, Qt.PenStyle.DashDotLine)
        painter.setPen(pen)
        painter.setBrush(QColor(255, 140, 0, 50))
        if zone.zone_type == ZoneType.CIRCLE and zone.coordinates:
            center_lat, center_lon, zoom, w, h = ctx
            c = zone.coordinates[0]
            px = self._to_px(c.lat, c.lon, ctx)
            from bimap.engine.tile_math import meters_per_pixel
            mpp = meters_per_pixel(c.lat, zoom)
            r = zone.radius_m / mpp if mpp > 0 else 0
            painter.drawEllipse(QRectF(px.x() - r, px.y() - r, r * 2, r * 2))
        else:
            pts = [self._to_px(c.lat, c.lon, ctx) for c in zone.coordinates]
            if len(pts) >= 2:
                poly = QPolygonF(pts)
                path = QPainterPath()
                path.addPolygon(poly)
                path.closeSubpath()
                painter.drawPath(path)

    def _draw_multi_select_keypoint(self, painter: QPainter, kp, ctx: tuple) -> None:
        """Draw an orange ring for keypoints in the magic-wand selection."""
        pos = self._to_px(kp.lat, kp.lon, ctx)
        r = kp.icon_size + 6
        pen = QPen(QColor(255, 140, 0), 2, Qt.PenStyle.DashDotLine)
        painter.setPen(pen)
        painter.setBrush(QColor(255, 140, 0, 50))
        painter.drawEllipse(QRectF(pos.x() - r, pos.y() - r, r * 2, r * 2))

    # ── Delimitation overlay ───────────────────────────────────────────────────

    def _draw_delimitation(self, painter: QPainter, polygon: list,
                           ctx: tuple, w: int, h: int) -> None:
        """Darken the area outside the delimitation polygon and draw its border."""
        pts = [self._to_px(coord[1], coord[0], ctx) for coord in polygon]
        if len(pts) < 3:
            return
        # Build the inner path (the delimitation area)
        inner = QPainterPath()
        inner.addPolygon(QPolygonF(pts))
        inner.closeSubpath()
        # Outer full-canvas path minus the inner = the "outside" area
        outer = QPainterPath()
        outer.addRect(QRectF(0, 0, w, h))
        mask = outer.subtracted(inner)
        # Fill the outside with a subtle dark overlay
        painter.setBrush(QBrush(QColor(0, 0, 0, 70)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(mask)
        # Draw the delimitation boundary
        border_pen = QPen(QColor(255, 80, 0), 2, Qt.PenStyle.SolidLine)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(inner)

    # ── Scale bar ─────────────────────────────────────────────────────────────

    def _draw_scale_bar(self, painter: QPainter, center_lat: float, zoom: int,
                        w: int, h: int) -> None:
        """Draw a map scale bar in the bottom-left corner."""
        mpp = meters_per_pixel(center_lat, zoom)
        if mpp <= 0:
            return
        # Try to find a nice round scale bar width around 100px
        target_m = 100 * mpp
        magnitude = 10 ** math.floor(math.log10(max(target_m, 1)))
        for nice in (1, 2, 5, 10):
            bar_m = nice * magnitude
            bar_px = bar_m / mpp
            if bar_px >= 80:
                break
        bar_px = bar_m / mpp
        x0, y0 = 16, h - 36
        x1 = x0 + bar_px
        painter.setFont(QFont("Arial", 8))
        bar_color = QColor(30, 30, 30)
        bg_color = QColor(255, 255, 255, 180)
        painter.fillRect(QRectF(x0 - 2, y0 - 14, bar_px + 4, 22), bg_color)
        painter.setPen(QPen(bar_color, 2))
        painter.drawLine(QPointF(x0, y0), QPointF(x1, y0))
        painter.drawLine(QPointF(x0, y0 - 4), QPointF(x0, y0 + 4))
        painter.drawLine(QPointF(x1, y0 - 4), QPointF(x1, y0 + 4))
        label = f"{int(bar_m)} m" if bar_m < 1000 else f"{bar_m / 1000:.1f} km"
        painter.setPen(bar_color)
        fm = QFontMetricsF(painter.font())
        tw = fm.horizontalAdvance(label)
        painter.drawText(QPointF(x0 + (bar_px - tw) / 2, y0 - 4), label)

    # ── North arrow ───────────────────────────────────────────────────────────

    def _draw_north_arrow(self, painter: QPainter, w: int, h: int) -> None:
        """Draw a simple north arrow in the top-right corner."""
        cx, cy, size = w - 36, 44, 16
        # Background circle
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.setPen(QPen(QColor(120, 120, 120), 1))
        painter.drawEllipse(QRectF(cx - size - 4, cy - size - 4, (size + 4) * 2, (size + 4) * 2))
        # North (dark) half
        path_n = QPainterPath()
        path_n.moveTo(cx, cy - size)
        path_n.lineTo(cx - size * 0.45, cy + size * 0.2)
        path_n.lineTo(cx, cy)
        path_n.closeSubpath()
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path_n)
        # South (light) half
        path_s = QPainterPath()
        path_s.moveTo(cx, cy - size)
        path_s.lineTo(cx + size * 0.45, cy + size * 0.2)
        path_s.lineTo(cx, cy)
        path_s.closeSubpath()
        painter.setBrush(QBrush(QColor(200, 200, 200)))
        painter.drawPath(path_s)
        # 'N' label
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(cx - 5, cy - size - 1, 10, 12),
                         Qt.AlignmentFlag.AlignCenter, "N")

    # ── Zone rendering ─────────────────────────────────────────────────────────

    def _draw_zone(self, painter: QPainter, zone: Zone, ctx: tuple) -> None:
        if not zone.coordinates:
            return

        style = zone.style
        fill = QColor(style.fill_color)
        fill.setAlpha(style.fill_alpha)
        border = QColor(style.border_color)

        pen = QPen(border, style.border_width)
        if style.border_style == BorderStyle.DASHED:
            pen.setStyle(Qt.PenStyle.DashLine)
        elif style.border_style == BorderStyle.DOTTED:
            pen.setStyle(Qt.PenStyle.DotLine)

        painter.setPen(pen)
        painter.setBrush(QBrush(fill))

        if zone.zone_type == ZoneType.CIRCLE:
            self._draw_circle_zone(painter, zone, ctx)
        else:
            self._draw_polygon_zone(painter, zone, ctx)

        # Zone label
        if zone.label and zone.label.text:
            self._draw_zone_label(painter, zone, ctx)

    def _draw_polygon_zone(self, painter: QPainter, zone: Zone, ctx: tuple) -> None:
        pts = [self._to_px(c.lat, c.lon, ctx) for c in zone.coordinates]
        if len(pts) < 2:
            return
        poly = QPolygonF(pts)
        path = QPainterPath()
        path.addPolygon(poly)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_circle_zone(self, painter: QPainter, zone: Zone, ctx: tuple) -> None:
        if not zone.coordinates:
            return
        center_lat, center_lon, zoom, w, h = ctx
        c = zone.coordinates[0]
        px = self._to_px(c.lat, c.lon, ctx)
        mpp = meters_per_pixel(c.lat, zoom)
        radius_px = zone.radius_m / mpp if mpp > 0 else 0
        painter.drawEllipse(
            QRectF(px.x() - radius_px, px.y() - radius_px,
                   radius_px * 2, radius_px * 2)
        )

    def _draw_zone_label(self, painter: QPainter, zone: Zone, ctx: tuple) -> None:
        ls = zone.label.style
        font = QFont(ls.font_family, ls.font_size)
        font.setBold(ls.bold)
        font.setItalic(ls.italic)
        painter.setFont(font)
        painter.setPen(QColor(ls.color))

        if zone.coordinates:
            # Centroid of vertices
            lats = [c.lat for c in zone.coordinates]
            lons = [c.lon for c in zone.coordinates]
            cx = sum(lats) / len(lats)
            cy = sum(lons) / len(lons)
            if zone.zone_type == ZoneType.CIRCLE:
                cx, cy = zone.coordinates[0].lat, zone.coordinates[0].lon
            pos = self._to_px(cx, cy, ctx)
            painter.drawText(QPointF(pos.x() + zone.label.offset_x,
                                     pos.y() + zone.label.offset_y),
                             zone.label.text)

    # ── Keypoint rendering ─────────────────────────────────────────────────────

    def _draw_keypoint(self, painter: QPainter, kp: Keypoint, ctx: tuple) -> None:
        pos = self._to_px(kp.lat, kp.lon, ctx)
        size = kp.icon_size
        color = QColor(kp.icon_color)
        shadow = QColor(0, 0, 0, 80)

        # Draw pin shape: circle with dot + stem
        painter.setPen(QPen(shadow, 1))
        painter.setBrush(QBrush(color))
        # Circle head
        painter.drawEllipse(
            QRectF(pos.x() - size / 2, pos.y() - size * 1.5, size, size)
        )
        # Dot centre
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        dot = size * 0.3
        painter.drawEllipse(
            QRectF(pos.x() - dot / 2, pos.y() - size * 1.5 + (size - dot) / 2, dot, dot)
        )
        # Stem
        painter.setPen(QPen(color, 2))
        painter.drawLine(
            QPointF(pos.x(), pos.y() - size * 0.5),
            QPointF(pos.x(), pos.y())
        )

        # Keynote number badge
        if kp.keynote_number is not None:
            badge_font = QFont("Arial", max(7, size // 2))
            badge_font.setBold(True)
            painter.setFont(badge_font)
            painter.setPen(QColor(255, 255, 255))
            badge_rect = QRectF(
                pos.x() - size / 2, pos.y() - size * 1.5, size, size
            )
            painter.drawText(badge_rect,
                             Qt.AlignmentFlag.AlignCenter,
                             str(kp.keynote_number))

        # Title label below pin
        title = kp.info_card.title
        if title:
            label_font = QFont("Arial", 9)
            painter.setFont(label_font)
            painter.setPen(QColor(30, 30, 30))
            fm = QFontMetricsF(label_font)
            tw = fm.horizontalAdvance(title)
            bg_rect = QRectF(pos.x() - tw / 2 - 2, pos.y() + 2, tw + 4, fm.height() + 2)
            painter.fillRect(bg_rect, QColor(255, 255, 255, 200))
            painter.drawText(QPointF(pos.x() - tw / 2, pos.y() + fm.ascent() + 2), title)

    # ── Annotation rendering ───────────────────────────────────────────────────

    def _draw_annotation(self, painter: QPainter, ann: Annotation, ctx: tuple) -> None:
        if ann.ann_type == AnnotationType.TEXT_BOX:
            self._draw_text_box(painter, ann, ctx)
        elif ann.ann_type == AnnotationType.CALLOUT:
            self._draw_callout(painter, ann, ctx)

    def _draw_text_box(self, painter: QPainter, ann: Annotation, ctx: tuple) -> None:
        s = ann.style
        font = QFont(s.font_family, s.font_size)
        font.setBold(s.bold)
        font.setItalic(s.italic)
        painter.setFont(font)

        # Determine position
        if ann.anchor_lat is not None and ann.anchor_lon is not None:
            pos = self._to_px(ann.anchor_lat, ann.anchor_lon, ctx)
            x, y = pos.x(), pos.y()
        else:
            x, y = ann.position.x, ann.position.y

        fm = QFontMetricsF(font)
        lines = ann.content.split("\n")
        max_w = max((fm.horizontalAdvance(l) for l in lines), default=40)
        total_h = fm.height() * len(lines)
        pad = s.padding
        rect = QRectF(x, y, max_w + pad * 2, total_h + pad * 2)

        bg = QColor(s.background_color)
        bg.setAlpha(s.background_alpha)
        painter.fillRect(rect, bg)
        painter.setPen(QPen(QColor(s.border_color), s.border_width))
        painter.drawRect(rect)

        painter.setPen(QColor(s.color))
        for i, line in enumerate(lines):
            painter.drawText(
                QPointF(x + pad, y + pad + fm.ascent() + i * fm.height()),
                line
            )

    def _draw_callout(self, painter: QPainter, ann: Annotation, ctx: tuple) -> None:
        # Draw text box first
        self._draw_text_box(painter, ann, ctx)
        # Then arrow from box to target
        if ann.target_lat is None or ann.target_lon is None:
            return
        if ann.anchor_lat is not None:
            start = self._to_px(ann.anchor_lat, ann.anchor_lon, ctx)
        else:
            start = QPointF(ann.position.x + ann.position.width / 2,
                            ann.position.y + ann.position.height)
        end = self._to_px(ann.target_lat, ann.target_lon, ctx)
        painter.setPen(QPen(QColor(ann.style.color), 2,
                            Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.drawLine(start, end)
        # Arrow head
        self._draw_arrowhead(painter, start, end, QColor(ann.style.color))

    def _draw_arrowhead(
        self, painter: QPainter, start: QPointF, end: QPointF, color: QColor
    ) -> None:
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        angle = math.atan2(dy, dx)
        size = 10.0
        a1 = angle + math.pi * 5 / 6
        a2 = angle - math.pi * 5 / 6
        p1 = QPointF(end.x() + size * math.cos(a1), end.y() + size * math.sin(a1))
        p2 = QPointF(end.x() + size * math.cos(a2), end.y() + size * math.sin(a2))
        painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(color))
        path = QPainterPath()
        path.moveTo(end)
        path.lineTo(p1)
        path.lineTo(p2)
        path.closeSubpath()
        painter.drawPath(path)
