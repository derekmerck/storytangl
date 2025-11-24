from __future__ import annotations

"""
Ephemeral parsing artifacts for story content.

``MuBlock`` instances are smaller than blocks and never persist in the graph.
They are created during rendering to translate inline content into structured
fragments with styling hints (e.g., dialog speakers or cards).
"""
from abc import ABC, abstractmethod
from typing import Any

from tangl.core import Graph, Node
from tangl.journal.content import ContentFragment


class MuBlock(Node):
    """
    MuBlock(text: str = "", label: str | None = None)

    Transient parsing artifact used to produce content fragments with optional
    styling or attribution metadata.
    """

    text: str = ""
    label: str | None = None
    style_cls: str | None = None
    style_dict: dict[str, str] | None = None

    def to_fragment(self) -> ContentFragment:
        """Convert this micro-block into a content fragment."""

        raise NotImplementedError


class MuBlockHandler(ABC):
    """Protocol for handlers that detect, parse, and render micro-blocks."""

    @classmethod
    @abstractmethod
    def has_mu_blocks(cls, text: str) -> bool:
        """Return ``True`` if ``text`` contains this handler's format."""

    @classmethod
    @abstractmethod
    def parse(cls, text: str, *, graph: Graph, **ctx: Any) -> list[MuBlock]:
        """Parse ``text`` into micro-block instances."""

    @classmethod
    def render(cls, mu_blocks: list[MuBlock]) -> list[ContentFragment]:
        """Render parsed micro-blocks into fragments."""

        return [mu_block.to_fragment() for mu_block in mu_blocks]
