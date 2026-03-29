"""GeoJSON file or URL data source connector."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from bimap.config import HTTP_HEADERS
from bimap.data.base import DataSourceBase


class GeoJsonSource(DataSourceBase):
    """Reads GeoJSON from a local file or remote URL."""

    def __init__(self, path_or_url: str) -> None:
        self._src = path_or_url
        self._rows: list[dict[str, Any]] = []
        self._columns: list[str] = []

    def connect(self) -> None:
        if not (self._src.startswith("http") or Path(self._src).exists()):
            raise ValueError(f"GeoJSON source not found: {self._src}")

    def fetch(self) -> list[dict[str, Any]]:
        if self._src.startswith("http"):
            try:
                resp = requests.get(self._src, headers=HTTP_HEADERS, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as exc:
                raise ValueError(f"GeoJSON fetch failed: {exc}") from exc
        else:
            data = json.loads(Path(self._src).read_text(encoding="utf-8"))

        features = data.get("features", [])
        rows = []
        for f in features:
            props = f.get("properties") or {}
            geom = f.get("geometry") or {}
            row = {"_geom_type": geom.get("type", ""), **props}
            coords = geom.get("coordinates")
            if coords:
                row["_coordinates"] = json.dumps(coords)
            rows.append(row)
        self._rows = rows
        if rows:
            self._columns = list(rows[0].keys())
        return rows

    def get_columns(self) -> list[str]:
        return self._columns

    def disconnect(self) -> None:
        self._rows = []
        self._columns = []
