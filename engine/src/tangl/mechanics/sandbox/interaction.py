"""Sponsored interaction declarations for sandbox concepts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from tangl.core.runtime_op import Effect, Predicate


class SandboxInteraction(BaseModel):
    """Ordinary action sponsored by a scoped sandbox concept."""

    label: str
    text: str
    target: str
    journal_text: str = ""
    activation: str | None = None
    once: bool = False
    return_to_location: bool = False
    availability: list[Predicate] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
