# tangl/config.py
# See 'tangl/defaults.toml' for config usage

from pprint import pprint
from pathlib import Path
import os
import re

from dynaconf import Dynaconf
from dynaconf.utils import parse_conf

package_root = Path(__file__).parent
default_settings = package_root / 'defaults.toml'

settings = Dynaconf(
    envvar_prefix="TANGL",   # set "foo=bar" with `export TANGL_FOO=bar`.
    preload=[default_settings],
    settings_files=['settings.toml', 'settings.local.toml', '.secrets.toml'],
    root_path = os.getcwd(),  # set a base path in env with ROOT_PATH_FOR_DYNACONF
)

def cast_path( value: str | Path ):
    # If a path starts with "./" and we are in a subdir, change it to "../"
    if 'tests' in os.getcwd() and str(value).startswith('.'):
        # We are in a subdir and need to resolve for it
        i = os.getcwd().find('tests')
        root_path = os.getcwd()[0:i]
        value = re.sub(r'\./', root_path + '/', value)
    return Path( value ).expanduser().resolve()

parse_conf.converters["@path"] = (
    lambda value: value.set_casting(cast_path)
    if isinstance(value, parse_conf.Lazy)
    else cast_path(value)
)

def show_settings():
    s = settings.as_dict()
    pprint( s )
