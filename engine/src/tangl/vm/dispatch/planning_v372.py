# tangl.vm.dispatch.planning
"""
Default planning handlers (v3.7 refactored implementation).

The planning phase is wired in four small steps:

1. ``planning_collect_offers`` (EARLY) – enumerate open frontier requirements,
   deduplicate EXISTING offers, and sort by (cost, proximity, registration order).
2. ``planning_link_affordances`` (NORMAL) – filter available affordances and accept.
3. ``planning_link_dependencies`` (LATE) – select best offer per requirement and accept.
4. ``planning_job_receipt`` (LAST) – summarize into a PlanningReceipt.

Key improvements from legacy implementation:
- Deduplication of EXISTING offers by provider_id (keeps cheapest/closest)
- Selection before execution (no try-until-success loops)
- Always generate BuildReceipts (success or failure)
"""

from collections import defaultdict
from uuid import UUID
from typing import Iterable
from functools import partial
import logging

from tangl.core import Entity, Node, Graph
from tangl.core.behavior import HandlerPriority as Prio, CallReceipt, ContextP
from tangl.core.dispatch import scoped_dispatch
from tangl.vm import Context, ChoiceEdge, ResolutionPhase as P
from tangl.vm.provision import (
    Provisioner,
    ProvisionOffer,
    DependencyOffer,
    AffordanceOffer,
    Dependency,
    Affordance,
    BuildReceipt,
    PlanningReceipt,
    ProvisioningPolicy,
    GraphProvisioner,
    TemplateProvisioner,
    UpdatingProvisioner,
    CloningProvisioner,
)
from .vm_dispatch import vm_dispatch

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

def get_dependencies(*args, **kwargs) -> list[Dependency]:
    return list( Dependency.get_dependencies(*args, **kwargs) )

# --------------------------
# Provisioner discovery

on_get_provisioners = partial(vm_dispatch.register, task="get_provisioners")


@on_get_provisioners(priority=Prio.EARLY)
def _inject_default_provisioners(caller: Entity, *, ctx: Context, **_):
    """Provide baseline provisioners for graphs without custom handlers."""

    if not isinstance(caller, Graph):
        return []

    registry = ctx.graph
    return [
        GraphProvisioner(node_registry=registry, layer="local"),
        UpdatingProvisioner(node_registry=registry, layer="local"),
        CloningProvisioner(node_registry=registry, layer="local"),
        TemplateProvisioner(template_registry=None, layer="local"),
    ]


@on_get_provisioners(priority=Prio.LATE)
def _contribute_local_provisioners(caller: Entity, *_, **__):
    """Contribute provisioners from entities that have them."""
    if hasattr(caller, "provisioners"):
        return caller.provisioners


def do_get_provisioners(anchor: Node, *, ctx: ContextP, extra_handlers=None, **kwargs) -> list[Provisioner]:
    """
    Walks local layers (ancestors) and gathers provisioners.

    Non-specific application and author level owner handlers may want to
    register with is_instance=Graph rather than is_instance=Node, so they
    are only included once at the top.
    """
    receipts = scoped_dispatch(
        caller=anchor,
        ctx=ctx,
        with_kwargs=kwargs,
        task="get_provisioners",
        extra_handlers=extra_handlers
    )
    return CallReceipt.merge_results(*receipts)


# --------------------------
# Helper functions

def _iter_frontier(cursor: Node) -> list[Node]:
    """Return the active cursor as the planning frontier."""

    return [cursor]


def _attach_offer_metadata(
    offer: ProvisionOffer,
    provisioner: Provisioner,
    proximity: int,
    *,
    source: str,
) -> ProvisionOffer:
    """Attach provisioner metadata to offer."""
    if offer.source_provisioner_id is None:
        offer.source_provisioner_id = provisioner.uid
    if offer.source_layer is None:
        offer.source_layer = getattr(provisioner, "layer", None)
    offer.proximity = min(getattr(offer, "proximity", proximity), proximity)
    if not hasattr(offer, "selection_criteria") or offer.selection_criteria is None:
        offer.selection_criteria = {}
    if "source" not in offer.selection_criteria:
        offer.selection_criteria["source"] = source
    return offer


def _deduplicate_offers(offers: list[ProvisionOffer]) -> list[ProvisionOffer]:
    """
    Deduplicate EXISTING offers by provider_id.

    For EXISTING offers with the same provider_id, keep only the best one
    (lowest cost, closest proximity, earliest registration).

    CREATE/UPDATE/CLONE offers are never deduplicated since they produce
    distinct results.
    """
    # Separate EXISTING from other offers
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

    # For each provider_id, keep only the best EXISTING offer
    deduplicated: list[tuple[int, ProvisionOffer]] = []

    for provider_offers in existing_by_provider.values():
        # Sort by (cost, proximity, original_index)
        best = min(
            provider_offers,
            key=lambda item: (
                item[1].cost,
                item[1].proximity,
                item[0],  # Registration order
            )
        )
        deduplicated.append(best)

    # Add back non-EXISTING offers
    deduplicated.extend(non_existing)

    # Sort by (cost, proximity, original_index) to maintain proper ordering
    deduplicated.sort(key=lambda item: (
        item[1].cost,
        item[1].proximity,
        item[0],
    ))

    return [offer for _, offer in deduplicated]


