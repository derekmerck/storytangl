from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tangl.ir.story_ir.scene_script_models import BlockScript
from tangl.media.media_resource.media_dependency import MediaDep

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from tangl.story.episode.block import Block
    from tangl.story.story_graph import StoryGraph


logger = logging.getLogger(__name__)


def attach_media_deps_for_block(*, graph: "StoryGraph", block: "Block", script: BlockScript) -> None:
    """Attach :class:`MediaDep` edges for media declared on ``script``."""

    if not script.media:
        return

    for media_item in script.media:
        media_name = getattr(media_item, "name", None)
        if media_name:
            MediaDep(
                graph=graph,
                source_id=block.uid,
                media_path=str(media_name),
                media_role=getattr(media_item, "media_role", None),
                caption=getattr(media_item, "text", None),
            )
            continue

        logger.debug("Skipping media entry on %s without a name", block.get_label())
