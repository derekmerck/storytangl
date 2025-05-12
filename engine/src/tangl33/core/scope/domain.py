from dataclasses import dataclass, field

from ..entity import Entity
from .scope_mixin import ScopeMixin

@dataclass(kw_only=True)
class Domain(Entity, ScopeMixin):
    """Holds world-level singletons that must survive graph reloads."""

    # # For domains / global scope, expose locals as r/o globals
    # @property
    # def globals(self) -> StringMap:
    #     return self.locals    # alias, purely semantic
