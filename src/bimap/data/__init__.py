"""Data source package — factory function."""

from __future__ import annotations

from typing import Any

from bimap.data.api_source import ApiSource
from bimap.data.base import DataSourceBase
from bimap.data.csv_source import CsvSource
from bimap.data.geojson_source import GeoJsonSource
from bimap.data.refresh import DataRefreshManager, RefreshWorker
from bimap.data.sql_source import SqlSource
from bimap.models.data_source import DataSource, SourceType


def build_connector(ds: DataSource) -> DataSourceBase:
    """Factory: create the appropriate connector from a DataSource model."""
    c = ds.connection
    match ds.source_type:
        case SourceType.CSV | SourceType.EXCEL:
            return CsvSource(
                file_path=c.get("file_path", ""),
                sheet_name=c.get("sheet_name", 0),
            )
        case SourceType.SQL:
            return SqlSource(
                connection_string=c.get("connection_string", ""),
                query=c.get("query", "SELECT 1"),
            )
        case SourceType.REST_API:
            return ApiSource(
                url=c.get("url", ""),
                data_path=c.get("data_path", ""),
                auth_token=c.get("auth_token", ""),
            )
        case SourceType.GEOJSON:
            return GeoJsonSource(path_or_url=c.get("path_or_url", ""))
        case _:
            raise ValueError(f"Unsupported source type: {ds.source_type}")


__all__ = [
    "ApiSource",
    "CsvSource",
    "DataRefreshManager",
    "DataSourceBase",
    "GeoJsonSource",
    "RefreshWorker",
    "SqlSource",
    "build_connector",
]
