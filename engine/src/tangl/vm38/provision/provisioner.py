from __future__ import annotations
from enum import Flag, auto
from typing import ClassVar, Callable, Protocol, Iterable, Iterator, TYPE_CHECKING
from dataclasses import dataclass

from pydantic import ConfigDict, SkipValidation

from tangl.core38 import Entity, Record, EntityTemplate, Node, Selector, resolve_ctx

if TYPE_CHECKING:
    from .requirement import Requirement, Affordance


class ProvisionPolicy(Flag):
    EXISTING = auto()
    UPDATE = auto()
    CREATE = auto()
    CLONE = auto()   # create + update
    ANY = EXISTING | UPDATE | CREATE


class ProvisionOffer(Record):

    model_config = ConfigDict(arbitrary_types_allowed=True)
    # has arbitrary types, don't allow serialization
    guard_unstructure: ClassVar[bool] = True

    policy: ProvisionPolicy
    callback: Callable

# todo: do we want ctx/dispatch hooks for specific get offers, top level aggregator, ignore?

class Provisioner(Protocol):

    def get_dependency_offers(self, requirement: Requirement) -> Iterable[ProvisionOffer]:
        ...

    def get_affordance_offers(self, node: Node):
        ...


@dataclass
class FindProvisioner:

    values: SkipValidation[Iterable[Entity]]  # current graph

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        candidates = requirement.filter(self.values)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = "FindProvisioner",
                policy = ProvisionPolicy.EXISTING,
                callback = lambda *_, **__: c
            )

    def get_affordance_offers(self, node: Node) -> Iterator[ProvisionOffer]:
        from .requirement import Affordance
        candidates = Selector(has_kind=Affordance, satisfied_by=node).filter(self.values)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = "FindProvisioner",
                policy = ProvisionPolicy.EXISTING,
                callback = lambda *_, **__: c
            )

@dataclass
class TemplateProvisioner:

    templates: SkipValidation[Iterable[EntityTemplate]]  # world's template registry

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        candidates = requirement.filter(self.templates)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = "TemplateProvisioner",
                policy = ProvisionPolicy.CREATE,
                callback = c.materialize
            )

    # Not sure what affordance providers look like in template form?


class FallbackProvisioner:

    @classmethod
    def get_dependency_offers(cls, requirement: Requirement) -> Iterable[ProvisionOffer]:
        return requirement.get_fallback_offer()

    # Can't have a fallback affordance, that's just a structure that's in scope?
