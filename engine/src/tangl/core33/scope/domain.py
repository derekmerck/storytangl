from dataclasses import dataclass, field

from ..entity import Entity
from .scope_mixin import ScopeMixin

@dataclass(kw_only=True)
class Domain(Entity, ScopeMixin):
    """Holds world-level config that must survive graph reloads."""
    ...
