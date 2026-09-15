"""A still's pointer to one of its sprite sheets, carried with the still itself."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from tangl.presentation.sprite_sheet import SpriteSheetManifest


class SpriteSheetRef(BaseModel):
    """Where a sheet's bytes are, what identifies them, and what its frames are.

    Why it rides on the still
    -------------------------
    A story does not keep a live handle on its world's media inventory: when a
    block's media is provisioned, the still's record is copied into the story
    graph and bound there. A sheet found later by searching the inventory would
    be found in a quick test and missing in every saved-and-reloaded session. So
    indexing attaches each sheet to its still once, and the reference travels
    wherever the still does -- into the graph, through persistence, onto the wire.

    A plain value rather than a nested inventory record, so a graph snapshot
    carries data and never a second registry-bound entity.
    """

    model_config = ConfigDict(frozen=True)

    path: Path
    rit_id: UUID
    """The sheet's own record id at indexing time, used as its payload identity."""

    content_hash: str
    """Hex digest of the sheet's bytes: the identity that survives re-indexing."""

    manifest: SpriteSheetManifest


__all__ = ["SpriteSheetRef"]
