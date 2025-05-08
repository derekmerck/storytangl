from typing import Callable

from ..type_hints import Context
from ..entity import Entity

class Template(Entity):
    build: Callable[[Context], Entity]   # author‑supplied
