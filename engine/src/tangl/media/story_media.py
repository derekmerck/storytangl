from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID

from tangl.config import get_story_media_dir
from tangl.media.media_resource.resource_manager import ResourceManager


def get_story_resource_manager(
    story_id: str | UUID,
    *,
    create: bool = True,
) -> ResourceManager | None:
    """Return a story-scoped resource manager rooted at ``story_id``."""

    resource_path = get_story_media_dir(str(story_id))
    if resource_path is None:
        return None

    if create:
        resource_path.mkdir(parents=True, exist_ok=True)
    elif not resource_path.exists():
        return None

    manager = ResourceManager(
        resource_path=resource_path,
        scope="story",
        label=f"story_media:{story_id}",
    )
    if resource_path.exists():
        manager.index_directory(".")
    return manager


def remove_story_media(story_id: str | UUID) -> bool:
    """Delete story-scoped media for ``story_id`` when present."""

    resource_path = get_story_media_dir(str(story_id))
    if resource_path is None or not resource_path.exists():
        return False
    shutil.rmtree(resource_path)
    return True
