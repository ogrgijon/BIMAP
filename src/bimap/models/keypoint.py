"""Keypoint (map pin / marker) domain model."""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from bimap.models.zone import DataBinding


class InfoCardField(BaseModel):
    label: str
    value: str


class InfoCard(BaseModel):
    title: str = ""
    subtitle: str = ""
    fields: list[InfoCardField] = Field(default_factory=list)
    image_path: str = ""        # local file path or URL
    link_url: str = ""
    notes: str = ""


class Keypoint(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    lat: float = 0.0
    lon: float = 0.0
    icon: str = "pin"           # built-in icon name or path to custom SVG/PNG
    icon_color: str = "#E74C3C"
    icon_size: int = 14
    info_card: InfoCard = Field(default_factory=InfoCard)
    visible: bool = True
    data_binding: DataBinding | None = None
    group: str = "Default"
    layer: str = "Default"
    keynote_number: int | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def name(self) -> str:
        """Convenience alias for info_card.title."""
        return self.info_card.title

    @name.setter
    def name(self, value: str) -> None:
        self.info_card.title = value