def _select_best_offer(offers: Iterable[ProvisionOffer]) -> ProvisionOffer | None:
    """
    Select the best offer from a deduplicated list.

    Selection criteria (in order):
    1. Lowest cost (DIRECT < LIGHT_INDIRECT < HEAVY_INDIRECT < CREATE)
    2. Closest proximity (lower is better)
    3. Registration order (first wins)
    """
    enumerated = list(enumerate(offers))
    if not enumerated:
        return None

    best_idx, best_offer = min(
        enumerated,
        key=lambda item: (
            item[1].cost,
            item[1].proximity,
            item[0],  # Registration order as tiebreaker
        )
    )

    return best_offer


def _policy_from_offer(offer: DependencyOffer) -> ProvisioningPolicy:
    """Extract provisioning policy from offer operation string."""
    if isinstance(offer.operation, ProvisioningPolicy):
        return offer.operation
    try:
        return ProvisioningPolicy[str(offer.operation)]
    except KeyError:
        return ProvisioningPolicy.NOOP


# --------------------------
# Planning phase handlers

on_planning = partial(vm_dispatch.register, task=P.PLANNING)


@on_planning(priority=Prio.EARLY)
def _planning_collect_offers(cursor: Node, *, ctx: Context, **kwargs):
    """
    Collect affordance and responsive offers for the frontier.

    This handler:
    - Gathers provisioners via scoped_dispatch
    - Collects affordance offers (broadcast to all frontier nodes)
    - Collects dependency offers (targeted to specific requirements)
    - Deduplicates EXISTING offers by provider_id
    - Sorts all offers by (cost, proximity, registration order)

    Returns:
        Dict mapping requirement UIDs to sorted offer lists:
        - offers['*'] = affordance offers (broadcast)
        - offers[dep.uid] = responsive dependency offers (unicast)
    """
    provisioners = list(do_get_provisioners(cursor, ctx=ctx))
    indexed_provisioners = list(enumerate(provisioners))
    offers: dict[UUID | str, list[ProvisionOffer]] = defaultdict(list)

    # Collect affordance offers (broadcast)
    for proximity, provisioner in indexed_provisioners:
        for offer in provisioner.get_affordance_offers(cursor, ctx=ctx):
            offers["*"].append(
                _attach_offer_metadata(offer, provisioner, proximity, source="affordance")
            )

    # Collect dependency offers (unicast per requirement)
    for frontier_node in _iter_frontier(cursor):
        for dep in get_dependencies(frontier_node):
            if dep.requirement.provider is not None:
                continue
            for proximity, provisioner in indexed_provisioners:
                for offer in provisioner.get_dependency_offers(dep.requirement, ctx=ctx):
                    offers[dep.uid].append(
                        _attach_offer_metadata(
                            offer,
                            provisioner,
                            proximity,
                            source="dependency",
                        )
                    )

        for affordance in frontier_node.edges_in(is_instance=Affordance):
            requirement = affordance.requirement
            if requirement.provider is not None:
                continue
            key = f"affordance:{requirement.uid}"
            for proximity, provisioner in indexed_provisioners:
                for offer in provisioner.get_dependency_offers(requirement, ctx=ctx):
                    offers[key].append(
                        _attach_offer_metadata(
                            offer,
                            provisioner,
                            proximity,
                            source="affordance",
                        )
                    )

    # Deduplicate and sort ALL offer lists
    deduplicated_offers = {}
    for key, offer_list in offers.items():
        deduplicated_offers[key] = _deduplicate_offers(offer_list)

    # Store in context for next handlers
    if not hasattr(ctx, "provision_offers"):
        ctx.provision_offers = {}
    ctx.provision_offers.update(deduplicated_offers)

    flattened: list[ProvisionOffer] = []
    for offer_list in deduplicated_offers.values():
        flattened.extend(offer_list)

    return flattened


