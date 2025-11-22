"""
Dump the openapi spec from a fastapi app
https://github.com/tiangolo/fastapi/issues/1490
"""

from pathlib import Path
import json

from fastapi.openapi.utils import get_openapi

project_root = Path(__file__).parent.parent
EXTRAS_DIR = project_root / "extras/api"

def get_openapi_for_app(app):
    return get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
        )


if __name__ == "__main__":

    if not EXTRAS_DIR.is_dir():
        EXTRAS_DIR.mkdir(exist_ok=True)

    from tangl.rest.api_server import app
    spec = get_openapi_for_app(app)

    with open(EXTRAS_DIR / 'openapi.json', 'w') as f:
        json.dump( spec, f )

