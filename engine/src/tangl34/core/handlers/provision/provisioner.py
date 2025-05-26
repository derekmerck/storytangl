from __future__ import annotations
from abc import abstractmethod
from typing import TYPE_CHECKING, Optional, Self
from abc import ABC
import logging

from pydantic import Field

from .enums import ResolutionState
from ...type_hints import StringMap, UnstructuredData
from ...entity import Entity, Registry
from ..enums import ServiceKind
from ..base import Handler
from .requirement import Requirement

if TYPE_CHECKING:
    from ...structure import Graph, EdgeKind

logger = logging.getLogger(__name__)

class Provisioner(Handler, ABC):
    """
    Provisioner is a handler that can produce an entity that satisfies a Requirement,
    either through discovery or creation.

    Provisioners must implement two functions: 'satisfies_requirement(req, ctx)' and
    'get_provider(req, ctx)'.  The first is used to determine whether a requirement can
    be satisfied at all, and the second is used to find or create the entity that satisfies.

    The cursor driver's entry point is the 'resolve_all_requirements' function, which will
    attempt to extend the story resolution horizon by guaranteeing a resolution for candidate
    upcoming structure nodes.
    """

    @abstractmethod
    def satisfies_requirement(self, req: Requirement, ctx: StringMap) -> bool:
        ...

    @abstractmethod
    def get_provider(self, req: Requirement, ctx: StringMap) -> Optional[Entity]:
        ...

    @classmethod
    def resolve_requirement(cls, req: Requirement, caller, *objects, ctx: StringMap) -> bool:
        # If you want to apply caller's effects on another object/scope, provide a different context
        logger.debug(f"resolving requirement {req!r}")

        if req.is_resolved:
            return True

        # todo: prune objects to the allowed req.scope-range

        def find_provisioner(req, provisioner_cls) -> Optional[Self]:
            provider_handlers = cls.gather_handlers(ServiceKind.PROVISION, caller, *objects, obj_cls=provisioner_cls)
            for h in provider_handlers:
                if h.satisfies_requirement(req, ctx=ctx):
                    return h

        match req.obligation:
            case "find_or_create":
                prov_h = find_provisioner(req, FindProvisioner) or find_provisioner(req, BuildProvisioner)
            case "find_only":
                prov_h = find_provisioner(req, FindProvisioner)
            case "create_only":
                prov_h = find_provisioner(req, BuildProvisioner)
            case _:
                prov_h = None

        if prov_h is not None:
            prov = prov_h.get_provider(req, ctx=ctx)
            req.resolution_state = ResolutionState.RESOLVED
            req.dst_id = prov.uid

            from ...structure import Graph, EdgeKind
            g = objects[0]  # type: Graph
            g.add(prov)
            g.add_edge(prov, caller, edge_kind=EdgeKind.PROVIDES)
            # g.add_edge(prov, prov_h, edge_kind=EdgeKind.BLAME)
            # todo: this won't work as is, handlers aren't in the graph...
        else:
            req.resolution_state = ResolutionState.UNRESOLVABLE
        return True

    @classmethod
    def resolve_all_requirements(cls, caller, *objects, ctx) -> bool:
        for req in caller.requirements:  # type: Requirement
            if req.is_satisfied(ctx=ctx):
                continue
            if not cls.resolve_requirement(req, caller, *objects, ctx=ctx):
                return False
        return True


class FindProvisioner(Provisioner):
    # Search a scope for available entities that satisfy the requirement criteria
    provider_registry: Registry = Field(default_factory=Registry)  
    # this should be the graph or a scope-level node registry for this requirement criteria
    # graph should offer one of these automatically, domain can offer one for world-level assets, etc.
    
    def satisfies_requirement(self, req: Requirement, ctx: StringMap) -> bool:
        return self.get_provider(req, ctx=ctx) is not None

    def get_provider(self, req: Requirement, ctx = None):
        # todo: actually want to check satisfies req and ungated by predicate
        return self.provider_registry.find_one(**req.provider_criteria)


class BuildProvisioner(Provisioner):

    provider_features: UnstructuredData = None

    def build(self, req: Requirement, ctx: StringMap) -> Entity:
        return self.func(req, ctx)

    def satisfies_requirement(self, req: Requirement, ctx: StringMap) -> bool:
        return req.matches_provider(self.provider_features)

    def get_provider(self, req: Requirement, ctx: StringMap) -> Entity:
        template = self.find_template(req, ctx)
        return self.build(template, ctx)


class ProviderTemplate(Entity):
    data: UnstructuredData

    def satisfies_requirement(self, req: Requirement) -> bool:
        # the entity built from this template will match the required criteria
        ...


class BuildFromTemplateProvisioner(Provisioner):
    # Create a entity that will match the requirement criteria, does not
    # call build func, calls Entity.structure on template data.
    provider_templates: Registry[ProviderTemplate]

    def build(self, template: ProviderTemplate, ctx: StringMap) -> Entity:
        return self.structure(**template.data)

    def find_template(self, req: Requirement, ctx: StringMap) -> ProviderTemplate:
        # todo: actually want to check satisfies req and ungated by predicate
        return self.templates.find_one(**req.provider_criteria)

    def satisfies_requirement(self, req: Requirement, ctx: StringMap) -> bool:
        return self.find_template(req, ctx) is not None

    def get_provider(self, req: Requirement, ctx: StringMap) -> Entity:
        template = self.find_template(req, ctx)
        return self.build(template, ctx)
