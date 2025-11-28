from __future__ import annotations

from functools import lru_cache

from tangl.config import get_sys_media_dir
from tangl.media.media_resource.resource_manager import ResourceManager


@lru_cache(maxsize=1)
def get_system_resource_manager() -> ResourceManager | None:
    """Return the cached system-level :class:`ResourceManager` if configured."""

    root = get_sys_media_dir()
    if root is None:
        return None

    manager = ResourceManager(resource_path=root)
    manager.index_directory(".")
    return manager
