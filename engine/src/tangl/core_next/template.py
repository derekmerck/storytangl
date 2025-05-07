from typing import Callable

from .requirement import Providable
from .entity import Entity
from .context_builder import ContextView

class Template(Entity, Providable):
    build: Callable[[ContextView], Entity]   # author‑supplied
