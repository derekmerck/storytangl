from __future__ import annotations
from abc import abstractmethod
from typing import Any, Optional, Callable, TYPE_CHECKING
from abc import ABC
import logging

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
    """

    def can_satisfy_requirement(self, req: Requirement) -> bool:
        # Override this for more complicated provisioning logic
        return self.get_provider(req) is not None

    @abstractmethod
    def get_provider(self, req: Requirement, ctx: StringMap):
        ...

    @classmethod
    def try_find_provisioners(cls, req, caller, *objects, ctx):
        provider_handlers = cls.gather_handlers(ServiceKind.PROVISION, *objects, obj_cls=FindProvisioner)
        for h in provider_handlers:
            if h.can_satisfy_requirement(req):
                return h.get_provider(req, ctx)

    @classmethod
    def try_build_provisioners(cls, req, caller, *objects, ctx):
        provider_handlers = cls.gather_handlers(ServiceKind.PROVISION, *objects, obj_cls=BuildProvisioner)
        for h in provider_handlers:
            if h.can_satisfy_requirement(req):
                return h.get_provider(req, ctx)

    @classmethod
    def resolve_requirement(cls, req: Requirement, caller, *objects, ctx):
        # If you want to apply caller's effects on another object/scope, provide a different context
        logger.debug(f"resolving requirement {req!r}")
        if req.obligation in ("find_only", "find_or_create"):
            if x := cls.try_find_provisioners(req, caller, *objects, ctx=ctx):
                return x
        if req.obligation in ("find_or_create", "create_only"):
            if x := cls.try_build_provisioners(req, caller, *objects, ctx=ctx):
                return x

    @classmethod
    def resolve_requirements2(cls, caller, *objects, ctx):

        graph = objects[0]  # type: Graph

        for req in caller.requirements:  # type: Requirement
            if req.is_satisfied(ctx=ctx):
                continue

            prov = None
            match req.obligation:
                case "find_or_create":
                    prov = cls.try_find_provisioners(req, *objects, ctx=ctx) or cls.try_build_provisioners(req, *objects, ctx=ctx)
                case "find_only":
                    prov = cls.try_find_provisioners(req, *objects, ctx=ctx)
                case "always_create":
                    prov = cls.try_build_provisioners(req, *objects, ctx=ctx)
                case _ if req.hard:
                    return False
            if prov:
                from ...structure import Graph, EdgeKind
                req.dst_id = prov.uid
                graph.add_edge(prov, caller, edge_kind=EdgeKind.PROVIDES)
                # should return handler as well
                # graph.add_edge(caller, h, edge_kind=EdgeKind.BLAME)
        return True

    @classmethod
    def resolve_all_requirements(cls, caller, *objects, ctx):
        for req in caller.requirements:
            cls.resolve_requirement(req, caller, *objects, ctx=ctx)


class FindProvisioner(Provisioner):
    # Search a scope for available entities that satisfy the requirement criteria

    def get_provider(self, req: Requirement, provider_registry: Registry, ctx = None):
        # todo: actually want to check satisfies req and ungated by predicate
        return provider_registry.find_one(**req.provider_criteria)


class BuildProvisioner(Provisioner):

    provider_features: UnstructuredData = None

    def build(self, req: Requirement, ctx: StringMap) -> Entity:
        return self.func(req, ctx)

    def satisfies_requirement(self, req: Requirement) -> bool:
        return req.matches_provider(self.provider_features)

    def get_provider(self, req: Requirement, ctx: StringMap) -> Entity:
        template = self.find_template(req, ctx)
        return self.build(template, ctx)


class ProviderTemplate(Entity):
    data: UnstructuredData

    def satisfies_requirement(self, req: Requirement) -> bool:
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
