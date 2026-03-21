"""Root Project model."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from bimap.models.annotation import Annotation
from bimap.models.data_source import DataSource
from bimap.models.keypoint import Keypoint
from bimap.models.layer import Layer
from bimap.models.map_state import MapState
from bimap.models.pdf_layout import PDFLayout
from bimap.models.style import StylePreset
from bimap.models.zone import Zone


class Project(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = "Untitled Project"
    file_path: str = ""        # serialized as string; empty = unsaved
    map_state: MapState = Field(default_factory=MapState)
    zones: list[Zone] = Field(default_factory=list)
    keypoints: list[Keypoint] = Field(default_factory=list)
    annotations: list[Annotation] = Field(default_factory=list)
    layers: list[Layer] = Field(default_factory=lambda: [Layer(name="Default")])
    data_sources: list[DataSource] = Field(default_factory=list)
    pdf_layout: PDFLayout = Field(default_factory=PDFLayout)
    style_presets: list[StylePreset] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)

    def mark_modified(self) -> None:
        self.modified_at = datetime.now()

    @property
    def path(self) -> Path | None:
        return Path(self.file_path) if self.file_path else None
