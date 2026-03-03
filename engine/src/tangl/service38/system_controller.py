"""Service38 system controller endpoints."""

from __future__ import annotations

import logging
from typing import Any

import humanize

from tangl.info import __title__, __url__, __version__
from tangl.service.api_endpoint import HasApiEndpoints
from tangl.service.response.info_response import SystemInfo
from tangl.service.world_registry import WorldRegistry
from tangl.service38.api_endpoint import AccessLevel, ApiEndpoint38, MethodType, ResponseType
from tangl.service38.response import RuntimeInfo
from tangl.utils.app_uptime import app_uptime

logger = logging.getLogger(__name__)


class SystemController(HasApiEndpoints):
    """Service metadata and diagnostics endpoints."""

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.INFO,
        binds=(),
    )
    @staticmethod
    def get_system_info(*args: Any, **kwargs: Any) -> SystemInfo:
        _ = (args, kwargs)
        try:
            num_worlds = len(WorldRegistry().list_worlds())
        except Exception:  # pragma: no cover - defensive import boundary
            num_worlds = 0

        info = SystemInfo(
            engine=__title__,
            version=__version__,
            uptime=humanize.naturaldelta(app_uptime()),
            homepage_url=__url__,
            worlds=num_worlds,
            num_users=1,
        )
        logger.debug("system info requested: %s", info)
        return info

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.RESTRICTED,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(),
    )
    @staticmethod
    def reset_system(*args: Any, hard: bool = False, **kwargs: Any) -> RuntimeInfo:
        _ = (args, hard, kwargs)
        raise NotImplementedError


__all__ = ["SystemController"]
