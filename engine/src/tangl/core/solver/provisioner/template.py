from __future__ import annotations
from typing import Protocol, Optional, Self

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Registry
from tangl.core.entity.entity import match_logger
from tangl.core.dispatch import HasHandlers, HandlerPriority as Priority
from .requirement import HasRequirement, on_provision_requirement

class Provider(Protocol):

    def can_provide(self, **criteria) -> bool: ...
    def provision(self, **overrides) -> Entity: ...


class EntityTemplate(Entity):

    data: StringMap

    def matches(self, **criteria) -> bool:
        for k, v in criteria.items():
            match_logger.debug(f"Matching for provides {k}: {v}")
            if not self.data.get(k, None) == v:
                return False
        return True

    def build(self, **overrides) -> Entity:
        item = self.structure(**self.data, **overrides)
        return item


class TemplateProvider(HasHandlers):
    """Implements Provider protocol"""

    template_registry: Registry[EntityTemplate] = Field(default_factory=Registry[EntityTemplate])

    def can_provide(self, **criteria) -> bool:
        template = self.template_registry.find_one(**criteria)
        if template is not None:
            return True
        return False

    def provision(self, req: HasRequirement, **criteria) -> Optional[Entity]:
        template = self.template_registry.find_one(**criteria)
        overrides = getattr(req, "overrides") or {}
        if template is not None:
            return template.build(**overrides)
        # maybe raise if it tries to provision improperly?
        return None

    # todo: implement as scoped provider, mixin for domain with "in_scope"
    # @on_provision_requirement.register(priority=Priority.LATE, domain=Self)
    # def _provision_if_possible(self, caller: HasRequirement, *, ctx: StringMap) -> Optional[Entity]:
    #     overrides = getattr(caller, "overrides", {})
    #     if self.can_provide(**caller.req_criteria) is not None:
    #         return self.provision(overrides=overrides, **caller.criteria)
