from __future__ import annotations
from typing import Protocol, Optional, Self

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Registry
from tangl.core.entity.entity import match_logger


class Provider(Protocol):

    def can_provide(self, **criteria) -> bool: ...
    def provision(self, *, criteria: StringMap, **kwargs) -> Entity: ...


class EntityTemplate(Entity):

    data: StringMap

    def matches(self, **criteria) -> bool:
        match_logger.debug("Matching template")
        for k, v in criteria.items():
            match_logger.debug(f"Matching for provides {k}: {v} (callable: {callable(v)})")
            vv = self.data.get(k)
            if vv is None:
                return False
            elif callable(v):
                if not v(vv):
                    match_logger.debug(f"Failed lambda {v}: {v(vv)}")
                    return False
            elif not v == vv:
                match_logger.debug(f"Failed equivalence {v}: {vv}")
                return False
        return True

    def build(self, **overrides) -> Entity:
        overrides = overrides or {}
        data = self.data.copy() | overrides.copy()
        item = Entity.structure(data=data)
        return item


class TemplateProvider(Entity):
    """Implements Provider protocol"""

    template_registry: Registry[EntityTemplate] = Field(default_factory=Registry[EntityTemplate])

    def can_provide(self, **criteria) -> bool:
        criteria = criteria or {}
        template = self.template_registry.find_one(**criteria)
        if template is None:
            return False
        return True

    def provision(self, *, criteria: StringMap, build_overrides: StringMap = None, **kwargs) -> Optional[Entity]:
        template = self.template_registry.find_one(**criteria)
        if template is None:
            return None
        build_overrides = build_overrides or {}
        return template.build(**build_overrides)

    # todo: implement as scoped provider, mixin for domain with "in_scope"
    #       req inherit from HasHandlers
    # @on_provision_requirement.register(priority=Priority.LATE, domain=Self)
    # def _provision_if_possible(self, caller: HasRequirement, *, ctx: StringMap) -> Optional[Entity]:
    #     overrides = getattr(caller, "overrides", {})
    #     if self.can_provide(**caller.req_criteria) is not None:
    #         return self.provision(overrides=overrides, **caller.criteria)
