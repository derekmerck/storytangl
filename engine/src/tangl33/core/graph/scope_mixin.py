from typing import Mapping, Any
from dataclasses import dataclass, field

from ..type_hints import StringMap

@dataclass(kw_only=True)
class ScopeMixin:
    # implements Scope
    locals: StringMap = field(default_factory=dict)

    def handler_layer(self):
        return {}

    def template_layer(self):
        return {}

    def local_layer(self, service) -> StringMap:
        return self.locals

