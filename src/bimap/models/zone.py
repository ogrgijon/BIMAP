"""Zone (polygon/shape) domain model."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from bimap.models.style import ZoneLabel, ZoneStyle


class ZoneType(StrEnum):
    POLYGON = "polygon"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    FREEHAND = "freehand"


class LatLon(BaseModel):
    lat: float
    lon: float


class DataBinding(BaseModel):
    """Link a data-source column to a zone/keypoint property."""
    source_id: str           # UUID str of the DataSource
    column: str              # column/field name in the source
    target_property: str     # e.g. "style.fill_color", "info_card.revenue"
    transform: str = ""      # optional Python expression, 'value' is the variable


class Zone(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = "Zone"
    zone_type: ZoneType = ZoneType.POLYGON
    # For polygon/rectangle/freehand: list of vertices.
    # For circle: [center] and radius_m field.
    coordinates: list[LatLon] = Field(default_factory=list)
    radius_m: float = 500.0              # only used for ZoneType.CIRCLE
    group: str = "Default"
    visible: bool = True
    style: ZoneStyle = Field(default_factory=ZoneStyle)
    label: ZoneLabel = Field(default_factory=ZoneLabel)
    data_binding: DataBinding | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    locked: bool = False              # locked zones cannot be selected/moved
    layer: str = "Default"
