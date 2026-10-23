"""Loaded domain kinds for qualified constructor-form persistence witnesses."""

from __future__ import annotations

from tangl.story import Block


class Scene(Block):
    """An explicitly selected domain class, not a replacement cardinal name."""

    domain_marker: str = "custom scene"
