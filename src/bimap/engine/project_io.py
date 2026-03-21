"""Project I/O — save and load .bimap (JSON) files."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from bimap.config import PROJECT_FILE_EXTENSION
from bimap.models.project import Project


class ProjectIOError(Exception):
    pass


def save_project(project: Project, path: Path) -> None:
    """Serialise *project* to *path* (creates/overwrites the file)."""
    if path.suffix.lower() != PROJECT_FILE_EXTENSION:
        path = path.with_suffix(PROJECT_FILE_EXTENSION)
    try:
        data = project.model_dump_json(indent=2)
        path.write_text(data, encoding="utf-8")
        project.file_path = str(path)
    except (OSError, ValueError) as exc:
        raise ProjectIOError(f"Could not save project: {exc}") from exc


def load_project(path: Path) -> Project:
    """Deserialise a .bimap file and return a Project instance."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        project = Project.model_validate(data)
        project.file_path = str(path)
        return project
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ProjectIOError(f"Could not load project: {exc}") from exc


def export_backup(project: Project, path: Path) -> None:
    """Export the project as a portable ZIP backup (.bimap.zip)."""
    json_data = project.model_dump_json(indent=2)
    stem = Path(project.file_path).stem if project.file_path else "project"
    entry_name = stem + PROJECT_FILE_EXTENSION
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(entry_name, json_data)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ProjectIOError(f"Could not write backup: {exc}") from exc


def import_backup(path: Path) -> Project:
    """Load a project from a ZIP backup or a plain .bimap file."""
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, "r") as zf:
                bimap_entries = [n for n in zf.namelist() if n.endswith(PROJECT_FILE_EXTENSION)]
                if not bimap_entries:
                    raise ProjectIOError("No .bimap file found inside the backup archive.")
                raw = zf.read(bimap_entries[0]).decode("utf-8")
        else:
            raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        project = Project.model_validate(data)
        project.file_path = ""   # not bound to a location yet
        return project
    except ProjectIOError:
        raise
    except (OSError, json.JSONDecodeError, ValueError, zipfile.BadZipFile) as exc:
        raise ProjectIOError(f"Could not import backup: {exc}") from exc
