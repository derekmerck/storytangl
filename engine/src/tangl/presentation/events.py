"""Transient advisory events and command grammar for runtime surfaces."""

from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class UxEvent(BaseModel):
    """Transient client guidance carried beside a journal fragment stream."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    presentation: Literal["inline", "interrupt"] = "inline"
    replay: bool = False
    severity: Literal["info", "success", "warning", "error"] = "info"
    details: dict[str, JsonValue] = Field(default_factory=dict)


class GrammarVerb(BaseModel):
    """One visible command verb and its advisory completion frames."""

    model_config = ConfigDict(extra="forbid")

    verb: str
    aliases: list[str] = Field(default_factory=list)
    frames: list[str] | None = None


class GrammarNoun(BaseModel):
    """One visible command noun and the pieces it may denote."""

    model_config = ConfigDict(extra="forbid")

    noun: str
    aliases: list[str] = Field(default_factory=list)
    piece_ids: list[str] = Field(default_factory=list)


class GrammarHint(BaseModel):
    """Advisory command vocabulary projected from the visible turn surface."""

    model_config = ConfigDict(extra="forbid")

    verbs: list[GrammarVerb] = Field(default_factory=list)
    nouns: list[GrammarNoun] = Field(default_factory=list)
    placeholder: str | None = None
    examples: list[str] = Field(default_factory=list)


__all__ = ["GrammarHint", "GrammarNoun", "GrammarVerb", "UxEvent"]
