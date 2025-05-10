from dataclasses import dataclass, field

from ..entity import Entity
from .scope_mixin import ScopeMixin

@dataclass(kw_only=True)
class Domain(Entity, ScopeMixin):
    """Holds world-level singletons that must survive graph reloads."""
    templates: dict = field(default_factory=dict)
    # todo: type hint self.templates properly?

    def get_templates(self) -> dict:
        return self.templates
