from __future__ import annotations

"""Compatibility wrapper for the system controller."""

from tangl.system.system_controller import SystemController as _LegacySystemController

SystemController = _LegacySystemController

__all__ = ["SystemController"]
