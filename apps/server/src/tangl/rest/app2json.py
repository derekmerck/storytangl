"""
Dump the openapi spec from a fastapi app
https://github.com/tiangolo/fastapi/issues/1490
"""

import json
from fastapi.openapi.utils import get_openapi

def get_openapi_for_app(app):
    return get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
        )


if __name__ == "__main__":
    from tangl.rest.api_server import app
    spec = get_openapi_for_app(app)

    with open('openapi.json', 'w') as f:
        json.dump( spec, f )

