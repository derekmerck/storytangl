from typing import Callable
from .base import Entity, ProvisionKey, Providable
from .context import ContextView

class Template(Entity, Providable):
    requires: set[ProvisionKey] = set()
    provides: set[ProvisionKey] = set()
    build: Callable[[ContextView], Entity]   # author‑supplied
