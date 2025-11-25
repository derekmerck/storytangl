from __future__ import annotations

"""
Ephemeral parsing artifacts for story content.

``MuBlock`` instances are smaller than blocks and never persist in the graph.
They are created during rendering to translate inline content into structured
fragments with styling hints (e.g., dialog speakers or cards).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from tangl.journal.content import ContentFragment


@dataclass(slots=True)
class MuBlock:
    """
    MuBlock(text: str = "", label: str | None = None)

    Transient parsing artifact used to produce content fragments with optional
    styling or attribution metadata.

    Notes
    -----
    Micro-blocks are intentionally **not** graph entities. They carry just
    enough context (e.g., ``source_id``) to annotate the resulting fragments
    without registering themselves in the persistent story graph.
    """

    text: str = ""
    label: str | None = None
    style_cls: str | None = None
    style_dict: dict[str, str] | None = None
    source_id: UUID | None = field(default=None)

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
    def parse(cls, text: str, *, source_id: UUID | None = None, **ctx: Any) -> list[MuBlock]:
        """Parse ``text`` into micro-block instances."""

    @classmethod
    def render(cls, mu_blocks: list[MuBlock]) -> list[ContentFragment]:
        """Render parsed micro-blocks into fragments."""

        return [mu_block.to_fragment() for mu_block in mu_blocks]
