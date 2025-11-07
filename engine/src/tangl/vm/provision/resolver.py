"""Pure provisioning helpers used by the planning pipeline."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from random import Random
from typing import Iterable
from uuid import UUID

from tangl.core import Graph, Node

from .offer import (
    AffordanceOffer,
    BuildReceipt,
    DependencyOffer,
    ProvisionOffer,
)
from .open_edge import Affordance, Dependency
from .provisioner import Provisioner
from .requirement import ProvisioningPolicy


@dataclass(slots=True)
class ProvisioningContext:
    """VM-independent execution context for provisioning."""

    graph: Graph
    step: int
    rng_seed: int | None = None

    _rand: Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        seed = self.rng_seed if self.rng_seed is not None else self.step
        self._rand = Random(seed)

    @property
    def rand(self) -> Random:
        """Return a deterministic random generator for provisioners."""

        return self._rand


@dataclass
class ProvisioningResult:
    """Result of provisioning a single structural node."""

    node: Node
    builds: list[BuildReceipt] = field(default_factory=list)
    dependency_offers: dict[UUID, list[DependencyOffer]] = field(default_factory=dict)
    affordance_offers: list[AffordanceOffer] = field(default_factory=list)

    @property
    def is_viable(self) -> bool:
        """True when all hard requirements targeting the node are satisfied."""

        for dependency in Dependency.get_dependencies(self.node):
            requirement = dependency.requirement
            if requirement.hard_requirement and requirement.provider is None:
                return False
        for affordance in self.node.edges_in(is_instance=Affordance):
            requirement = affordance.requirement
            if requirement is None:
                continue
            if requirement.hard_requirement and requirement.provider is None:
                return False
        return True


def _attach_offer_metadata(
    offer: ProvisionOffer,
    provisioner: Provisioner,
    proximity: int,
    *,
    source: str,
) -> ProvisionOffer:
    """Populate offer metadata used during arbitration."""

    if offer.source_provisioner_id is None:
        offer.source_provisioner_id = provisioner.uid
    if offer.source_layer is None:
        offer.source_layer = getattr(provisioner, "layer", None)
    offer.proximity = min(getattr(offer, "proximity", proximity), proximity)
    if not hasattr(offer, "selection_criteria") or offer.selection_criteria is None:
        offer.selection_criteria = {}
    offer.selection_criteria.setdefault("source", source)
    return offer


def _policy_from_offer(offer: DependencyOffer) -> ProvisioningPolicy:
    """Return the provisioning policy represented by *offer*."""

    if isinstance(offer.operation, ProvisioningPolicy):
        return offer.operation
    try:
        return ProvisioningPolicy[str(offer.operation)]
    except KeyError:
        return ProvisioningPolicy.NOOP


def _deduplicate_offers(offers: list[ProvisionOffer]) -> list[ProvisionOffer]:
    """Deduplicate EXISTING offers by provider identifier."""

    existing_by_provider: dict[UUID, list[tuple[int, ProvisionOffer]]] = defaultdict(list)
    non_existing: list[tuple[int, ProvisionOffer]] = []

    for idx, offer in enumerate(offers):
        if (
            isinstance(offer, DependencyOffer)
            and _policy_from_offer(offer) is ProvisioningPolicy.EXISTING
            and offer.provider_id is not None
        ):
            existing_by_provider[offer.provider_id].append((idx, offer))
        else:
            non_existing.append((idx, offer))

    deduplicated: list[tuple[int, ProvisionOffer]] = []
    for provider_offers in existing_by_provider.values():
        best = min(
            provider_offers,
            key=lambda item: (
                item[1].cost,
                item[1].proximity,
                item[0],
            ),
        )
        deduplicated.append(best)

    deduplicated.extend(non_existing)
    deduplicated.sort(key=lambda item: (item[1].cost, item[1].proximity, item[0]))
    return [offer for _, offer in deduplicated]


def _select_best_offer(offers: Iterable[ProvisionOffer]) -> ProvisionOffer | None:
    """Select the most desirable offer from *offers*."""

    enumerated = list(enumerate(offers))
    if not enumerated:
        return None
    _, offer = min(
        enumerated,
        key=lambda item: (
            item[1].cost,
            item[1].proximity,
            item[0],
        ),
    )
    return offer


def provision_node(
    node: Node,
    provisioners: list[Provisioner],
    *,
    ctx: ProvisioningContext,
) -> ProvisioningResult:
    """Provision ``node`` using *provisioners* and return a result summary."""

    if node is None:
        raise ValueError("node must be provided for provisioning")
    if not provisioners:
        raise ValueError("provisioners must not be empty")

    result = ProvisioningResult(node=node)

    indexed_provisioners = list(enumerate(provisioners))
    dependencies = [
        dep
        for dep in Dependency.get_dependencies(node)
        if dep.requirement.provider is None
    ]
    dependency_by_requirement: dict[UUID, Dependency] = {
        dep.requirement.uid: dep for dep in dependencies
    }

    inbound_affordances = [
        affordance
        for affordance in node.edges_in(is_instance=Affordance)
        if affordance.requirement is not None
    ]
    affordance_by_requirement: dict[UUID, Affordance] = {
        aff.requirement.uid: aff for aff in inbound_affordances if aff.requirement is not None
    }

    offer_map: dict[UUID, list[DependencyOffer]] = defaultdict(list)

    for proximity, provisioner in indexed_provisioners:
        for offer in provisioner.get_affordance_offers(node, ctx=ctx):
            result.affordance_offers.append(
                _attach_offer_metadata(offer, provisioner, proximity, source="affordance")
            )

    for requirement_id, dep in dependency_by_requirement.items():
        offer_map.setdefault(requirement_id, [])
        for proximity, provisioner in indexed_provisioners:
            try:
                offers_iter = provisioner.get_dependency_offers(dep.requirement, ctx=ctx)
            except NotImplementedError:
                continue
            for offer in offers_iter:
                offer_map[requirement_id].append(
                    _attach_offer_metadata(offer, provisioner, proximity, source="dependency")
                )

    for requirement_id, affordance in affordance_by_requirement.items():
        requirement = affordance.requirement
        if requirement.provider is not None:
            continue
        offer_map.setdefault(requirement_id, [])
        for proximity, provisioner in indexed_provisioners:
            try:
                offers_iter = provisioner.get_dependency_offers(requirement, ctx=ctx)
            except NotImplementedError:
                continue
            for offer in offers_iter:
                offer_map[requirement_id].append(
                    _attach_offer_metadata(offer, provisioner, proximity, source="affordance")
                )

    deduplicated_map: dict[UUID, list[DependencyOffer]] = {}
    for requirement_id, offers in offer_map.items():
        deduplicated_map[requirement_id] = [
            offer for offer in _deduplicate_offers(list(offers)) if isinstance(offer, DependencyOffer)
        ]

    result.dependency_offers.update(deduplicated_map)

    used_affordance_labels: dict[UUID, set[str]] = defaultdict(set)

    for offer in result.affordance_offers:
        if not isinstance(offer, AffordanceOffer):
            continue
        label = offer.get_label()
        if label is not None and label in used_affordance_labels[node.uid]:
            continue
        if not offer.available_for(node):
            continue
        try:
            affordance_edge = offer.accept(ctx=ctx, destination=node)
            provider = affordance_edge.source if affordance_edge else None
            requirement = affordance_edge.requirement if affordance_edge else None
            if label is not None:
                used_affordance_labels[node.uid].add(label)
            if provider is not None:
                for dep in dependencies:
                    if dep.requirement.provider is not None:
                        continue
                    if dep.satisfied_by(provider):
                        dep.destination = provider
            if requirement is not None and requirement.provider is None and provider is not None:
                requirement.provider = provider
            build = BuildReceipt(
                provisioner_id=offer.source_provisioner_id or offer.uid,
                requirement_id=(requirement.uid if requirement is not None else UUID(int=0)),
                provider_id=(provider.uid if provider is not None else None),
                operation=ProvisioningPolicy.EXISTING,
                accepted=True,
                hard_req=False,
            )
            result.builds.append(build)
        except Exception as exc:  # pragma: no cover - defensive
            build = BuildReceipt(
                provisioner_id=offer.source_provisioner_id or offer.uid,
                requirement_id=UUID(int=0),
                provider_id=None,
                operation=ProvisioningPolicy.NOOP,
                accepted=False,
                hard_req=False,
                reason=str(exc),
            )
            result.builds.append(build)

    for requirement_id, offers in deduplicated_map.items():
        if requirement_id in dependency_by_requirement:
            dependency = dependency_by_requirement[requirement_id]
            requirement = dependency.requirement
        else:
            affordance = affordance_by_requirement.get(requirement_id)
            if affordance is None:
                continue
            requirement = affordance.requirement
            dependency = None
        if requirement.provider is not None:
            continue
        best_offer = _select_best_offer(offers)
        if best_offer is None:
            if requirement.hard_requirement:
                result.builds.append(
                    BuildReceipt(
                        provisioner_id=UUID(int=0),
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=True,
                        reason="No offers available",
                    )
                )
            continue
        try:
            provider = best_offer.accept(ctx=ctx)
            if provider is None:
                raise ValueError("Offer accepted without provider")
            requirement.provider = provider
            if dependency is not None:
                dependency.destination = provider
            elif requirement.uid in affordance_by_requirement:
                affordance_by_requirement[requirement.uid].requirement.provider = provider
            result.builds.append(
                BuildReceipt(
                    provisioner_id=best_offer.source_provisioner_id or best_offer.uid,
                    requirement_id=requirement.uid,
                    provider_id=provider.uid,
                    operation=_policy_from_offer(best_offer),
                    accepted=True,
                    hard_req=requirement.hard_requirement,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            result.builds.append(
                BuildReceipt(
                    provisioner_id=best_offer.source_provisioner_id or best_offer.uid,
                    requirement_id=requirement.uid,
                    provider_id=None,
                    operation=_policy_from_offer(best_offer),
                    accepted=False,
                    hard_req=requirement.hard_requirement,
                    reason=str(exc),
                )
            )

    return result
