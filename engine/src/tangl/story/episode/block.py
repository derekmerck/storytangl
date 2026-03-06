from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.vm import TraversableNode


class Block(TraversableNode):
    """Block()

    Primary interactive cursor node in a runtime story graph.

    Why
    ----
    Blocks are the units a player or consumer actually visits. They hold the
    authored narrative content together with local action, role, setting, and
    media declarations that journaling and provisioning consume.
    """

    content: str = ""
    actions: list[dict[str, Any]] = Field(default_factory=list)
    continues: list[dict[str, Any]] = Field(default_factory=list)
    redirects: list[dict[str, Any]] = Field(default_factory=list)
    roles: list[dict[str, Any]] = Field(default_factory=list)
    settings: list[dict[str, Any]] = Field(default_factory=list)
    media: list[dict[str, Any]] = Field(default_factory=list)
