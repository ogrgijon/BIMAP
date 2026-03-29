"""
Tests for UI widgets — requires QtTest / offscreen QApplication.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def app():
    from PyQt6.QtWidgets import QApplication
    instance = QApplication.instance() or QApplication([])
    yield instance
    # Cancel all pending tile fetches and drain the thread pool gracefully.
    # This prevents QPixmap creation after QApplication is destroyed (qFatal).
    import bimap.ui.map_canvas.tile_fetcher as _tf
    from PyQt6.QtCore import QThreadPool
    _tf._cancelled = True
    for w in instance.topLevelWidgets():
        w.close()
    instance.processEvents()
    QThreadPool.globalInstance().waitForDone(-1)
    _tf._cancelled = False


class TestTileWidget:
    def test_instantiation(self, app):
        from bimap.ui.map_canvas.tile_widget import TileWidget
        w = TileWidget()
        assert w is not None

    def test_set_project(self, app):
        from bimap.ui.map_canvas.tile_widget import TileWidget
        from bimap.models.project import Project
        w = TileWidget()
        p = Project()
        w.set_project(p)
        assert w.center_lat == p.map_state.center_lat
        assert w.zoom == p.map_state.zoom

    def test_zoom_in_out(self, app):
        from bimap.ui.map_canvas.tile_widget import TileWidget
        from bimap.models.project import Project
        w = TileWidget()
        w.set_project(Project())
        initial_zoom = w.zoom
        w.zoom_in()
        assert w.zoom == initial_zoom + 1
        w.zoom_out()
        assert w.zoom == initial_zoom

    def test_zoom_limits(self, app):
        from bimap.ui.map_canvas.tile_widget import TileWidget
        from bimap.config import MIN_ZOOM, TILE_PROVIDERS, DEFAULT_TILE_PROVIDER
        from bimap.models.project import Project
        w = TileWidget()
        w.set_project(Project())
        provider_max = TILE_PROVIDERS.get(DEFAULT_TILE_PROVIDER, {}).get("max_zoom", 19)
        for _ in range(30):
            w.zoom_in()
        assert w.zoom == provider_max
        for _ in range(30):
            w.zoom_out()
        assert w.zoom == MIN_ZOOM

    def test_set_tool(self, app):
        from bimap.ui.map_canvas.tile_widget import TileWidget
        from bimap.ui.map_canvas.interaction import ToolMode
        w = TileWidget()
        w.set_tool(ToolMode.DRAW_POLYGON)
        assert w.interaction.tool == ToolMode.DRAW_POLYGON

    def test_set_tile_provider(self, app):
        from bimap.ui.map_canvas.tile_widget import TileWidget
        w = TileWidget()
        w.set_tile_provider("cartodb_light")
        assert w.tile_provider == "cartodb_light"

    def test_invalid_provider_ignored(self, app):
        from bimap.ui.map_canvas.tile_widget import TileWidget
        w = TileWidget()
        original = w.tile_provider
        w.set_tile_provider("nonexistent_provider")
        assert w.tile_provider == original


class TestLayersPanel:
    def test_instantiation(self, app):
        from bimap.ui.panels.layers_panel import LayersPanel
        p = LayersPanel()
        assert p is not None

    def test_refresh(self, app):
        from bimap.ui.panels.layers_panel import LayersPanel
        from bimap.models.project import Project
        from bimap.models.zone import Zone
        lp = LayersPanel()
        proj = Project()
        proj.zones.append(Zone(name="Test"))
        lp.refresh(proj)   # should not raise


class TestMainWindow:
    def test_instantiation(self, app):
        from bimap.ui.main_window import MainWindow
        w = MainWindow()
        assert w is not None

    def test_window_title(self, app):
        from bimap.ui.main_window import MainWindow
        from bimap.config import APP_NAME
        w = MainWindow()
        assert APP_NAME in w.windowTitle()
