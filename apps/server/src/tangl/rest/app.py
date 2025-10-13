"""
FastAPI_ api, media, and docs server for StoryTangl narrative engine.

_fastapi: https://https://fastapi.tiangolo.com/

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
from pathlib import Path
import logging
from uuid import UUID

from fastapi import FastAPI, APIRouter, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from tangl.config import settings
from tangl.rest.dependencies import get_orchestrator
from tangl.service import Orchestrator

logger = logging.getLogger(__name__)


# todo: this is a placeholder that creates a default user for testing
def get_user_credentials(orchestrator: Orchestrator) -> UUID:
    secret = settings.client.secret
    user = orchestrator.execute("UserController.create_user", secret=secret)
    logger.debug("Created dev user via orchestrator", extra={"user": user})
    user_id = getattr(user, "uid", None)
    if user_id is None:
        raise RuntimeError("Orchestrator failed to return a user identifier")

    persistence = getattr(orchestrator, "persistence", None)
    if persistence is not None:
        persistence.save(user)
    else:
        logger.warning("Skipping user persistence: orchestrator missing persistence manager")

    info = orchestrator.execute("UserController.get_user_info", user_id=user_id)
    logger.debug("Fetched dev user info", extra={"info": info})
    return user_id


get_user_credentials(get_orchestrator())

app = FastAPI(
    docs_url=None,
    redoc_url=None
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
    app.mount("/guide", sphinx_docs_files, name="sphinx-docs")

    @app.get("/guide")
    async def redirect_to_guide_with_slash():
        return RedirectResponse(url="/guide/")

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