@on_planning(priority=Prio.NORMAL)
def _planning_link_affordances(cursor: Node, *, ctx: Context, **kwargs):
    """
    Select and accept best affordance offers.

    For each frontier node:
    - Filter affordances by availability (target_tags match)
    - Ensure label uniqueness per destination
    - Accept all available affordances (additive, not exclusive)
    - Check if affordances satisfy any dependencies
    """
    if not hasattr(ctx, "provision_offers"):
        return []

    if not hasattr(ctx, "provision_builds"):
        ctx.provision_builds = []

    affordance_offers = ctx.provision_offers.get("*", [])
    used_labels: dict[UUID, set[str]] = defaultdict(set)
    builds_snapshot = []
    satisfied_requirements: set[UUID] = set()

    for frontier_node in _iter_frontier(cursor):
        # Filter available offers for this frontier node
        for offer in affordance_offers:
            if not isinstance(offer, AffordanceOffer):
                continue

            label = offer.get_label()
            if label is not None and label in used_labels[frontier_node.uid]:
                continue

            if not offer.available_for(frontier_node):
                continue

            # Accept this affordance
            try:
                affordance_edge = offer.accept(ctx=ctx, destination=frontier_node)
                requirement = affordance_edge.requirement
                if requirement is not None:
                    satisfied_requirements.add(requirement.uid)

                if label is not None:
                    used_labels[frontier_node.uid].add(label)

                # Check if this affordance satisfies any dependencies
                provider = affordance_edge.source
                if provider is not None:
                    for dep in get_dependencies(frontier_node):
                        if dep.requirement.provider is not None:
                            continue
                        if dep.satisfied_by(provider):
                            dep.destination = provider

                # Record success (affordances don't have specific requirement IDs)
                build = BuildReceipt(
                    provisioner_id=offer.source_provisioner_id or offer.uid,
                    requirement_id=UUID(int=0),  # Affordances aren't requirement-specific
                    provider_id=provider.uid if provider else None,
                    operation=ProvisioningPolicy.EXISTING,
                    accepted=True,
                    hard_req=False,  # Affordances are always soft
                )
                ctx.provision_builds.append(build)
                builds_snapshot.append(build)

            except Exception:
                logger.exception(
                    "Affordance offer failed",
                    extra={"offer": offer, "destination": frontier_node},
                )
                # Don't create BuildReceipt for failed affordances
                continue

        for affordance in list(frontier_node.edges_in(is_instance=Affordance)):
            requirement = affordance.requirement
            if requirement.provider is not None:
                satisfied_requirements.add(requirement.uid)
                continue

            fallback_key = f"affordance:{requirement.uid}"
            fallback_offers = ctx.provision_offers.get(fallback_key, [])
            best_offer = _select_best_offer(fallback_offers)

            if best_offer is not None:
                try:
                    provider = best_offer.accept(ctx=ctx)
                    if provider is None:
                        raise ValueError("Offer accepted but returned None")
                    requirement.provider = provider
                    satisfied_requirements.add(requirement.uid)
                    build = BuildReceipt(
                        provisioner_id=best_offer.source_provisioner_id or best_offer.uid,
                        requirement_id=requirement.uid,
                        provider_id=provider.uid,
                        operation=_policy_from_offer(best_offer),
                        accepted=True,
                        hard_req=requirement.hard_requirement,
                    )
                    ctx.provision_builds.append(build)
                    builds_snapshot.append(build)
                except Exception as exc:
                    logger.exception(
                        "Fallback affordance offer failed",
                        extra={"offer": best_offer, "requirement": requirement},
                    )
                    requirement.is_unresolvable = True
                    build = BuildReceipt(
                        provisioner_id=best_offer.source_provisioner_id or best_offer.uid,
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=_policy_from_offer(best_offer),
                        accepted=False,
                        hard_req=requirement.hard_requirement,
                        reason=str(exc),
                    )
                    ctx.provision_builds.append(build)
                    builds_snapshot.append(build)
                finally:
                    ctx.provision_offers.pop(fallback_key, None)
            elif requirement.hard_requirement and requirement.uid not in satisfied_requirements:
                requirement.is_unresolvable = True
                build = BuildReceipt(
                    provisioner_id=UUID(int=0),
                    requirement_id=requirement.uid,
                    provider_id=None,
                    operation=ProvisioningPolicy.NOOP,
                    accepted=False,
                    hard_req=True,
                    reason="no_offers",
                )
                ctx.provision_builds.append(build)
                builds_snapshot.append(build)

    # Return a snapshot, not the reference to ctx.provision_builds
    return builds_snapshot


