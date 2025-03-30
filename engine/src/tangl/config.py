from pprint import pprint
from pathlib import Path
import os
import re

from dynaconf import Dynaconf
from dynaconf.utils import parse_conf

settings = Dynaconf(
    envvar_prefix="TANGL",  # set "foo=bar" with `export TANGL_FOO=bar`.
    settings_files=['defaults.toml', 'settings.toml', 'settings.local.toml', '.secrets.toml'],
    root_path = Path(__file__).parent,
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
