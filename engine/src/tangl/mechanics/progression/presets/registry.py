from __future__ import annotations

from typing import Dict

from ..definition.stat_system import StatSystemDefinition

_PRESETS: Dict[str, StatSystemDefinition] = {}


def register_preset(system: StatSystemDefinition, *, name: str | None = None) -> None:
    """
    Register a stat system preset by name.

    If name is omitted, `system.name` is used.
    """
    key = (name or system.name).strip().lower()
    _PRESETS[key] = system


def get_preset(name: str) -> StatSystemDefinition:
    """
    Look up a preset by name (case-insensitive).

    Raises KeyError if not found.
    """
    key = name.strip().lower()
    return _PRESETS[key]


def all_presets() -> Dict[str, StatSystemDefinition]:
    """Return a copy of the preset registry."""
    return dict(_PRESETS)