@on_planning(priority=Prio.LATE)
def _planning_link_dependencies(cursor: Node, *, ctx: Context, **kwargs):
    """
    Select and accept best dependency offers.

    For each unsatisfied dependency:
    - Get deduplicated offers (already done in EARLY)
    - Select best offer by cost/proximity/order
    - Accept ONCE (not try-until-success)
    - Build receipt for success or failure
    - Bind provider if successful
    - Check if provider also satisfies sibling dependencies
    """
    if not hasattr(ctx, "provision_offers"):
        return []

    if not hasattr(ctx, "provision_builds"):
        ctx.provision_builds = []

    builds_snapshot = []

    for frontier_node in _iter_frontier(cursor):
        # Materialize dependencies list BEFORE iterating
        # This prevents "dictionary changed size during iteration" errors
        # when accept() calls add nodes to the graph
        deps = [dep for dep in get_dependencies(frontier_node) if dep.requirement.provider is None]
        for dep in deps:
            requirement = dep.requirement
            offers = ctx.provision_offers.get(dep.uid, [])

            if not offers:
                requirement.is_unresolvable = True
                build = BuildReceipt(
                    provisioner_id=UUID(int=0),
                    requirement_id=requirement.uid,
                    provider_id=None,
                    operation=ProvisioningPolicy.NOOP,
                    accepted=False,
                    hard_req=requirement.hard_requirement,
                    reason="no_offers",
                )
                ctx.provision_builds.append(build)
                builds_snapshot.append(build)
                continue

            provider = None
            winning_offer: DependencyOffer | None = None
            for candidate in offers:
                try:
                    provider = candidate.accept(ctx=ctx)
                except Exception as exc:
                    logger.exception(
                        "Dependency offer failed",
                        extra={"offer": candidate, "requirement": requirement},
                    )
                    continue

                if provider is None:
                    continue

                winning_offer = candidate
                break

            if provider is None or winning_offer is None:
                requirement.is_unresolvable = True
                build = BuildReceipt(
                    provisioner_id=offers[0].source_provisioner_id or offers[0].uid,
                    requirement_id=requirement.uid,
                    provider_id=None,
                    operation=_policy_from_offer(offers[0]),
                    accepted=False,
                    hard_req=requirement.hard_requirement,
                    reason="no_viable_offers",
                )
                ctx.provision_builds.append(build)
                builds_snapshot.append(build)
                continue

            dep.destination = provider

            for sibling in deps:
                if sibling is not dep and sibling.satisfied_by(provider):
                    sibling.destination = provider

            build = BuildReceipt(
                provisioner_id=winning_offer.source_provisioner_id or winning_offer.uid,
                requirement_id=requirement.uid,
                provider_id=provider.uid,
                operation=_policy_from_offer(winning_offer),
                accepted=True,
                hard_req=requirement.hard_requirement,
            )
            ctx.provision_builds.append(build)
            builds_snapshot.append(build)

    # Return a snapshot, not the reference to ctx.provision_builds
    return builds_snapshot


@on_planning(priority=Prio.LAST)
def _planning_job_receipt(cursor: Node, *, ctx: Context, **kwargs):
    """
    Summarize build receipts into a PlanningReceipt.

    This handler:
    - Collects all BuildReceipts from ctx.provision_builds
    - Summarizes into a single PlanningReceipt
    - Cleans up context state

    Note: Previous handlers return snapshots of provision_builds,
    so clearing here doesn't affect their CallReceipt results.
    """
    builds = getattr(ctx, "provision_builds", [])
    receipt = PlanningReceipt.summarize(*builds)

    # Clean up context (safe because handlers returned snapshots)
    if hasattr(ctx, "provision_offers"):
        ctx.provision_offers.clear()
    if hasattr(ctx, "provision_builds"):
        ctx.provision_builds.clear()

    return receipt


def plan_collect_offers(cursor: Node, *, ctx: Context) -> list[ProvisionOffer]:
    """Compatibility helper returning a flattened list of provision offers."""

    ctx.provision_offers.clear()
    offers = _planning_collect_offers(cursor, ctx=ctx)
    return list(offers)


def plan_select_and_apply(cursor: Node, *, ctx: Context) -> list[BuildReceipt]:
    """Compatibility helper emulating the legacy selector pipeline."""

    if not ctx.provision_offers:
        offers_by_req: dict[UUID, list[DependencyOffer]] = defaultdict(list)
        affordance_offers: list[AffordanceOffer] = []
        for receipt in ctx.call_receipts:
            result = receipt.result
            if isinstance(result, list):
                candidates = result
            else:
                candidates = [result]
            for offer in candidates:
                if isinstance(offer, AffordanceOffer):
                    affordance_offers.append(offer)
                elif isinstance(offer, DependencyOffer):
                    offers_by_req.setdefault(offer.requirement_id, []).append(offer)
        if affordance_offers:
            ctx.provision_offers["*"] = _deduplicate_offers(affordance_offers)

        if offers_by_req:
            for dep in cursor.edges_out(is_instance=Dependency):
                offer_list = offers_by_req.get(dep.requirement.uid)
                if offer_list:
                    ctx.provision_offers[dep.uid] = _deduplicate_offers(offer_list)

    ctx.provision_builds.clear()
    affordance_builds = _planning_link_affordances(cursor, ctx=ctx)
    dependency_builds = _planning_link_dependencies(cursor, ctx=ctx)
    return list(affordance_builds) + list(dependency_builds)