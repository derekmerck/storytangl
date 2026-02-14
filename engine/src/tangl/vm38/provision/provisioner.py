from __future__ import annotations
from enum import Flag, auto
from typing import ClassVar, Callable, Protocol, Iterable, Iterator, TYPE_CHECKING
from dataclasses import dataclass

from pydantic import ConfigDict, SkipValidation

from tangl.core38 import Entity, Record, EntityTemplate, Node, Selector, resolve_ctx, Priority, TokenFactory

if TYPE_CHECKING:
    from .requirement import Requirement, Affordance


class ProvisionPolicy(Flag):
    FORCE = auto()  # for offers only, forces highest priority
    EXISTING = auto()
    UPDATE = auto()
    CREATE = auto()
    CLONE = auto()   # create + update
    ANY = EXISTING | UPDATE | CREATE  # for requirements only, not offers

    def __int__(self):
        # should be monotonic
        return self.value


class ProvisionOffer(Record):
    # todo: seems like we want to attach the accepted offer to the requirement or
    #       requirement carrier, maybe exclude the callback and serialize as just the
    #       origin, policy, priority?  Or just track the accepted-offer-id in the
    #       requirement?

    model_config = ConfigDict(arbitrary_types_allowed=True)
    # has arbitrary types, don't allow serialization
    guard_unstructure: ClassVar[bool] = True

    policy: ProvisionPolicy  # but not ANY
    callback: Callable
    priority: int = Priority.NORMAL

    def sort_key(self):
        # earliest policy, priority, seq sorts to earliest
        # a couple of knobs here:
        # - if you set an offer _policy_ to FORCE it will beat everything else
        # - if you set an offer _priority_ to EARLY, it will beat anything in
        #   that policy tier and similarly for LATE will lose to anything in that
        #   tier
        # You can inject offers manually in the resolver do_resolve_req hook
        return int(self.policy), self.priority, self.seq


class Provisioner(Protocol):

    def get_dependency_offers(self, requirement: Requirement) -> Iterable[ProvisionOffer]:
        ...

    def get_affordance_offers(self, node: Node) -> Iterable[ProvisionOffer]:
        ...


@dataclass
class FindProvisioner:

    values: SkipValidation[Iterable[Entity]]  # current graph, don't copy on create
    distance: int = 0

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        candidates = requirement.filter(self.values)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = "FindProvisioner",
                policy = ProvisionPolicy.EXISTING,
                priority = Priority.NORMAL + self.distance,
                callback = lambda *_, _c=c, **__: _c # need to freeze ref to _this_ c
            )

    def get_affordance_offers(self, node: Node) -> Iterator[ProvisionOffer]:
        from .requirement import Affordance
        candidates = Selector(has_kind=Affordance, satisfied_by=node).filter(self.values)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = "FindProvisioner",
                policy = ProvisionPolicy.EXISTING,
                priority = Priority.NORMAL + self.distance,
                callback = lambda *_, _c=c, **__: _c  # need to freeze ref to _this_ c
            )

@dataclass
class TemplateProvisioner:

    templates: SkipValidation[Iterable[EntityTemplate]]  # world's template registry
    distance: int = 0

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        candidates = requirement.filter(self.templates)
        for c in candidates:
            # can set priority from scope-distance once we have defined that
            yield ProvisionOffer(
                origin_id = "TemplateProvisioner",
                policy = ProvisionPolicy.CREATE,
                priority = Priority.NORMAL + self.distance,
                callback = c.materialize
            )

    # Not sure what affordance providers look like in template form?


class FallbackProvisioner:

    @classmethod
    def get_dependency_offers(cls, requirement: Requirement) -> Iterable[ProvisionOffer]:
        if requirement.fallback_templ is not None:
            # set priority to late b/c it's fallback
            return [ ProvisionOffer(
                origin_id=requirement.fallback_templ.get_label(),
                policy=ProvisionPolicy.CREATE,
                callback=requirement.fallback_templ.materialize,
                priority=Priority.LATE) ]
        return []

    # Can't have a fallback affordance, that's just a structure that's in scope?

class TokenProvisioner:
    # todo: This doesn't work yet b/c token factory doesn't present attribs that can be filtered by req

    token_factories: Iterable[TokenFactory]  # has all token types for this provisioner

    def get_dependency_offers(self, requirement: Requirement) -> Iterable[ProvisionOffer]:

        candidates = requirement.filter(self.token_factories)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = f"{c.get_label()}:{requirement.token_from}",
                policy = ProvisionPolicy.CREATE_TOKEN,
                callback = c.materialize(requirement.token_from),
                priority=Priority.EARLY  # tokens are considered to be cheaper than full nodes when available
            )
