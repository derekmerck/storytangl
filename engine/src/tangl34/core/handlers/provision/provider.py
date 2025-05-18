from abc import abstractmethod
from typing import Any, Optional

from ...type_hints import Context
from ...entity import Entity, Registry
from ..enums import ServiceKind
from ..handler import Handler
from ..gather import gather_handlers
from .requirement import Requirement

class Provider(Handler):

    @abstractmethod
    def satisfies_requirement(self, req: Requirement) -> bool:
        ...

    @abstractmethod
    def get_provider(self, req: Requirement, ctx: Context):
        ...

class FindProvider(Registry[Entity]):
    # Search a scope for matching entities

    # todo: actually want to check satisfies req and ungated by predicate
    def satisfies_requirement(self, req: Requirement) -> bool:
        return self.get_provider(req) is not None

    def get_provider(self, req: Requirement, ctx = None):
        return self.find_one(**req.provider_criteria)

class ResourceBuilder(Entity):
    # templates
    data: dict[str, Any]

    def satisfies_requirement(self, req: Requirement) -> bool:
        ...

    @abstractmethod
    def build(self, ctx: Context) -> Entity:
        return self.structure(**self.data)

def try_find_provider(req: Requirement, *scopes, ctx: Context) -> Optional[Provider]:
    provider_handlers = gather_handlers(ServiceKind.PROVISION, *scopes, obj_cls=FindProvider)
    for h in provider_handlers:
        if h.satisfies_requirement(req):
            return h.get_provider(req, ctx)


class CreateProvider(Registry[ResourceBuilder]):
    # Search a scope for matching builders

    def _find_builder(self, req: Requirement) -> Optional[ResourceBuilder]:
        return self.find_one(**req.provider_criteria)

    def satisfies_requirement(self, req: Requirement) -> bool:
        return self._find_builder(req) is not None

    def get_provider(self, req: Requirement, ctx: Context) -> Entity:
        builder = self._find_builder(req)
        return builder.build(ctx)

def try_create_provider(req: Requirement, *scopes, ctx: Context) -> Optional[Provider]:
    provider_handlers = gather_handlers(ServiceKind.PROVISION, *scopes, obj_cls=CreateProvider)
    for h in provider_handlers:
        if h.satisfies_requirement(req):
            return h.get_provider(req, ctx)

# class Provision(Link):
#     # Link that is assigned to a concept req once it is satisfied
#     # It is always added to the recruiter's context by the req name
#     req: Requirement
#
# class Path(Provision):
#     # Link that is assigned to a structure req once it is satisfied
#     # It is always added to the requirement's transition table by the req name
#     req: StructureRequirement
#     @property
#     def phase(self) -> Optional[Literal["before", "after"]]:
#         return self.req.phase
#
# class Provider(Entity):
#     # ProvisionFinder takes a _graph_ and finds a matching node/entity/link within scope
#     def provides_match(self, **criteria: Any) -> bool:
#         return self._find_match(**criteria) is not None
#     def get_match(self, **criteria: Any) -> Provider: ...
#
# class FindProvider(Provider):
#     # Find provider within scope-range
#     def _find_match(self, scopes, **criteria: Any) -> Provider: ...
#     def get_match(self, scopes, **criteria: Any) -> Provider:
#         return self._find_match(**criteria)
#
# class IndirectProvider(Provider):
#     # Find template within registry
#     templates: EntityRegistry[Provider]
#
#     def _find_match(self, **criteria: Any) -> Provider:
#         return next(*self.templates.find(**criteria))
#
#     def get_match(self, **criteria: Any) -> Provider:
#         template = self._find_template(**criteria)
#         return template.build(**criteria)
#
