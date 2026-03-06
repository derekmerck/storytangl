from __future__ import annotations

from typing import Protocol


class AssetManagerProtocol(Protocol):
    countable_classes: dict[str, type]

    def register_countable_class(self, label: str, cls: type) -> None: ...


class AssetCompiler:
    """Register built-in assets onto an asset manager."""

    def setup_defaults(self, asset_manager: AssetManagerProtocol) -> None:
        if "countable" in asset_manager.countable_classes:
            return

        try:
            from tangl.story.concepts.asset import CountableAsset
        except ModuleNotFoundError:  # pragma: no cover - optional dependency
            return

        asset_manager.register_countable_class("countable", CountableAsset)
