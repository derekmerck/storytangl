from typing import Mapping, Any
from dataclasses import dataclass, field

from .. import Service
from ..type_hints import StringMap

@dataclass(kw_only=True)
class ScopeMixin:
    # implements Scope
    locals: StringMap = field(default_factory=dict)

    def handler_layer(self, service: Service):
        return {}

    # For provides service
    def template_layer(self):
        return {}

    # For context service
    def locals_layer(self) -> StringMap:
        return self.locals

