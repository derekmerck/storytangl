"""Narrator-facing epistemic bookkeeping for story concept carriers.

This module keeps narrator knowledge in the story-domain layer as explicit,
typed annotation state on the concepts it is knowledge of. The live render
environment remains ephemeral; only the per-concept bookkeeping persists with
the graph.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import Field

from tangl.utils.base_model_plus import BaseModelPlus

__all__ = ["EntityKnowledge", "HasNarratorKnowledge", "get_narrator_key"]


class EntityKnowledge(BaseModelPlus):
    """EntityKnowledge()

    Flat epistemic bookkeeping annotation for one narrator and one concept.

    Why
    ---
    ``EntityKnowledge`` is intentionally small and diff-friendly. It stores the
    state a narrator has reached for a specific concept without introducing a
    separate session registry or graph-shadow lookup layer.

    Key Features
    ------------
    - Uses simple string states for replay-friendly constructor-form storage.
    - Captures the first anonymous description and crystallized handle when a
      concept is encountered before formal identification.
    - Stores only bookkeeping fields; narrative policy stays in render/filter
      code that reads and mutates this model.
    """

    state: str = "UNKNOWN"
    nominal_handle: str | None = None
    first_description: str | None = None
    identification_source: str | None = None


def get_narrator_key(ctx: Any = None, *, default: str = "_") -> str:
    """Return the active narrator key from context metadata.

    The first runtime pass keeps narrator selection intentionally simple:
    ``ctx.get_meta()["narrator_key"]`` when available, otherwise ``"_"``.
    """

    meta: Mapping[str, Any] | None = None
    get_meta = getattr(ctx, "get_meta", None)
    if callable(get_meta):
        value = get_meta()
        if isinstance(value, Mapping):
            meta = value
    elif isinstance(getattr(ctx, "meta", None), Mapping):
        meta = getattr(ctx, "meta")

    narrator_key = meta.get("narrator_key") if meta is not None else None
    if isinstance(narrator_key, str) and narrator_key:
        return narrator_key
    return default


class HasNarratorKnowledge:
    """Mixin adding narrator-facing knowledge state to a story concept."""

    narrator_knowledge: dict[str, EntityKnowledge] = Field(default_factory=dict)

    def get_knowledge(self, key: str = "_") -> EntityKnowledge:
        """Return narrator-specific knowledge, creating the default record lazily."""
        narrator_key = str(key or "_")
        if not isinstance(self.narrator_knowledge, dict):
            self.narrator_knowledge = {}

        knowledge = self.narrator_knowledge.get(narrator_key)
        if not isinstance(knowledge, EntityKnowledge):
            updated = dict(self.narrator_knowledge)
            updated[narrator_key] = EntityKnowledge()
            self.narrator_knowledge = updated
            knowledge = self.narrator_knowledge[narrator_key]
        return knowledge
