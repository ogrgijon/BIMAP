"""Shared UI utility helpers."""

from __future__ import annotations

from typing import Any


def _set_nested_attr(obj: Any, dotted_path: str, value: Any) -> None:
    """Set a nested attribute like 'style.fill_color' on *obj*."""
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        if part == "info_card" and hasattr(obj, "info_card"):
            obj = obj.info_card
        elif part == "style" and hasattr(obj, "style"):
            obj = obj.style
        elif part == "label" and hasattr(obj, "label"):
            obj = obj.label
        elif part == "fields":
            return  # complex sub-list, skip for now
        else:
            obj = getattr(obj, part)
    setattr(obj, parts[-1], value)
