"""
Command-line interactive user interface for interacting with
the StoryTangl narrative engine.

`tangl-cli` is built on `cmd2`, a fully-featured interactive shell
application framework for Python.  See the `cmd2` docs for a
discussion of the various features, such as command history and
scripting.

Tangl uses `dynaconf` for configuration and can be configured
through `TANGL_CLIENT` prefix environment variables or with a
``settings.toml`` file.

Set the user secret and default world.
``TANGL_CLIENT_SECRET=romAnt1c H0p3``
``TANGL_CLIENT_WORLD=my_world``

Connect to a remote api service:
``TANGL_SERVICE_REMOTE_API=https://www.afreet.city/api/v2``

If no ``REMOTE_API`` is set, the app will instantiate a local game
service and try to load any local worlds it can find on the `worlds`
path.

Set worlds path:
``TANGL_SERVICE_PATHS_WORLDS='[ @path ./worlds ]'``

By default, the cli local service runs with an ephemeral,
in-memory-only storage.  However, you can also specify a
persistent storage backend.

``TANGL_SERVICE_PERSISTENCE=pickle``
``TANGL_SERVICE_PATHS_USER__DATA='@path ./data/user'``

It is also possible to specify any of several other storage backend
adapters (`shelf`, `redis`, `mongodb`), but they are more useful for
supporting multiple users and non-file-based storage.

See the ``tangl`` package docs for full specs of all api service
configuration settings.
"""
import importlib
import logging
from typing import Any

import cmd2
import pydantic

from tangl.info import __version__
# from tangl.utils.response_models import BaseResponse

# Don't delete this import, it registers the command sets
from tangl.cli.controllers import *
from tangl.cli.app_service_manager import user_id

banner = f"t4⅁gL-cl1 v{__version__}"

class TanglShell(cmd2.Cmd):
    prompt = '⅁$ '

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.poutput(f"Set user to {user_id}")

        # shortcuts = dict(cmd2.DEFAULT_SHORTCUTS)
        # shortcuts.update({'ss': 'story', 'aa': 'action'})
        # cmd2.Cmd.__init__(self, shortcuts=shortcuts)


app = TanglShell()
