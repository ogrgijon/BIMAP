"""App-wide configuration and constants."""

from __future__ import annotations

import os
from pathlib import Path

# ── Application ──────────────────────────────────────────────────────────────
APP_NAME = "BIMAP"
APP_VERSION = "0.1.0"
APP_ORGANISATION = "BIMAP"

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME_DIR: Path = Path.home()
APP_DATA_DIR: Path = HOME_DIR / ".bimap"
TILE_CACHE_DIR: Path = APP_DATA_DIR / "tile_cache"
PROJECTS_DIR: Path = APP_DATA_DIR / "projects"
THEME_QSS_PATH: Path = Path(__file__).parent / "ui" / "dark_theme.qss"

for _d in (APP_DATA_DIR, TILE_CACHE_DIR, PROJECTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Map ───────────────────────────────────────────────────────────────────────
TILE_SIZE: int = 256
MIN_ZOOM: int = 1
MAX_ZOOM: int = 19
DEFAULT_ZOOM: int = 12
DEFAULT_CENTER_LAT: float = 40.4168   # Madrid
DEFAULT_CENTER_LON: float = -3.7038

# ── Tile Providers ────────────────────────────────────────────────────────────
TILE_PROVIDERS: dict[str, dict] = {
    "osm_standard": {
        "label": "OpenStreetMap Standard",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "max_zoom": 19,
        "attribution": "© OpenStreetMap contributors",
    },
    "cartodb_light": {
        "label": "CartoDB Positron (Light)",
        "url": "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
        "max_zoom": 19,
        "attribution": "© OpenStreetMap contributors © CartoDB",
    },
    "cartodb_dark": {
        "label": "CartoDB Dark Matter",
        "url": "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
        "max_zoom": 19,
        "attribution": "© OpenStreetMap contributors © CartoDB",
    },
    "topo": {
        "label": "OpenTopoMap",
        "url": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
        "max_zoom": 17,
        "attribution": "© OpenTopoMap contributors",
    },
}
DEFAULT_TILE_PROVIDER: str = "osm_standard"

# ── HTTP Headers (OSM usage policy requires a meaningful User-Agent) ─────────
HTTP_HEADERS: dict[str, str] = {
    "User-Agent": f"{APP_NAME}/{APP_VERSION} (https://github.com/ogrgijon/BIMAP)",
    "Accept": "image/png,image/*,*/*",
}

# ── Tile Cache ────────────────────────────────────────────────────────────────
TILE_CACHE_SIZE_BYTES: int = 512 * 1024 * 1024   # 512 MB
TILE_CACHE_EXPIRE_DAYS: int = 7

# ── Geocoding ─────────────────────────────────────────────────────────────────
NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT: str = f"{APP_NAME}/{APP_VERSION}"

# ── Drawing ───────────────────────────────────────────────────────────────────
DEFAULT_ZONE_COLOR: str = "#3388FF"
DEFAULT_ZONE_ALPHA: int = 80          # 0-255
DEFAULT_ZONE_BORDER_WIDTH: int = 2
DEFAULT_KEYPOINT_COLOR: str = "#E74C3C"
DEFAULT_KEYPOINT_SIZE: int = 14

# ── PDF Export ────────────────────────────────────────────────────────────────
PDF_DEFAULT_DPI: int = 300
PDF_PAGE_SIZES: dict[str, tuple[float, float]] = {
    "A4": (595.27, 841.89),
    "A3": (841.89, 1190.55),
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
}

# ── Project file ──────────────────────────────────────────────────────────────
PROJECT_FILE_EXTENSION: str = ".bimap"

# ── Auto-save ────────────────────────────────────────────────────────────────
AUTOSAVE_INTERVAL_MS: int = 60_000   # 1 minute

# ── Undo ─────────────────────────────────────────────────────────────────────
UNDO_STACK_LIMIT: int = 100
