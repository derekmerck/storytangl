from __future__ import annotations

"""Compatibility wrapper for the legacy world controller."""

from tangl.story.story_domain.world_controller import WorldController as _LegacyWorldController

WorldController = _LegacyWorldController

__all__ = ["WorldController"]
