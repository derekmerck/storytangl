"""Local mechanics asset base for wearable token types.

This is a temporary cutover-local replacement for the legacy story asset base.
"""

from __future__ import annotations

from tangl.core.singleton import InstanceInheritance


class AssetType(InstanceInheritance):
    """Base singleton type for tokenizable mechanics assets."""
