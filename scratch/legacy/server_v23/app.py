"""
v2.3 Flask-based REST server.
"""
import connexion
import pathlib
import sys
from flask import Blueprint
from flask_cors import CORS

from tangl.info import __version__, __author_email__
from tangl.config import settings

api_path = f"{settings.rest.protocol}://{settings.rest.host}{settings.rest.api_path}"
client_path = f"{settings.rest.protocol}://{settings.rest.host}{settings.rest.client_path}"


def create_app():
    here = pathlib.Path(__file__).parent
    sys.path.append(str(here/"controllers"))
    app = connexion.App(__name__, specification_dir=here)
    CORS(app.app, supports_credentials=True)  # Need this for pix
    app.add_api("tangl2.oa3.yaml",
                arguments={'TANGL_VERSION': __version__,
                           'TANGL_AUTHOR_EMAIL': __author_email__,
                           'TANGL_API_BASE_PATH': settings.rest.api_path},
                pythonic_params=True)
    print(f" * Serving backend at {settings.rest.api_path}")

    if hasattr(settings.rest, "client_path"):
        blueprint = Blueprint('client',
                              __name__,
                              static_url_path=settings.rest.client_path,
                              static_folder=settings.rest.client_dist_path)
        app.app.register_blueprint(blueprint)
        print(f" * Serving client at {settings.rest.client_path} ({settings.rest.client_dist_path})")

    return app.app
