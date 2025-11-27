from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tangl.config import get_sys_media_dir

logger = logging.getLogger(__name__)


def mount_system_media(app: FastAPI, mount_path: str = "/media/sys", *, force: bool = False) -> None:
    """Mount system-level media directory under ``/media/sys`` if available."""

    sys_dir = get_sys_media_dir()
    if sys_dir is None:
        logger.info("No system media configured; skipping /media/sys mount")
        return

    if not sys_dir.exists():
        logger.warning("System media directory %s does not exist", sys_dir)
        return

    for route in list(app.router.routes):
        if getattr(route, "path", None) == mount_path or getattr(route, "prefix", None) == mount_path:
            if not force:
                logger.info("System media already mounted at %s", mount_path)
                return
            app.router.routes.remove(route)

    app.mount(
        mount_path,
        StaticFiles(directory=str(sys_dir)),
        name="media-sys",
    )
    logger.info("Mounted system media at %s from %s", mount_path, sys_dir)
