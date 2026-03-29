"""
OverlayRenderer — paints zones, keypoints, and annotations on the map canvas.
"""

from __future__ import annotations

import math
import os
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
    QPixmap,
    QPolygonF,
)
try:
    from PyQt6.QtSvg import QSvgRenderer
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False

from bimap.engine.tile_math import lat_lon_to_pixel, meters_per_pixel
from bimap.models.annotation import Annotation, AnnotationType
from bimap.models.keypoint import Keypoint
from bimap.models.live_layer import LiveLayer
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
        show_scale_bar: bool = True,
        show_north_arrow: bool = True,
        live_layers: list[LiveLayer] | None = None,
        live_positions: dict[str, list[dict]] | None = None,
        show_grid: bool = False,
        grid_scale: float = 1.0,
    ) -> None:
        ctx = (center_lat, center_lon, zoom, w, h)
        _multi = set(multi_selected) if multi_selected else set()
        if show_grid:
            self._draw_grid(painter, ctx, grid_scale)
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
        if show_scale_bar:
            self._draw_scale_bar(painter, center_lat, zoom, w, h)
        if show_north_arrow:
            self._draw_north_arrow(painter, w, h)
        if live_layers:
            self._draw_live_layers(painter, live_layers, live_positions or {}, ctx)

    # ── to-pixel helper ────────────────────────────────────────────────────────

    @staticmethod
    def _to_px(lat: float, lon: float, ctx: tuple) -> QPointF:
        center_lat, center_lon, zoom, w, h = ctx
        p = lat_lon_to_pixel(lat, lon, center_lat, center_lon, zoom, w, h)
        return QPointF(p.px, p.py)

    # ── Selection highlights ───────────────────────────────────────────────────

    def _draw_selection_zone(self, painter: QPainter, zone: Zone, ctx: tuple) -> None:
        """Draw dashed cyan selection outline over a selected zone.

        Uses the same path-building and rotation logic as _draw_zone so the
        selection outline always perfectly overlaps the rendered zone.
        """
        pen = QPen(QColor(0, 180, 255), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if zone.zone_type == ZoneType.CIRCLE:
            if zone.coordinates:
                c = zone.coordinates[0]
                px = self._to_px(c.lat, c.lon, ctx)
                _, _, zoom, _, _ = ctx
                mpp = meters_per_pixel(c.lat, zoom)
                r = zone.radius_m / mpp if mpp > 0 else 0
                painter.drawEllipse(QRectF(px.x() - r, px.y() - r, r * 2, r * 2))
        else:
            # Build selection path the same way _draw_zone does so it always
            # matches the visual shape (including dimensioned-rect rotation).
            if zone.zone_type == ZoneType.RECTANGLE and zone.width_m > 0 and zone.height_m > 0:
                path = self._metered_rect_path(zone, ctx)
            else:
                path = self._polygon_path(zone, ctx)
            if path is None:
                return
            rotation_deg = getattr(zone, "rotation_deg", 0.0)
            rotated = rotation_deg != 0.0 and bool(zone.coordinates)
            if rotated:
                pxs = [self._to_px(c.lat, c.lon, ctx) for c in zone.coordinates]
                piv_x = sum(p.x() for p in pxs) / len(pxs)
                piv_y = sum(p.y() for p in pxs) / len(pxs)
                painter.save()
                painter.translate(piv_x, piv_y)
                painter.rotate(rotation_deg)
                painter.translate(-piv_x, -piv_y)
            painter.drawPath(path)
            if rotated:
                painter.restore()

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
            mpp = meters_per_pixel(c.lat, zoom)
            r = zone.radius_m / mpp if mpp > 0 else 0
            painter.drawEllipse(QRectF(px.x() - r, px.y() - r, r * 2, r * 2))
        else:
            pts = [self._to_px(c.lat, c.lon, ctx) for c in zone.coordinates]
            if len(pts) >= 2:
                rotation_deg = getattr(zone, "rotation_deg", 0.0)
                _is_dimensioned_rect = (
                    zone.zone_type == ZoneType.RECTANGLE
                    and zone.width_m > 0 and zone.height_m > 0
                )
                _needs_rot = rotation_deg != 0.0 and not _is_dimensioned_rect
                if _needs_rot:
                    piv_x = sum(p.x() for p in pts) / len(pts)
                    piv_y = sum(p.y() for p in pts) / len(pts)
                    painter.save()
                    painter.translate(piv_x, piv_y)
                    painter.rotate(rotation_deg)
                    painter.translate(-piv_x, -piv_y)
                poly = QPolygonF(pts)
                path = QPainterPath()
                path.addPolygon(poly)
                path.closeSubpath()
                painter.drawPath(path)
                if _needs_rot:
                    painter.restore()

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

    # ── Live-feed layer rendering ──────────────────────────────────────────────

    def _draw_live_layers(
        self,
        painter: QPainter,
        live_layers: list[LiveLayer],
        live_positions: dict[str, list[dict]],
        ctx: tuple,
    ) -> None:
        for layer in live_layers:
            if not layer.visible:
                continue
            positions = live_positions.get(layer.id, [])
            if not positions:
                continue
            color = QColor(layer.icon_color)
            label_font = QFont("Arial", max(7, layer.icon_size - 4))
            icon_font = QFont("Arial", layer.icon_size)

            # Draw trail polylines first (bottom layer)
            trail = layer.trail_length
            if trail > 0:
                trail_pen = QPen(color, 1.5, Qt.PenStyle.SolidLine)
                trail_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(trail_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                # trail_positions may hold the recent history stored per marker
                for pos in positions:
                    history = pos.get("_trail")
                    if isinstance(history, list) and len(history) >= 2:
                        pts = [self._to_px(p["lat"], p["lon"], ctx) for p in history[-trail:]]
                        for i in range(1, len(pts)):
                            alpha = int(80 + 120 * i / len(pts))
                            tc = QColor(color)
                            tc.setAlpha(alpha)
                            trail_pen.setColor(tc)
                            painter.setPen(trail_pen)
                            painter.drawLine(pts[i - 1], pts[i])

            # Draw markers
            for pos in positions:
                px = self._to_px(pos["lat"], pos["lon"], ctx)
                heading = pos.get("heading")
                icon_glyph = layer.icon  # Unicode glyph (may be multi-codepoint emoji)
                use_glyph = icon_glyph not in ("▶", "●", "")

                # When the layer icon is a directional arrow (▶) and heading is
                # known, draw a proper rotated geometric arrow.
                if heading is not None and not use_glyph:
                    try:
                        h_deg = float(heading)
                    except (TypeError, ValueError):
                        h_deg = 0.0
                    painter.save()
                    painter.translate(px)
                    painter.rotate(h_deg)
                    arrow_pen = QPen(color, 1)
                    painter.setPen(arrow_pen)
                    painter.setBrush(QBrush(color))
                    r = layer.icon_size / 2.0
                    arrow = QPainterPath()
                    arrow.moveTo(0, -r * 1.4)
                    arrow.lineTo(-r * 0.55, r * 0.7)
                    arrow.lineTo(0, r * 0.2)
                    arrow.lineTo(r * 0.55, r * 0.7)
                    arrow.closeSubpath()
                    painter.drawPath(arrow)
                    painter.restore()
                elif use_glyph:
                    # Draw Unicode/emoji icon centred on the position
                    painter.setFont(icon_font)
                    metrics = QFontMetricsF(icon_font)
                    gw = metrics.horizontalAdvance(icon_glyph)
                    gh = metrics.height()
                    painter.setPen(color)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawText(
                        QRectF(px.x() - gw / 2, px.y() - gh / 2, gw, gh),
                        Qt.AlignmentFlag.AlignCenter,
                        icon_glyph,
                    )
                else:
                    # Dot marker (● or empty icon)
                    r = layer.icon_size / 2.0
                    dot_color = QColor(color)
                    dot_color.setAlpha(220)
                    painter.setBrush(QBrush(dot_color))
                    outline = QPen(QColor(0, 0, 0, 80), 1)
                    painter.setPen(outline)
                    painter.drawEllipse(QRectF(px.x() - r, px.y() - r, r * 2, r * 2))

                # Label
                label = pos.get("label", "")
                _, _, zoom, _, _ = ctx
                if label and zoom >= 8:
                    painter.setFont(label_font)
                    metrics = QFontMetricsF(label_font)
                    lw = metrics.horizontalAdvance(label) + 4
                    lh = metrics.height()
                    lx = px.x() - lw / 2
                    ly = px.y() - layer.icon_size - 3 - lh
                    bg = QColor(0, 0, 0, 140)
                    painter.setBrush(QBrush(bg))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(QRectF(lx, ly, lw, lh), 2, 2)
                    painter.setPen(QColor(255, 255, 255, 230))
                    painter.drawText(QRectF(lx, ly, lw, lh),
                                     Qt.AlignmentFlag.AlignCenter, label)

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
            zone_path = self._circle_path(zone, ctx)
        elif (
            zone.zone_type == ZoneType.RECTANGLE
            and zone.width_m > 0
            and zone.height_m > 0
        ):
            zone_path = self._metered_rect_path(zone, ctx)
        else:
            zone_path = self._polygon_path(zone, ctx)

        if zone_path is not None:
            rotation_deg = getattr(zone, "rotation_deg", 0.0)
            rotated = rotation_deg != 0.0 and zone.zone_type != ZoneType.CIRCLE
            if rotated and zone.coordinates:
                pxs = [self._to_px(c.lat, c.lon, ctx) for c in zone.coordinates]
                pivot_x = sum(p.x() for p in pxs) / len(pxs)
                pivot_y = sum(p.y() for p in pxs) / len(pxs)
                painter.save()
                painter.translate(pivot_x, pivot_y)
                painter.rotate(rotation_deg)
                painter.translate(-pivot_x, -pivot_y)
            painter.drawPath(zone_path)
            if zone.svg_fill_url and os.path.isfile(zone.svg_fill_url):
                self._draw_svg_fill(painter, zone_path, zone.svg_fill_url)
            if rotated:
                painter.restore()

        # Zone label
        if zone.label and zone.label.text:
            _, _, zoom, _, _ = ctx
            if zoom >= 8:
                self._draw_zone_label(painter, zone, ctx)

    def _polygon_path(self, zone: Zone, ctx: tuple) -> QPainterPath | None:
        pts = [self._to_px(c.lat, c.lon, ctx) for c in zone.coordinates]
        if len(pts) < 2:
            return None
        poly = QPolygonF(pts)
        path = QPainterPath()
        path.addPolygon(poly)
        path.closeSubpath()
        return path

    def _circle_path(self, zone: Zone, ctx: tuple) -> QPainterPath | None:
        if not zone.coordinates:
            return None
        _, _, zoom, _, _ = ctx
        c = zone.coordinates[0]
        px = self._to_px(c.lat, c.lon, ctx)
        mpp = meters_per_pixel(c.lat, zoom)
        radius_px = zone.radius_m / mpp if mpp > 0 else 0
        rect = QRectF(px.x() - radius_px, px.y() - radius_px,
                      radius_px * 2, radius_px * 2)
        path = QPainterPath()
        path.addEllipse(rect)
        return path

    def _metered_rect_path(self, zone: Zone, ctx: tuple) -> QPainterPath | None:
        """Build a rectangle QPainterPath sized in metres, centred on the zone's centroid."""
        if not zone.coordinates:
            return None
        _, _, zoom, _, _ = ctx
        pts = [self._to_px(c.lat, c.lon, ctx) for c in zone.coordinates]
        if not pts:
            return None
        cx = sum(p.x() for p in pts) / len(pts)
        cy = sum(p.y() for p in pts) / len(pts)
        # Use lat of first coord for mpp approximation
        mpp = meters_per_pixel(zone.coordinates[0].lat, zoom)
        hw = (zone.width_m / 2.0) / mpp if mpp > 0 else 0
        hh = (zone.height_m / 2.0) / mpp if mpp > 0 else 0
        rect = QRectF(cx - hw, cy - hh, hw * 2, hh * 2)
        path = QPainterPath()
        path.addRect(rect)
        return path

    def _draw_svg_fill(self, painter: QPainter, clip_path: QPainterPath, svg_url: str) -> None:
        """Render an SVG file tiled/fitted inside a painter path, clipped to the path."""
        try:
            from PyQt6.QtSvg import QSvgRenderer
        except ImportError:
            return
        renderer = QSvgRenderer(svg_url)
        if not renderer.isValid():
            return
        bounds = clip_path.boundingRect()
        painter.save()
        painter.setClipPath(clip_path, Qt.ClipOperation.IntersectClip)
        renderer.render(painter, bounds)
        painter.restore()

    # ── Kept for backward-compat (called nowhere externally but guard anyway) ─ #
    def _draw_polygon_zone(self, painter: QPainter, zone: Zone, ctx: tuple) -> None:
        path = self._polygon_path(zone, ctx)
        if path is not None:
            painter.drawPath(path)

    def _draw_circle_zone(self, painter: QPainter, zone: Zone, ctx: tuple) -> None:
        path = self._circle_path(zone, ctx)
        if path is not None:
            painter.drawPath(path)

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

            # Dimension sub-label
            dim_text = ""
            if (zone.zone_type == ZoneType.RECTANGLE
                    and getattr(zone, "width_m", 0) > 0
                    and getattr(zone, "height_m", 0) > 0):
                dim_text = f"({zone.width_m:.1f} x {zone.height_m:.1f} m)"
            elif (zone.zone_type == ZoneType.CIRCLE
                    and getattr(zone, "radius_m", 0) > 0):
                dim_text = f"(r={zone.radius_m:.1f} m)"
            if dim_text:
                font2 = QFont(ls.font_family, max(ls.font_size - 2, 7))
                painter.setFont(font2)
                painter.drawText(
                    QPointF(pos.x() + zone.label.offset_x,
                            pos.y() + zone.label.offset_y + ls.font_size + 3),
                    dim_text,
                )

    # ── Keypoint rendering ─────────────────────────────────────────────────────

    def _draw_grid(self, painter: QPainter, ctx: tuple, grid_scale: float = 1.0) -> None:
        """Draw a coordinate grid (precision / 'square paper' overlay)."""
        from bimap.engine.tile_math import pixel_to_lat_lon
        center_lat, center_lon, zoom, w, h = ctx
        mpp = meters_per_pixel(center_lat, zoom)

        # Choose a base grid spacing that gives 5–25 lines across the viewport
        for spacing_m in (10, 25, 50, 100, 250, 500, 1000, 2500, 5000,
                          10000, 25000, 50000, 100000, 250000, 500000):
            spacing_px = spacing_m / mpp
            if w / spacing_px < 25:
                break

        # Apply user density multiplier (>1 = coarser, <1 = finer)
        spacing_m *= grid_scale

        # Convert to degrees
        spacing_lat = spacing_m / 111_320.0
        spacing_lon = spacing_m / (111_320.0 * math.cos(math.radians(center_lat)) + 1e-9)

        # Corners in lat/lon
        tl_lat, tl_lon = pixel_to_lat_lon(0, 0, center_lat, center_lon, zoom, w, h)
        br_lat, br_lon = pixel_to_lat_lon(w, h, center_lat, center_lon, zoom, w, h)

        pen_line = QPen(QColor(80, 160, 220, 100), 1)
        pen_label = QPen(QColor(120, 200, 255, 200))
        font = QFont("Consolas", 7)
        painter.setFont(font)

        # Vertical grid lines (constant longitude)
        start_lon = math.floor(min(tl_lon, br_lon) / spacing_lon) * spacing_lon
        end_lon = math.ceil(max(tl_lon, br_lon) / spacing_lon) * spacing_lon
        lon_val = start_lon
        while lon_val <= end_lon:
            p_top = self._to_px(tl_lat, lon_val, ctx)
            p_bot = self._to_px(br_lat, lon_val, ctx)
            painter.setPen(pen_line)
            painter.drawLine(QPointF(p_top.x(), 0), QPointF(p_top.x(), h))
            painter.setPen(pen_label)
            painter.drawText(QPointF(p_top.x() + 2, 10), f"{lon_val:.4f}")
            lon_val += spacing_lon

        # Horizontal grid lines (constant latitude)
        start_lat = math.floor(min(tl_lat, br_lat) / spacing_lat) * spacing_lat
        end_lat = math.ceil(max(tl_lat, br_lat) / spacing_lat) * spacing_lat
        lat_val = start_lat
        while lat_val <= end_lat:
            p_left = self._to_px(lat_val, tl_lon, ctx)
            painter.setPen(pen_line)
            painter.drawLine(QPointF(0, p_left.y()), QPointF(w, p_left.y()))
            painter.setPen(pen_label)
            painter.drawText(QPointF(2, p_left.y() - 2), f"{lat_val:.4f}")
            lat_val += spacing_lat

    # ── Keypoint rendering ─────────────────────────────────────────────────────

    def _draw_keypoint(self, painter: QPainter, kp: Keypoint, ctx: tuple) -> None:
        pos = self._to_px(kp.lat, kp.lon, ctx)
        size = kp.icon_size
        color = QColor(kp.icon_color)
        shadow = QColor(0, 0, 0, 80)
        icon_val = getattr(kp, "icon", "pin")

        # ── Custom file icon (SVG or raster) ─────────────────────────────── #
        if icon_val and icon_val not in ("pin", "circle", "star", "square", "diamond") \
                and os.path.isfile(icon_val):
            rect = QRectF(pos.x() - size, pos.y() - size * 2, size * 2, size * 2)
            ext = os.path.splitext(icon_val)[1].lower()
            if ext == ".svg" and _SVG_AVAILABLE:
                renderer = QSvgRenderer(icon_val)
                painter.save()
                renderer.render(painter, rect)
                painter.restore()
            else:
                pix = QPixmap(icon_val)
                if not pix.isNull():
                    pix = pix.scaled(
                        int(size * 2), int(size * 2),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    painter.drawPixmap(
                        int(pos.x() - pix.width() / 2),
                        int(pos.y() - pix.height()),
                        pix,
                    )

        # ── Built-in icon shapes ──────────────────────────────────────────── #
        elif icon_val == "circle":
            painter.setPen(QPen(shadow, 1))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QRectF(pos.x() - size / 2, pos.y() - size, size, size))

        elif icon_val == "square":
            painter.setPen(QPen(shadow, 1))
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(pos.x() - size / 2, pos.y() - size, size, size))

        elif icon_val == "diamond":
            painter.setPen(QPen(shadow, 1))
            painter.setBrush(QBrush(color))
            cx, cy = pos.x(), pos.y() - size * 0.5
            pts = QPolygonF([
                QPointF(cx, cy - size * 0.5),
                QPointF(cx + size * 0.5, cy),
                QPointF(cx, cy + size * 0.5),
                QPointF(cx - size * 0.5, cy),
            ])
            painter.drawPolygon(pts)

        elif icon_val == "star":
            painter.setPen(QPen(shadow, 1))
            painter.setBrush(QBrush(color))
            cx, cy = pos.x(), pos.y() - size
            path = QPainterPath()
            outer, inner = size * 0.5, size * 0.2
            for i in range(10):
                angle = math.radians(i * 36 - 90)
                r = outer if i % 2 == 0 else inner
                x, y = cx + r * math.cos(angle), cy + r * math.sin(angle)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            painter.drawPath(path)

        else:  # default: "pin"
            # Draw pin shape: circle with dot + stem
            painter.setPen(QPen(shadow, 1))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(
                QRectF(pos.x() - size / 2, pos.y() - size * 1.5, size, size)
            )
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            dot = size * 0.3
            painter.drawEllipse(
                QRectF(pos.x() - dot / 2, pos.y() - size * 1.5 + (size - dot) / 2, dot, dot)
            )
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
        _, _, zoom, _, _ = ctx
        if title and zoom >= 8:
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
