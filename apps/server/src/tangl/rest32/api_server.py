"""
FastAPI api server for StoryTangl narrative engine.
"""
from fastapi import FastAPI

from tangl.info import __title__, __version__, __author__, __author_email__, __url__, __desc__
from tangl.config import settings
from tangl.rest.routers import story_router, system_router, world_router, user_router

description = f"RESTful endpoints for {__title__}"

app = FastAPI(
    title=__title__,
    description=description,
    version=__version__,
    servers=[
        {"url": settings.service.rest.api_url,
         "description": "Reference API"},
    ],
    contact={
        "name":  __author__,
        "url":   __url__,
        "email": __author_email__,
    }
)

# Create first router
app.include_router(story_router,  prefix="/story")
app.include_router(user_router,   prefix="/user")
app.include_router(world_router,  prefix="/world")
app.include_router(system_router, prefix="/system")
