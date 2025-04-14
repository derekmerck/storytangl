"""
FastAPI server for StoryTangl media.
"""
# todo: We need 2 media servers:
#   - Static media, which could be swapped for a CDN
#   - Dynamic media that is created or selected for specific stories and story-states

import logging
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tangl.info import __title__, __version__, __author__, __author_email__, __url__, __desc__
from tangl.story.world import World

description = f"Media server for {__desc__.lower()}"

app = FastAPI(
    title=f"{__title__} Media Server",
    description=description,
    version=__version__,
    servers=[
        {"url": f"{__app_url__}/media", "description": "Reference Media"},
    ],
    contact={
        "name":  __author__,
        "url":   __url__,
        "email": __author_email__,
    },
    docs_url=None,
    redoc_url=None
)
def mount_media_for( world_id ):
    media_files = StaticFiles(html=True,
                              packages=[(f'{world_id}.resources', 'media')])
    app.mount(f"/world/{world_id}", media_files, name=world_id)

for uid in World._instances:
    try:
        mount_media_for(uid)
        # logger.debug( f"mounted {'uid'}.resources media" )
    except AssertionError as e:
        logger.warning(f"Could not find resources media", exc_info=True)
        pass
    except ModuleNotFoundError as e:
        logger.warning(f"Could not find module", exc_info=True)
        # This is an error, but it's ok if it happens during testing
        pass

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
