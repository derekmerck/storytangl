"""Canonical system-info helpers for the manager-first service layer."""

from __future__ import annotations

import logging

import humanize

from tangl.info import __title__, __url__, __version__
from tangl.utils.app_uptime import app_uptime

from .response import RuntimeInfo, SystemInfo
from .world_registry import WorldRegistry


logger = logging.getLogger(__name__)


def get_system_info() -> SystemInfo:
    """Return service/system metadata."""

    try:
        num_worlds = len(WorldRegistry().list_worlds())
    except Exception as exc:  # pragma: no cover - defensive import boundary
        logger.exception(
            "Failed to enumerate worlds from WorldRegistry.list_worlds(): %s",
            exc,
        )
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


def reset_system(*, hard: bool = False) -> RuntimeInfo:
    """Implementation-specific system reset hook."""

    _ = hard
    return RuntimeInfo.error(
        code="NOT_IMPLEMENTED",
        message="System reset is not implemented",
    )


__all__ = ["get_system_info", "reset_system"]
