from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class StoryMetadata(BaseModel):
    id: str
    label: str
    world_id: str
    entry_label: str | None = None
    # room for: tags, author, version, etc.


class StoryScript(BaseModel):
    """
    Engine-agnostic intermediate representation of a single playable script.
    """

    metadata: StoryMetadata

    blocks: dict[str, Any] = {}
    actors: dict[str, Any] = {}
    locations: dict[str, Any] = {}
    resources: dict[str, Any] = {}
    extra: dict[str, Any] = {}
