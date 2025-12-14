"""Pure provisioning helpers used by the planning pipeline."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from random import Random
from typing import Iterable, TYPE_CHECKING
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
from .requirement import ProvisioningPolicy, Requirement

if TYPE_CHECKING:  # pragma: no cover - import guarded for typing only
    from tangl.vm.context import Context


@dataclass(slots=True)
class ProvisioningContext:
    """VM-independent execution context for provisioning."""

    graph: Graph
    step: int
    rng_seed: int | None = None
    current_requirement_id: UUID | None = None
    current_requirement_label: str | None = None
    current_requirement_source_id: UUID | None = None

    _rand: Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        seed = self.rng_seed if self.rng_seed is not None else self.step
        self._rand = Random(seed)

    @property
    def rand(self) -> Random:
        """Return a deterministic random generator for provisioners."""

        return self._rand


@dataclass
class PlannedOffer:
    """Deferred execution of a provision offer captured during planning."""

    offer: ProvisionOffer
    requirement: Requirement | None = None
    dependency: Dependency | None = None
    affordance: Affordance | None = None
    destination: Node | None = None
    hard_requirement: bool | None = None

    def execute(self, *, ctx: "Context") -> BuildReceipt:
        """Execute ``offer`` and record the resulting build receipt."""

        provisioner_id = self.offer.source_provisioner_id or self.offer.uid
        requirement = self.requirement
        requirement_id = requirement.uid if requirement is not None else UUID(int=0)
        hard_req = self.hard_requirement if self.hard_requirement is not None else (
            requirement.hard_requirement if requirement is not None else False
        )

        try:
            if isinstance(self.offer, AffordanceOffer):
                edge = self.offer.accept(ctx=ctx, destination=self.destination)
                provider = edge.source if edge is not None else None
                resolved_requirement = edge.requirement if edge is not None else requirement
                if resolved_requirement is not None:
                    requirement_id = resolved_requirement.uid
                    if provider is not None and resolved_requirement.provider is None:
                        resolved_requirement.provider = provider
                if self.affordance is not None and provider is not None:
                    self.affordance.requirement.provider = provider
                if self.dependency is not None and provider is not None:
                    self.dependency.destination = provider
                operation = ProvisioningPolicy.EXISTING
            else:
                provider = self.offer.accept(ctx=ctx)
                if provider is None:
                    raise ValueError("Offer accepted without provider")
                if requirement is not None and requirement.provider is None:
                    requirement.provider = provider
                if self.dependency is not None:
                    self.dependency.destination = provider
                if self.affordance is not None:
                    self.affordance.requirement.provider = provider
                operation = _policy_from_offer(self.offer)

            provider_id = provider.uid if provider is not None else None
            return BuildReceipt(
                provisioner_id=provisioner_id,
                requirement_id=requirement_id,
                provider_id=provider_id,
                operation=operation,
                accepted=True,
                hard_req=hard_req,
                template_ref=getattr(self.offer, "template_ref", None),
                template_hash=getattr(self.offer, "template_hash", None),
                template_content_id=getattr(self.offer, "template_content_id", None),
            )
        except Exception as exc:  # pragma: no cover - defensive path
            if isinstance(self.offer, AffordanceOffer):
                operation = ProvisioningPolicy.EXISTING
            else:
                operation = _policy_from_offer(self.offer)
            return BuildReceipt(
                provisioner_id=provisioner_id,
                requirement_id=requirement_id,
                provider_id=None,
                operation=operation,
                accepted=False,
                hard_req=hard_req,
                reason=str(exc),
                template_ref=getattr(self.offer, "template_ref", None),
                template_hash=getattr(self.offer, "template_hash", None),
                template_content_id=getattr(self.offer, "template_content_id", None),
            )


@dataclass
class ProvisioningPlan:
    """Plan describing how to satisfy requirements for a node."""

    node: Node
    steps: list[PlannedOffer] = field(default_factory=list)
    satisfied_requirement_ids: set[UUID] = field(default_factory=set)
    already_satisfied_requirement_ids: set[UUID] = field(default_factory=set)

    _executed: bool = field(default=False, init=False, repr=False)
    _receipts: list[BuildReceipt] = field(default_factory=list, init=False, repr=False)

    def execute(self, *, ctx: "Context") -> list[BuildReceipt]:
        """Execute the plan once and return resulting build receipts."""

        if self._executed:
            return list(self._receipts)

        receipts: list[BuildReceipt] = []
        for planned in self.steps:
            requirement = planned.requirement
            if requirement is not None and requirement.provider is not None:
                continue
            receipts.append(planned.execute(ctx=ctx))

        self._receipts = receipts
        self._executed = True
        return list(receipts)

    @property
    def planned_accept_count(self) -> int:
        """Return how many offers this plan will attempt to accept."""

        return len(self.steps)


@dataclass
class ProvisioningResult:
    """Result of provisioning a single structural node."""

    node: Node
    plans: list[ProvisioningPlan] = field(default_factory=list)
    builds: list[BuildReceipt] = field(default_factory=list)
    dependency_offers: dict[UUID, list[DependencyOffer]] = field(default_factory=dict)
    affordance_offers: list[AffordanceOffer] = field(default_factory=list)
    unresolved_hard_requirements: list[UUID] = field(default_factory=list)
    waived_soft_requirements: list[UUID] = field(default_factory=list)
    selection_metadata: dict[UUID, dict[str, object]] = field(default_factory=dict)

    @property
    def primary_plan(self) -> ProvisioningPlan | None:
        """Return the preferred plan for this node when available."""

        return self.plans[0] if self.plans else None

    @property
    def satisfied_count(self) -> int:
        """Number of requirements expected to be satisfied by the plan or builds."""

        if self.builds:
            return sum(1 for build in self.builds if build.accepted)

        plan = self.primary_plan
        if plan is None:
            return 0
        return len(plan.satisfied_requirement_ids) + len(plan.already_satisfied_requirement_ids)

    @property
    def is_viable(self) -> bool:
        """True when no hard requirements remain unresolved."""

        return not self.unresolved_hard_requirements


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
    if getattr(offer, "proximity", None) in (None, 999, 999.0):
        offer.proximity = float(proximity)
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


def _select_best_offer(
    offers: Iterable[ProvisionOffer],
) -> tuple[ProvisionOffer | None, dict[str, object]]:
    """Select the most desirable offer from *offers* and record audit metadata."""

    enumerated = list(enumerate(offers))
    if not enumerated:
        return None, {
            "reason": "no_offers",
            "num_offers": 0,
            "all_offers": [],
        }

    sorted_offers = sorted(
        enumerated,
        key=lambda item: (
            item[1].cost,
            item[1].proximity,
            item[0],
        ),
    )
    best_index, best_offer = sorted_offers[0]

    audit_entries: list[dict[str, object]] = []
    for _, offer in sorted_offers:
        policy = _policy_from_offer(offer)
        audit_entries.append(
            {
                "provider_id": str(offer.provider_id) if getattr(offer, "provider_id", None) else None,
                "cost": offer.cost,
                "base_cost": float(getattr(offer, "base_cost", offer.cost)),
                "proximity": offer.proximity,
                "proximity_detail": getattr(offer, "proximity_detail", None),
                "operation": policy.name,
                "source_provisioner_id": str(offer.source_provisioner_id)
                if getattr(offer, "source_provisioner_id", None)
                else None,
            }
        )

    metadata = {
        "reason": "best_cost",
        "selected_cost": best_offer.cost if best_offer is not None else None,
        "selected_provider_id": str(best_offer.provider_id)
        if getattr(best_offer, "provider_id", None)
        else None,
        "selected_index": best_index,
        "num_offers": len(sorted_offers),
        "all_offers": audit_entries,
    }

    return best_offer, metadata


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

    # don't forget to check provisioning for all of the ancestors as well
    # particularly important when going into a new scene (fixme, shouldn't
    # be hidden like this)
    dependencies = []
    for a in reversed( [node] + list(node.ancestors()) ):
        dependencies.extend(list(Dependency.get_dependencies(a)))
    # dependencies = list(Dependency.get_dependencies(node))

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
        requirement = dep.requirement
        if requirement.provider is not None:
            continue
        offer_map.setdefault(requirement_id, [])
        ctx.current_requirement_id = requirement.uid
        ctx.current_requirement_label = requirement.label
        ctx.current_requirement_source_id = dep.source_id
        for proximity, provisioner in indexed_provisioners:
            try:
                offers_iter = provisioner.get_dependency_offers(requirement, ctx=ctx)
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
        ctx.current_requirement_id = requirement.uid
        ctx.current_requirement_label = requirement.label
        ctx.current_requirement_source_id = affordance.destination_id
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

    plan = ProvisioningPlan(node=node)

    for dep in dependencies:
        requirement = dep.requirement
        if requirement.provider is not None:
            plan.already_satisfied_requirement_ids.add(requirement.uid)

    for affordance in inbound_affordances:
        requirement = affordance.requirement
        if requirement is not None and requirement.provider is not None:
            plan.already_satisfied_requirement_ids.add(requirement.uid)

    used_affordance_labels: dict[UUID, set[str]] = defaultdict(set)

    for offer in result.affordance_offers:
        if not isinstance(offer, AffordanceOffer):
            continue
        label = offer.get_label()
        if label is not None and label in used_affordance_labels[node.uid]:
            continue
        if not offer.available_for(node):
            continue
        if label is not None:
            used_affordance_labels[node.uid].add(label)
        plan.steps.append(
            PlannedOffer(
                offer=offer,
                destination=node,
                hard_requirement=False,
            )
        )

    for requirement_id, offers in deduplicated_map.items():
        dependency = dependency_by_requirement.get(requirement_id)
        affordance = affordance_by_requirement.get(requirement_id)
        requirement = (
            dependency.requirement if dependency is not None else (
                affordance.requirement if affordance is not None else None
            )
        )
        if requirement is None:
            continue
        if requirement.provider is not None:
            plan.already_satisfied_requirement_ids.add(requirement.uid)
            continue
        best_offer, selection_meta = _select_best_offer(offers)
        selection_meta.setdefault("requirement_label", requirement.label)
        selection_meta.setdefault("requirement_uid", str(requirement.uid))
        selection_meta.setdefault("node_label", node.label)
        result.selection_metadata[requirement.uid] = selection_meta
        if best_offer is None:
            if requirement.hard_requirement:
                result.unresolved_hard_requirements.append(requirement.uid)
            else:
                result.waived_soft_requirements.append(requirement.uid)
            continue
        plan.satisfied_requirement_ids.add(requirement.uid)
        plan.steps.append(
            PlannedOffer(
                offer=best_offer,
                requirement=requirement,
                dependency=dependency,
                affordance=affordance,
                hard_requirement=requirement.hard_requirement,
            )
        )

    result.unresolved_hard_requirements = list(dict.fromkeys(result.unresolved_hard_requirements))
    result.waived_soft_requirements = list(dict.fromkeys(result.waived_soft_requirements))

    result.plans.append(plan)

    return result
