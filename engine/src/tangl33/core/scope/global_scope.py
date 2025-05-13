from typing import ClassVar, Self
from dataclasses import dataclass

from tangl33.utils.singleton import Singleton
from ..entity import Entity
from .scope_mixin import ScopeMixin

@dataclass(kw_only=True)
class GlobalScope(Singleton, ScopeMixin, Entity):
    """Holds system-wide config that must survive graph reloads."""
    ...
