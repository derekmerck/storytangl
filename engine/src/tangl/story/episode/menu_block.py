from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import Field

from tangl.vm import TraversableNode

from .block import Block


class MenuBlock(Block):
    """MenuBlock()

    Lightweight runtime payload for authored dynamic menu hubs.

    Why
    ----
    Story scripts still need to preserve menu metadata during compilation even
    before the full dynamic discovery/materialization behavior is reintroduced.
    ``MenuBlock`` keeps that authored shape attached to the compiled bundle so
    later passes can interpret it without lossy round-tripping.
    """

    menu_items: dict[str, Any] | list[Any] = Field(default_factory=dict)
    within_scene: bool = True
    auto_provision: bool = True

    @staticmethod
    def _is_selector_key(key: Any) -> bool:
        if not isinstance(key, str) or not key:
            return False
        if key.startswith("has_") or key.startswith("is_"):
            return True
        return key in {"label", "predicate", "admitted_to"}

    @classmethod
    def normalize_menu_selectors(cls, value: Any) -> list[dict[str, Any]]:
        """Return authored ``menu_items`` normalized to selector dicts."""
        if isinstance(value, Mapping):
            values = [dict(value)]
        elif isinstance(value, list):
            values = [dict(item) for item in value if isinstance(item, Mapping)]
        else:
            return []

        normalized: list[dict[str, Any]] = []
        for item in values:
            selector = {
                key: item[key]
                for key in item
                if cls._is_selector_key(key)
            }
            if selector:
                normalized.append(selector)
        return normalized

    @staticmethod
    def action_text_for(provider: TraversableNode) -> str:
        """Return an authored suggestion, not the destination's label floor."""
        value = provider.locals.get("action_text")
        if isinstance(value, str) and value:
            return value
        if isinstance(provider, Block) and provider.action_name:
            return provider.action_name
        value = provider.locals.get("menu_text")
        return value if isinstance(value, str) else ""
