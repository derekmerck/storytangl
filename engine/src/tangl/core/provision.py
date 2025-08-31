from __future__ import annotations
from uuid import UUID
import functools
from typing import Any, Callable, Optional

from pydantic import Field

from tangl.type_hints import StringMap, Predicate
from .entity import Entity
from .handler import JobReceipt

AcceptFunc = Callable[[StringMap], Entity]

class ProvisionRequirement(Entity):
    dependency_id: UUID = None  # requirer
    criteria: StringMap = Field(default_factory=dict)  # constraints

@functools.total_ordering
class ProvisionOffer(Entity):
    # blame
    provider_id: UUID            # blame
    requirement_id: UUID = None  # Responsive to prov requirement

    # conditions on accepting
    predicate: Optional[Predicate] = None
    # action to provide a receipt for a valid entity to link
    _accept_func: AcceptFunc

    # ordering
    cost: float = 1.0
    def __lt__(self, other) -> bool:
        return (self.cost, self.uid) < (other.cost, self.uid)

    def accept(self, ns: StringMap) -> JobReceipt:
        if self._accept_func is not None:
            result = self._accept_func(ns)
        else:
            result = ...
        blame_id = (self.provider_id, self.requirement_id) if self.requirement_id else self.provider_id
        return JobReceipt(
            blame_id=blame_id,
            result=result,
        )

class Provider(Entity):
    """
    Providers are special types of handlers that can update the graph shape
    on-demand.

    Instead of firing automatically, they are managed by a Provisioner, which
    queries the in-scope providers to solicit offers and then selects among them
    which to accept.  Accepting one produces a job receipt with an entity attachment.

    Providers can be queried 2 ways:
    - without requirements, to solicit "affordance" offers
    - with a specific requirement to solicit "dependency" offers

    Providers may return multiple offers.  Use tags like #strategy:x for
    annotations; e.g., strategy:create_new or strategy:find_existing.
    The Provisioner can filter offers by policy and sort by cost or
    other considerations.
    """

    # satisfying reqs with a find is usually cheaper than satisfying reqs with a create,
    # find searches the ns, create invokes a build func or returns a buildable template
    _get_affordances_func: Callable[[StringMap], list[ProvisionOffer]] = None
    _get_offers_func: Callable[[StringMap, ProvisionRequirement], list[ProvisionOffer]] = None

    def get_offers(self, ns: StringMap, requirement: ProvisionRequirement = None) -> list[ProvisionOffer]:
        if requirement is None and self._get_affordances_func is not None:
            return self._get_affordances_func(ns)
        elif requirement is not None and self._get_offers_func is not None:
            return self._get_offers_func(ns, requirement)
        return []

class Provisioner:
    # Orchestrator handler that assembles and selects offers based on available providers and current requirements

    @classmethod
    def run(cls, providers: list[Provider], ns: StringMap, requirement=None, select_func=None) -> list[JobReceipt]:
        # get offers
        offers: list[ProvisionOffer] = []
        for provider in providers:
            offers.extend(provider.get_offers(ns=ns, requirement=requirement))

        # select offers
        if not offers:
            return []
        elif select_func is not None:
            selected = select_func(offers)
        else:
            selected = sorted(offers)[:1]  # keyed by cost w total order

        # accept offers
        job_receipts: list[JobReceipt] = [o.accept(ns=ns) for o in selected]
        return job_receipts

# todo: implement get offers and get affordances for generic build/find providers
GenericFinder = Provider()
GenericBuilder = Provider()

DEFAULT_PROVISIONERS = [GenericFinder, GenericBuilder]
