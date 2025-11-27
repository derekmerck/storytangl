from __future__ import annotations

from tangl.media.dispatch import MediaTask, media_dispatch
from tangl.media.system_media import get_system_resource_manager


@media_dispatch.register(task=MediaTask.GET_SYSTEM_RESOURCE_MANAGER)
def get_sys_media_manager(caller=None, *, ctx=None, **_):
    """Default provider for the system-level :class:`ResourceManager`."""

    return get_system_resource_manager()
