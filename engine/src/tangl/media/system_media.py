from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from tangl.config import get_sys_media_dir
from tangl.media.media_resource.resource_manager import ResourceManager


class SystemMediaContext:
    """Holds a :class:`ResourceManager` for shared system media assets."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.resource_manager = ResourceManager(resource_path=root)
        # Index all media under the root directory
        self.resource_manager.index_directory(".")


@lru_cache(maxsize=1)
def get_system_media_context() -> SystemMediaContext | None:
    """Return a singleton :class:`SystemMediaContext` if configured."""

    root = get_sys_media_dir()
    if root is None:
        return None
    return SystemMediaContext(root)


def get_system_resource_manager() -> ResourceManager | None:
    """Convenience accessor for the system-level :class:`ResourceManager`."""

    context = get_system_media_context()
    return context.resource_manager if context is not None else None
