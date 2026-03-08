from __future__ import annotations

from typing import Any

from pydantic import Field

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
