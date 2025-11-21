"""
FastAPI api server for StoryTangl narrative engine.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from tangl.info import __title__, __version__, __author__, __author_email__, __url__, __desc__
from tangl.config import settings
from tangl.rest.routers import story_router, system_router, world_router, user_router
from tangl.service.exceptions import (
    AccessDeniedError,
    NoActiveStoryError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)

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


def _status_for_service_error(exc: ServiceError) -> int:
    if isinstance(exc, AccessDeniedError):
        return status.HTTP_403_FORBIDDEN
    if isinstance(exc, ResourceNotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(exc, ValidationError):
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    if isinstance(exc, NoActiveStoryError):
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_400_BAD_REQUEST


@app.exception_handler(ServiceError)
async def handle_service_error(request: Request, exc: ServiceError):  # pragma: no cover - FastAPI wiring
    status_code = _status_for_service_error(exc)
    payload = {"detail": str(exc), "code": getattr(exc, "code", "SERVICE_ERROR")}
    return JSONResponse(status_code=status_code, content=payload)

# Create api routers
app.include_router(story_router,  prefix="/story")
app.include_router(user_router,   prefix="/user")
app.include_router(world_router,  prefix="/world")
app.include_router(system_router, prefix="/system")
