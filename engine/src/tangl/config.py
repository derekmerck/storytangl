"""Configuration hub built on Dynaconf.

See ``tangl/defaults.toml`` for default values and casting rules.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from pprint import pprint

from dynaconf import Dynaconf
from dynaconf.utils import parse_conf

package_root = Path(__file__).parent
default_settings = package_root / "defaults.toml"

settings = Dynaconf(
    envvar_prefix="TANGL",  # set "foo=bar" with `export TANGL_FOO=bar`.
    preload=[default_settings],
    settings_files=["settings.toml", "settings.local.toml", ".secrets.toml"],
    root_path=os.getcwd(),  # set a base path in env with ROOT_PATH_FOR_DYNACONF
)


def cast_path(value: str | Path) -> Path:
    """Normalize user-provided paths with basic test-friendly handling."""

    # If a path starts with "./" and we are in a subdir, change it to "../"
    if "tests" in os.getcwd() and str(value).startswith("."):
        # We are in a subdir and need to resolve for it
        i = os.getcwd().find("tests")
        root_path = os.getcwd()[0:i]
        value = re.sub(r"\./", root_path + "/", str(value))
    return Path(value).expanduser().resolve()


parse_conf.converters["@path"] = (
    lambda value: value.set_casting(cast_path)
    if isinstance(value, parse_conf.Lazy)
    else cast_path(value)
)


def show_settings() -> None:
    s = settings.as_dict()
    pprint(s)


# Typed convenience helpers
# -------------------------


def get_world_dirs() -> list[Path]:
    """Return configured world search paths."""

    worlds = getattr(settings.service.paths, "worlds", None) or []
    # Dynaconf should already give Paths, but be defensive.
    return [Path(p) for p in worlds]


def get_sys_media_dir() -> Path | None:
    """Optional system-level media directory for shared assets."""

    system_media = getattr(settings.service.paths, "system_media", None)
    if not system_media:
        return None
    return Path(system_media)
