# tangl/vm/provisioning.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from tangl.type_hints import StringMap, Identifier, UnstructuredData
from tangl.core import Node, Registry
from .requirement import Requirement, ProvisioningPolicy

@dataclass
class Provisioner:
    # Default provisioner for Dependency edges
    # todo: Provisioners need to be implemented like handlers/handler registries, so
    #       that they can be passed around in domains, I think

    requirement: Requirement
    registries: list[Registry] = field(default_factory=list)

    def _resolve_existing(self,
                          provider_id: Optional[Identifier] = None,
                          provider_criteria: Optional[StringMap] = None) -> Optional[Node]:
        """Find successor by reference and filter by criteria"""
        # todo: do we want to check that it's available in the current ns?  We don't include the ns in the sig?
        provider_criteria = provider_criteria or {}
        if provider_id is not None:
            # clobber existing if given
            provider_criteria['alias'] = provider_id
        if not provider_criteria:
            raise ValueError("Must include some provider id or criteria")
        return Registry.chain_find_one(self.requirement.graph, *self.registries, **provider_criteria)

    def _resolve_update(self,
                        provider_id: Optional[Identifier] = None,
                        provider_criteria: Optional[StringMap] = None,
                        update_template: UnstructuredData = None
                        ) -> Optional[Node]:
        """Find successor by reference and filter by criteria, update by template"""
        if update_template is None:
            raise ValueError("UPDATE must include update template")
        provider = self._resolve_existing(provider_id, provider_criteria)
        if not provider:
            return None
        provider.update(**update_template)
        return provider

    def _resolve_clone(self,
                       ref_id: Optional[Identifier] = None,
                       ref_criteria: Optional[StringMap] = None,
                       update_template: UnstructuredData = None
                       ) -> Optional[Node]:
        """Find successor by reference and filter by criteria, evolve copy by template"""
        if update_template is None:
            raise ValueError("CLONE must include update template")
        ref = self._resolve_existing(ref_id, ref_criteria)
        if not ref:
            return None
        provider = ref.evolve(**update_template)  # todo: ensure NEW uid
        return provider

    def _resolve_create(self, provider_template: UnstructuredData) -> Node:
        """Create successor from template"""
        provider = Node.structure(provider_template)
        return provider

    # todo: this is the fallback for "on_provision_media", it returns if nothing else does first
    def resolve(self) -> Optional[Node]:
        """Attempt to resolve a provider for the requirement attribs and given policy"""

        provider = None

        match self.requirement.policies:
            case ProvisioningPolicy.EXISTING:
                provider = self._resolve_existing(
                    provider_id=self.requirement.identifier,
                    provider_criteria=self.requirement.criteria,
                )
            case ProvisioningPolicy.UPDATE:
                provider = self._resolve_update(
                    provider_id=self.requirement.identifier,
                    provider_criteria=self.requirement.criteria,
                    update_template=self.requirement.template
                    )
            case ProvisioningPolicy.CLONE:
                provider = self._resolve_clone(
                    ref_id=self.requirement.identifier,
                    ref_criteria=self.requirement.criteria,
                    update_template=self.requirement.template
                    )
            case ProvisioningPolicy.CREATE:
                provider = self._resolve_create(
                    provider_template=self.requirement.template
                    )

        # todo: If the default provisioner fails, we want to search for role aliases,
        #  alternative creation mechanisms and templates in the scope/namespace;
        #  assume we searched those first and just flag it as unresolvable here in the
        #  ns-free fallback?

        if provider is None:
            self.requirement.is_unresolvable = True
        else:
            self.requirement.provider = provider

# AcceptFunc = Callable[[StringMap], Entity]
#
#
# @functools.total_ordering
# class ProvisionOffer(Entity):
#     # blame
#     provisioner_id: UUID         # blame, which provisioner generated the offer
#     requirement_id: UUID = None  # Responsive to requirement
#
#     # proposed strategy
#     strategy: ProvisioningPolicy
#
#     # conditions on accepting
#     predicate: Optional[Predicate] = None
#
#     # action to provide a receipt for a valid provider entity to link
#     _accept_func: AcceptFunc = None
#
#     # ordering
#     cost: float = 1.0
#     def __lt__(self, other) -> bool:
#         return (self.cost, self.uid) < (other.cost, self.uid)
#
#     def accept(self, ns: StringMap) -> JobReceipt:
#         # result should be an entity
#         if self._accept_func is not None:
#             result = self._accept_func(ns)
#         else:
#             result = ...
#         blame_id = (self.provider_id, self.requirement_id) if self.requirement_id else self.provider_id
#         return JobReceipt(
#             blame_id=blame_id,
#             result=result,
#         )

# class Provisioner(Entity):
#     """
#     Provisioners are special types of handler-like entities that can propose
#     graph updates.
#
#     Instead of firing automatically, they are managed by an orchestrator, which
#     queries the in-scope provisioners to solicit offers and then selects among them
#     which to accept.  Accepting one produces a job receipt with an entity attachment.
#
#     Provisioners can be queried 2 ways:
#     - without requirements, to solicit "affordance" offers
#     - with a specific requirement to solicit "dependency" offers
#
#     Provisioners may return multiple offers.  Use the strategy field and
#     tags like #strategy:x for annotations; e.g., strategy:create_new or
#     strategy:find_existing.
#
#     The Provisioner can filter offers by policy and sort by cost or
#     other considerations.
#     """
#
#     # satisfying reqs with a find is usually cheaper than satisfying reqs with a create,
#     # find searches the ns, create invokes a build func or returns a buildable template
#     _get_affordances_func: Callable[[StringMap], list[ProvisionOffer]] = None
#     _get_offers_func: Callable[[StringMap, Requirement], list[ProvisionOffer]] = None
#
#     def get_offers(self, ns: StringMap, requirement: Requirement = None) -> list[ProvisionOffer]:
#         if requirement is None and self._get_affordances_func is not None:
#             return self._get_affordances_func(ns)
#         elif requirement is not None and self._get_offers_func is not None:
#             return self._get_offers_func(ns, requirement)
#         return []

# class ProvisionManager(Handler):
#     # Orchestrator handler that assembles and selects offers based on available providers and current requirements
#
#     @classmethod
#     def run(cls, providers: Iterable[Provisioner], ns: StringMap, requirement=None, select_func=None) -> list[JobReceipt]:
#         # get offers
#         offers: list[ProvisionOffer] = []
#         for provider in providers:
#             offers.extend(provider.get_offers(ns=ns, requirement=requirement))
#
#         # select offers
#         if not offers:
#             return []
#         elif select_func is not None:
#             selected = select_func(offers)
#         else:
#             selected = sorted(offers)[:1]  # keyed by cost w total order
#
#         # accept offers
#         job_receipts: list[JobReceipt] = [o.accept(ns=ns) for o in selected]
#         return job_receipts
#
# # todo: implement get offers and get affordances for generic build/find providers
# GenericFinder = Provisioner()
# GenericBuilder = Provisioner()
#
# DEFAULT_PROVISIONERS = [GenericFinder, GenericBuilder]
