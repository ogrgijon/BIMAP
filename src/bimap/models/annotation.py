"""Annotation domain model (text boxes, callouts, keynotes, legends)."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from bimap.models.style import AnnotationStyle


class AnnotationType(StrEnum):
    TEXT_BOX = "text_box"
    CALLOUT = "callout"
    LEGEND = "legend"
    TITLE_BLOCK = "title_block"
    SCALE_BAR = "scale_bar"
    KEYNOTE_TABLE = "keynote_table"
    NORTH_ARROW = "north_arrow"


class CanvasPosition(BaseModel):
    """Position on the PDF/canvas in points (pt), top-left = (0,0)."""
    x: float = 100.0
    y: float = 100.0
    width: float = 200.0
    height: float = 60.0


class Annotation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ann_type: AnnotationType = AnnotationType.TEXT_BOX
    # Lat/lon anchor (if placed on map). None = floating (canvas-only).
    anchor_lat: float | None = None
    anchor_lon: float | None = None
    # Canvas position in widget-relative pixels (updated on render).
    position: CanvasPosition = Field(default_factory=CanvasPosition)
    content: str = "Text"
    style: AnnotationStyle = Field(default_factory=AnnotationStyle)
    # For callout arrows: the lat/lon point the arrow targets.
    target_lat: float | None = None
    target_lon: float | None = None
    visible: bool = True
    layer: str = "Default"
