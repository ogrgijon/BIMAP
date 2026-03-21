"""
Tests for engine/project_io.py — serialisation round-trip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bimap.models.project import Project
from bimap.models.zone import Zone, ZoneType, LatLon
from bimap.models.keypoint import Keypoint
from bimap.models.annotation import Annotation, AnnotationType
from bimap.engine.project_io import save_project, load_project, ProjectIOError


@pytest.fixture
def tmp_bimap(tmp_path) -> Path:
    return tmp_path / "test.bimap"


class TestSaveLoad:
    def test_roundtrip_empty_project(self, tmp_bimap):
        p = Project()
        save_project(p, tmp_bimap)
        p2 = load_project(tmp_bimap)
        assert str(p2.id) == str(p.id)
        assert p2.name == p.name

    def test_roundtrip_with_zone(self, tmp_bimap):
        p = Project(name="Zone Test")
        z = Zone(name="District A", zone_type=ZoneType.POLYGON,
                 coordinates=[LatLon(lat=40.4, lon=-3.7),
                               LatLon(lat=40.5, lon=-3.6)])
        p.zones.append(z)
        save_project(p, tmp_bimap)
        p2 = load_project(tmp_bimap)
        assert len(p2.zones) == 1
        assert p2.zones[0].name == "District A"
        assert len(p2.zones[0].coordinates) == 2

    def test_roundtrip_with_keypoint(self, tmp_bimap):
        p = Project()
        kp = Keypoint(lat=40.41, lon=-3.70)
        kp.info_card.title = "HQ"
        kp.keynote_number = 1
        p.keypoints.append(kp)
        save_project(p, tmp_bimap)
        p2 = load_project(tmp_bimap)
        assert p2.keypoints[0].info_card.title == "HQ"
        assert p2.keypoints[0].keynote_number == 1

    def test_roundtrip_preserves_map_state(self, tmp_bimap):
        p = Project()
        p.map_state.zoom = 15
        p.map_state.center_lat = 51.5
        p.map_state.center_lon = -0.1
        p.map_state.tile_provider = "cartodb_light"
        save_project(p, tmp_bimap)
        p2 = load_project(tmp_bimap)
        assert p2.map_state.zoom == 15
        assert abs(p2.map_state.center_lat - 51.5) < 1e-9
        assert p2.map_state.tile_provider == "cartodb_light"

    def test_file_is_valid_json(self, tmp_bimap):
        p = Project(name="JSON Test")
        save_project(p, tmp_bimap)
        data = json.loads(tmp_bimap.read_text(encoding="utf-8"))
        assert "name" in data
        assert data["name"] == "JSON Test"


class TestProjectIOErrors:
    def test_load_nonexistent_raises(self, tmp_path):
        with pytest.raises(ProjectIOError):
            load_project(tmp_path / "missing.bimap")

    def test_load_corrupted_json_raises(self, tmp_bimap):
        tmp_bimap.write_text("{ this is not json", encoding="utf-8")
        with pytest.raises(ProjectIOError):
            load_project(tmp_bimap)

    def test_save_to_bad_path_raises(self):
        p = Project()
        with pytest.raises(ProjectIOError):
            save_project(p, Path("/no_such_dir/no_such_file.bimap"))
