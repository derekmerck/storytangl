"""FastAPI server for StoryTangl media."""
from __future__ import annotations

from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tangl.config import settings
from tangl.info import __author__, __author_email__, __desc__, __title__, __url__, __version__
from tangl.story.fabula.world import World

logger = logging.getLogger(__name__)

description = f"Media server for {__desc__.lower()}"

DEFAULT_APP_URL = "localhost:8000"
__app_url__ = settings.get("app.url", DEFAULT_APP_URL)

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


def mount_media_for_world(world_id: str, world_path: Path) -> None:
    """Mount the ``media`` directory for ``world_id`` if it exists."""

    media_dir = world_path / "media"
    if not media_dir.exists():
        logger.info("No media directory for world %s", world_id)
        return

    try:
        media_files = StaticFiles(directory=str(media_dir))
        app.mount(f"/world/{world_id}", media_files, name=f"media-{world_id}")
        logger.info("Mounted media for %s at /media/world/%s/", world_id, world_id)
    except Exception:  # pragma: no cover - defensive logging only
        logger.warning("Failed to mount media for %s", world_id, exc_info=True)


def initialize_media_mounts() -> None:
    """Mount media directories for all loaded :class:`~tangl.story.fabula.world.World` instances."""

    for world_id, world in World._instances.items():
        source_path = getattr(world, "source_path", None)
        if source_path is None:
            continue
        mount_media_for_world(world_id, Path(source_path).parent)


initialize_media_mounts()

# Middleware translation by resource manager
# from fastapi import FastAPI, Request
# from starlette.middleware.base import BaseHTTPMiddleware
# from starlette.responses import Response
#
# class AliasMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         path = request.url.path
#         # Logic to translate alias in path
#         # Example: /world/{world_id}/abc123 -> /world/{world_id}/actual_file.png
#
#         # Modify request here if necessary...
#
#         response = await call_next(request)
#         return response
#
# # Add middleware to the app
# app.add_middleware(AliasMiddleware)
