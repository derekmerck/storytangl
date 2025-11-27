from __future__ import annotations

from enum import Enum

from tangl.core.behavior import BehaviorRegistry


media_dispatch = BehaviorRegistry(label="media")


class MediaTask(str, Enum):
    GET_SYSTEM_RESOURCE_MANAGER = "get_system_resource_manager"
