"""
FastAPI_ api, media, and docs server for StoryTangl narrative engine.

_fastapi: https://fastapi.tiangolo.com/

```bash
$ tangl-serve
```
or

```bash
$ python -m tangl.rest
```

or

```bash
$ uvicorn tangl.rest.app:app
```

Default mounts:
- api:   `/api/v2`
- spec:  `/api/v2/openapi`
- docs:  `/docs`
- media: `/media`

"""
from contextlib import asynccontextmanager
from pathlib import Path
import logging
from uuid import UUID

from fastapi import FastAPI, APIRouter, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from tangl.config import settings
from tangl.rest.dependencies38 import get_service_gateway38
from tangl.rest.media_mounts import mount_system_media
from tangl.service import ServiceGateway38, ServiceOperation38
from tangl.service.response import RuntimeInfo

logger = logging.getLogger(__name__)


# todo: this is a placeholder that creates a default user for testing
def get_user_credentials(gateway: ServiceGateway38) -> UUID:
    secret = settings.client.secret
    result = gateway.execute(ServiceOperation38.USER_CREATE, secret=secret)

    user_id: UUID | None = None
    user_obj = None

    if isinstance(result, RuntimeInfo):
        if result.status != "ok":
            raise RuntimeError("Service gateway failed to create dev user")
        details = result.details or {}
        user_obj = details.get("user")
        raw_user_id = details.get("user_id")
        try:
            user_id = UUID(str(raw_user_id)) if raw_user_id is not None else None
        except (TypeError, ValueError):
            user_id = None
        if user_id is None and hasattr(user_obj, "uid"):
            user_id = getattr(user_obj, "uid")
    else:
        # Backward compatibility with previous create_user return type
        user_obj = result
        user_id = getattr(result, "uid", None)

    if user_id is None:
        raise RuntimeError("Service gateway failed to return a user identifier")

    logger.debug("Created dev user via service38 gateway", extra={"user_id": str(user_id)})
    return user_id


@asynccontextmanager
async def _app_lifespan(_: FastAPI):
    """Run startup initialization for service38-backed REST app."""
    try:
        get_user_credentials(get_service_gateway38())
    except Exception:
        logger.exception("Failed to initialize dev user credentials during startup")
        raise
    yield

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    lifespan=_app_lifespan,
)

DEFAULT_APP_URL = "localhost:8000"
__app_url__ = settings.get("app.url", "localhost:8000")

origins = [
    "http://localhost:5173",    # Vue dev app
    "http://127.0.0.1:5173",
    "http://localhost:8000",    # Docker container
    "http://127.0.0.1:8000",
    __app_url__,  # prod
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mount_system_media(app)

# @app.exception_handler(StoryAccessError)
# def handle_unavailable(request: Request, exc: StoryAccessError):
#     return JSONResponse(
#         {'message': "Story resources unavailable"},
#         status_code=HTTP_400_BAD_REQUEST
#     )

from tangl.rest.api_server import app as api_server
app.mount("/api/v2", api_server, name="api-server")

from tangl.rest.media_server import app as media_server
app.mount("/media", media_server, name="media-server")

docs_dir = settings.service.paths.docs  # type: Path
try:
    # This captures the case where the path is accessed without a slash,
    # which fails to route to the mount otherwise.
    sphinx_docs_files = StaticFiles(directory=docs_dir, html=True)
    app.mount("/docs", sphinx_docs_files, name="sphinx-docs")

    @app.get("/docs")
    async def redirect_to_docs_with_slash():
        return RedirectResponse(url="/docs/")

except (AssertionError, RuntimeError):
    logger.warning(f"Could not find sphinx docs at {docs_dir}")

# This _must_ be mounted last b/c it shadows the root path
client_dist_dir = settings.service.paths.client_dist  # type: Path
try:
    client_dist_files = StaticFiles(directory=client_dist_dir, html=True)
    app.mount("/", client_dist_files, name="client")
except (AssertionError, RuntimeError):
    logger.warning(f"Could not find client dist at {client_dist_dir}")

# logger.debug( app.routes )
# logger.debug( api_server.routes )
# logger.debug( media_server.routes )
