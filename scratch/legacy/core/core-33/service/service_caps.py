from __future__ import annotations
from typing import TypeVar, Generic, Protocol, TYPE_CHECKING, Iterable, Any, Type

from ..type_hints import Predicate, StringMap
from ..enums import CoreService

if TYPE_CHECKING:
    from ..capability import Capability
    from ..entity import Entity
    from ..graph import Node

ServiceT = TypeVar("ServiceT", bound=CoreService)

# Services provide capabilities at scopes:
# - context layers
# - template layers
# - build resources (find or create nodes)
# - link paths
# - gate resources
# - render fragments
# - state mutation

class CapabilityP(Protocol):
    service: CoreService          # Sets return type of apply
    priority: int = 0
    caller_criteria: StringMap    # Calling Entity must match this to offer
    caller_predicate: Predicate   # Calling Entity ctx must satisfy this to offer
    # Do we need to pass the entire scope?  Node isn't much good without its graph.
    # How would you update a domain.local with an effect?
    def satisfied_by_caller(self, caller: Entity, *, ctx: StringMap, **kwargs) -> bool: ...
    def apply(self, caller: Entity, *, ctx: StringMap, **kwargs) -> Any: ...

class TemplateBuilderP(CapabilityP):
    def can_satisfy_req(self, wants_criteria, wants_predicate, tplx: dict[str, TemplateP]) -> TemplateP: ...
    def build(self, tpl: TemplateP, node, graph, ctx) -> Node: ...

class TemplateP(Protocol):
    # a template is an indirect provider capability, it can _create_ a provider to satisfy a req
    features: StringMap   # features that can satisfy the wants criteria, role, name, type, etc.
    obj_cls: Type[Node]
    data: StringMap

# Templates may be provided by scoped capabilities
# Templates may be built by a scoped builder capability (global at least)

class RequirementP(Protocol):
    wants_criteria: StringMap   # Provided Entity must match this
    wants_predicate: Predicate  # Provided Entity ctx must satisfy this
    # Do we need to pass the entire scope?  Node isn't much good without its graph.
    # How would you update a domain.local with an effect?
    def satisfied_by_provider(self, obj):
        ...
    def find_one(self, caller: ScopeP, *, ctx: StringMap, **kwargs) -> Node | None:
        # Look through scopes to find one, should be able to _limit_ the scopes (must be within domain)
        for obj in ctx:
            if self.satisifed_by_provider(obj):
                return obj
        # Maybe we want a find service that uses the same api -- if the finder can satisfy this req, return the result
    def create_one(self, caller: ScopeP, *, tplx: StringMap, ctx: StringMap, **kwargs) -> Node | None:
        # Look through scopes and invoke indirect provider service(s)?
        for cap in service_caps[PROVISION]:
            if tpl := cap.can_satisfy_req(self.wants_criteria, self.wants_predicate, tplx, ctx, **kwargs):
                return cap.build(tpl, ctx, **kwargs)


# IsScope or HasCapabilities
class ScopeP(Protocol):
    def register_cap(self, cap: Capability) -> None:
        # This might bind the capability to the scope?
        ...
    def unregister_cap(self, cap: Capability) -> None:
        ...
    def get_service_caps(self, service: CoreService) -> Iterable[Capability]:
        ...

class ServiceCaps(Generic[ServiceT]):
    ...

    # we don't _care_ what the levels are named, do we?
    # we want all providers at all scopes that match predicate
    # they should be _returned_ ordered by scope

    # each _scoped_layer_ is a list
    # we want to iterate over _all_ of them in layer, priority order
    # we want to filter caps with satisfied predicates

    # this is not a chain map, it's a tiered chain _list_, 1 chain list per service
    # they are independent tho, so no need to combine I think.
    # Or build them all at once, then build ctx from it, then do each phase with handlers.for_service() and ctx. If we need to provision, can build tplx maps

    # ctx view and template view are tiered chainmaps, 1 per namespace (ctx, provider templates)
    # local templates should take precedence over farther scopes

    # propose tier no longer matters, just the order of adding things

    # This is just a view of _all_ services that are available from this caller's perspective
    # Get only the relevant ones with "satisfied_by_caller(service, caller)", which returns an ordered
    # list of caps at all scopes to iterate over.

    @classmethod
    def from_scopes(cls, service: CoreService, *scopes: ScopeP) -> Self:
        # scopes = node, graph, user, domain, global etc.
        # ---------------------------------------------------------
        maps = (s.service_handlers(service) for s in scopes)
        return ChainMap(*maps)

    # ScopeP only knows how to return "service_handlers(service) -> list[Capability]"

    def __iter__(self) -> Iterable[Capability]:
        ...

    @classmethod
    def satisfied_by_caller(cls, service: Service, caller: Node, ctx: StringMap):
        # return a list of all caps for this service that _should_ fire for this caller
        ...

