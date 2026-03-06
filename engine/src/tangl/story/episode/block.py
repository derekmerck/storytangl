from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.vm import TraversableNode


class Block(TraversableNode):
    """Primary interactive cursor node in story38."""

    content: str = ""
    actions: list[dict[str, Any]] = Field(default_factory=list)
    continues: list[dict[str, Any]] = Field(default_factory=list)
    redirects: list[dict[str, Any]] = Field(default_factory=list)
    roles: list[dict[str, Any]] = Field(default_factory=list)
    settings: list[dict[str, Any]] = Field(default_factory=list)
    media: list[dict[str, Any]] = Field(default_factory=list)
