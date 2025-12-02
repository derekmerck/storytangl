from __future__ import annotations

from tangl.story.fabula.asset_manager import AssetManager


class AssetCompiler:
    """Register built-in assets onto an :class:`AssetManager`."""

    def setup_defaults(self, asset_manager: AssetManager) -> None:
        if "countable" in asset_manager.countable_classes:
            return

        try:
            from tangl.story.concepts.asset import CountableAsset
        except ModuleNotFoundError:  # pragma: no cover - optional dependency
            return

        asset_manager.register_countable_class("countable", CountableAsset)
