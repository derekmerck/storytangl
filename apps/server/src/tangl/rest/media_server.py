"""FastAPI sub-application for serving world media assets."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tangl.config import settings
from tangl.info import __author__, __author_email__, __desc__, __title__, __url__, __version__
from tangl.rest.media_mounts import mount_system_media
from tangl.service.world_registry import WorldRegistry

logger = logging.getLogger(__name__)

description = f"Media server for {__desc__.lower()}"

__app_url__ = settings.get("app.url", "localhost:8000")

app = FastAPI(
    title=f"{__title__} Media Server",
    description=description,
    version=__version__,
    servers=[
        {"url": f"{__app_url__}/media", "description": "Reference Media"},
    ],
    contact={
        "name": __author__,
        "url": __url__,
        "email": __author_email__,
    },
    docs_url=None,
    redoc_url=None,
)


def mount_world_media(app: FastAPI, world_id: str, media_dir: Path) -> None:
    """Mount static files for a world's media directory."""

    if not media_dir.exists():
        logger.warning("Media directory %s does not exist", media_dir)
        return

    mount_path = f"/world/{world_id}"
    for route in app.router.routes:
        if getattr(route, "path", None) == mount_path or getattr(route, "prefix", None) == mount_path:
            logger.info("Media already mounted for world '%s'", world_id)
            return

    app.mount(
        mount_path,
        StaticFiles(directory=str(media_dir)),
        name=f"media-world-{world_id}",
    )
    logger.info("Mounted media for world '%s' at /media/world/%s", world_id, world_id)

def initialize_media_mounts(app: FastAPI, world_registry: WorldRegistry) -> None:
    """Mount media directories for all discovered worlds at startup."""

    for world_id, bundle in world_registry.bundles.items():
        mount_world_media(app, world_id, bundle.media_dir)


mount_system_media(app, mount_path="/sys")
