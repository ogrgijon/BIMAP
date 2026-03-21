"""
Map canvas widget — renders OSM tiles + zone/keypoint/annotation overlays.

Architecture:
- TileWidget (QWidget) — top-level composite
  ├─ TileFetcher (QThread) — downloads tiles from network
  ├─ TileCache — on-disk tile cache
  ├─ OverlayRenderer — paints zones, keypoints, annotations
  └─ InteractionHandler — translates mouse/keyboard events → tool actions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QRunnable, Qt, QThread, QThreadPool, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import requests

from bimap.config import HTTP_HEADERS, TILE_PROVIDERS, TILE_SIZE
from bimap.engine.tile_math import TileCoord
from bimap.ui.map_canvas.tile_cache import TileCache

if TYPE_CHECKING:
    pass

# Singleton cache shared across all canvases
_tile_cache: TileCache | None = None


def get_tile_cache() -> TileCache:
    global _tile_cache
    if _tile_cache is None:
        _tile_cache = TileCache()
    return _tile_cache


# ── Tile fetch runnable ────────────────────────────────────────────────────────

# Cancellation flag — set to True to stop all pending tile fetches immediately
_cancelled: bool = False


class TileFetchSignals(QObject):
    tile_ready = pyqtSignal(int, int, int, QPixmap)    # x, y, z, pixmap
    tile_error = pyqtSignal(int, int, int)


class TileFetchRunnable(QRunnable):
    """Downloads a single tile in the thread pool."""

    def __init__(self, tile: TileCoord, url_template: str) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._tile = tile
        self._url_template = url_template
        self.signals = TileFetchSignals()

    def run(self) -> None:
        global _cancelled
        if _cancelled:
            return
        t = self._tile
        cache = get_tile_cache()
        cache_key = f"{self._url_template}_{t.z}_{t.x}_{t.y}"
        cached = cache.get(cache_key)
        if cached:
            pm = _bytes_to_pixmap(cached)
            if pm and not pm.isNull():
                self.signals.tile_ready.emit(t.x, t.y, t.z, pm)
                return

        url = (
            self._url_template
            .replace("{z}", str(t.z))
            .replace("{x}", str(t.x))
            .replace("{y}", str(t.y))
        )
        import time
        data: bytes | None = None
        for attempt in range(3):
            if _cancelled:
                return
            try:
                resp = requests.get(url, headers=HTTP_HEADERS, timeout=10)
                resp.raise_for_status()
                data = resp.content
                break
            except requests.RequestException:
                if attempt == 2:
                    self.signals.tile_error.emit(t.x, t.y, t.z)
                    return
                time.sleep(0.4 * (2 ** attempt))

        cache.put(cache_key, data)
        pm = _bytes_to_pixmap(data)
        if pm and not pm.isNull():
            self.signals.tile_ready.emit(t.x, t.y, t.z, pm)
        else:
            self.signals.tile_error.emit(t.x, t.y, t.z)


def _bytes_to_pixmap(data: bytes) -> QPixmap:
    img = QImage()
    img.loadFromData(data)
    return QPixmap.fromImage(img)
