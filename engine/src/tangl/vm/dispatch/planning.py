# tangl.vm.planning.simple_planning_handlers.py
"""
Default planning handlers (reference implementation).

The planning phase is wired in three small steps:

1. ``planning_collect_offers`` (EARLY) – enumerate open frontier requirements and
   publish :class:`~tangl.vm.planning.ProvisionOffer` objects.
2. ``planning_link_affordances`` (NORMAL)
3. ``planning_link_dependencies`` (LATE) – coalesce offers per requirement, select
   by lowest priority, accept, and return :class:`~tangl.vm.planning.BuildReceipt`.
4. ``plan_compose_receipt`` (LAST) – summarize into a
   :class:`~tangl.vm.planning.PlanningReceipt`.

Domains can register additional builders/selectors at different priorities to
enrich or override behavior.
"""
from collections import defaultdict
from uuid import UUID
import logging
from functools import partial
from typing import Iterable

from tangl.core import Entity, Node
from tangl.core.behavior import HandlerPriority as Prio, CallReceipt, ContextP
from tangl.core.dispatch import scoped_dispatch
from tangl.vm import ResolutionPhase as P, Context, ChoiceEdge
from tangl.vm.provision import (
    Provisioner,
    ProvisionOffer,
    Dependency,
    AffordanceOffer,
    DependencyOffer,
    BuildReceipt,
    PlanningReceipt,
    ProvisioningPolicy,
)
from .vm_dispatch import vm_dispatch

logger = logging.getLogger(__name__)

get_dependencies = Dependency.get_dependencies
# todo: this should check that each dependency label is used only once per node

# todo: we also need to guarantee that at least **one** selectable edge
#       to a provisioned and available node exists on the frontier.

# --------------------------
# on-get provisioners helper

# system level task, specific to vm and applications that might use vm
on_get_provisioners = partial(vm_dispatch.register, task="get_provisioners")

# Assume anything with 'provisioners' wants to contribute.
@on_get_provisioners(priority=Prio.LATE)
def _contribute_local_provisioners(caller: Entity, *_, **__):
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
        # behavior ctx
        caller=anchor,
        ctx=ctx,  # Need context to get APP, AUTHOR layers
        with_kwargs=kwargs,

        # dispatch meta
        task="get_provisioners",
        extra_handlers=extra_handlers
    )
    return CallReceipt.merge_results(*receipts)  # chains results to single list

# --------------------------
# 1. Get offers (req get provisioners)

on_planning = partial(vm_dispatch.register, task=P.PLANNING)

def _policy_from_offer(offer: DependencyOffer) -> ProvisioningPolicy:
    try:
        return ProvisioningPolicy[offer.operation]
    except KeyError:
        return ProvisioningPolicy.NOOP


def _iter_frontier(cursor: Node) -> list[Node]:
    nodes = [
        edge.destination
        for edge in cursor.edges_out(is_instance=ChoiceEdge)
        if edge.destination is not None
    ]
    return nodes or [cursor]


def _attach_offer_metadata(
    offer: ProvisionOffer,
    provisioner: Provisioner,
    proximity: int,
) -> ProvisionOffer:
    if offer.source_provisioner_id is None:
        offer.source_provisioner_id = provisioner.uid
    if offer.source_layer is None:
        offer.source_layer = getattr(provisioner, "layer", None)
    offer.proximity = min(getattr(offer, "proximity", proximity), proximity)
    return offer


def _sort_offers(offers: Iterable[ProvisionOffer]) -> list[ProvisionOffer]:
    enumerated = list(enumerate(offers))
    return [
        offer
        for _, offer in sorted(
            enumerated,
            key=lambda item: (
                getattr(item[1], "cost", 0),
                getattr(item[1], "proximity", 999),
                item[0],
            ),
        )
    ]

@on_planning(priority=Prio.EARLY)
def _planning_collect_offers(cursor: Node, *, ctx: Context, **kwargs):
    """
    Collect affordance and responsive offers for the frontier.

    Returns:
        Dict mapping requirement UIDs to sorted offer lists:
        - offers['*'] = affordance offers (broadcast)
        - offers[dep.uid] = responsive offers (unicast)

    The behavior handler will wrap this in a call receipt and stash
    it in `ctx.call_receipts` by default.
    """

    provisioners = list(do_get_provisioners(cursor, ctx=ctx))
    indexed_provisioners = list(enumerate(provisioners))
    offers: dict[UUID | str, list[ProvisionOffer]] = defaultdict(list)

    for proximity, provisioner in indexed_provisioners:
        for offer in provisioner.get_affordance_offers(cursor, ctx=ctx):
            offers["*"].append(_attach_offer_metadata(offer, provisioner, proximity))

    for frontier_node in _iter_frontier(cursor):
        for dep in get_dependencies(frontier_node, satisfied=False):
            for proximity, provisioner in indexed_provisioners:
                for offer in provisioner.get_dependency_offers(dep.requirement, ctx=ctx):
                    offers[dep.uid].append(
                        _attach_offer_metadata(offer, provisioner, proximity)
                    )

    sorted_offers = {key: _sort_offers(value) for key, value in offers.items()}

    if hasattr(ctx, "provision_offers"):
        for key, value in sorted_offers.items():
            ctx.provision_offers.setdefault(key, []).extend(value)
    return sorted_offers
    # Offers are also be wrapped in a call receipt and added to ctx.call_receipts

# ------------------
# 2. Handle affordances

def _unstash_offers(ctx: ContextP) -> dict[UUID | str, list[ProvisionOffer]]:
    if hasattr(ctx, "provision_offers"):
        return ctx.provision_offers
    if hasattr(ctx, "call_receipts"):
        return ctx.call_receipts[-1].result
    raise RuntimeError(f"Unsupported context, can't find provision offers: {ctx}")

@on_planning(priority=Prio.NORMAL)
def _planning_link_affordances(cursor: Node, *, ctx: Context, **kwargs):

    offers = _unstash_offers(ctx)
    affordance_offers = offers.get("*", [])

    used_labels: dict[UUID, set[str]] = defaultdict(set)

    for offer in affordance_offers:
        if not isinstance(offer, AffordanceOffer):
            continue
        for frontier_node in _iter_frontier(cursor):
            label = offer.get_label()
            if label is not None and label in used_labels[frontier_node.uid]:
                continue
            if not offer.available_for(frontier_node):
                continue
            try:
                affordance_edge = offer.accept(ctx=ctx, destination=frontier_node)
            except Exception:
                logger.exception(
                    "Provisioner affordance offer failed",
                    extra={"offer": offer, "destination": frontier_node},
                )
                continue

            if label is not None:
                used_labels[frontier_node.uid].add(label)

            for dep in get_dependencies(frontier_node, satisfied=False):
                provider = affordance_edge.destination
                if provider is not None and dep.satisfied_by(provider):
                    dep.destination = provider

# --------------------------
# 3. accept offers and link

@on_planning(priority=Prio.LATE)
def _planning_link_dependencies(cursor: Node, *, ctx: Context, **kwargs):

    offers = _unstash_offers(ctx)
    builds = getattr(ctx, "provision_builds", [])

    for frontier_node in _iter_frontier(cursor):
        for dep in get_dependencies(frontier_node, satisfied=False):
            requirement = dep.requirement
            accepted_provider: Node | None = None

            for offer in offers.get(dep.uid, []):
                if not isinstance(offer, DependencyOffer):
                    continue
                try:
                    provider = offer.accept(ctx=ctx)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception(
                        "Provisioner dependency offer failed",
                        extra={"offer": offer, "requirement": requirement},
                    )
                    requirement.is_unresolvable = True
                    builds.append(
                        BuildReceipt(
                            provisioner_id=offer.source_provisioner_id or offer.uid,
                            requirement_id=requirement.uid,
                            provider_id=None,
                            operation=_policy_from_offer(offer),
                            accepted=False,
                            hard_req=requirement.hard_requirement,
                            reason=str(exc),
                        )
                    )
                    continue

                if provider is None:
                    continue

                dep.destination = provider
                for sibling in get_dependencies(frontier_node, satisfied=False):
                    if sibling is not dep and sibling.satisfied_by(provider):
                        sibling.destination = provider

                builds.append(
                    BuildReceipt(
                        provisioner_id=offer.source_provisioner_id or offer.uid,
                        requirement_id=requirement.uid,
                        provider_id=provider.uid,
                        operation=_policy_from_offer(offer),
                        accepted=True,
                        hard_req=requirement.hard_requirement,
                    )
                )
                accepted_provider = provider
                break

            if accepted_provider is None:
                requirement.is_unresolvable = True
                builds.append(
                    BuildReceipt(
                        provisioner_id=UUID(int=0),
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=requirement.hard_requirement,
                        reason="no_viable_offers",
                    )
                )

    return list(builds)

# --------------------------
# 4. Provide a summary job receipt

@on_planning(priority=Prio.LAST)
def _planning_job_receipt(cursor: Node, *, ctx: Context, **kwargs):
    """Summarize build receipts into a :class:`~tangl.vm.planning.PlanningReceipt`."""
    builds = getattr(ctx, "provision_builds", [])
    receipt = PlanningReceipt.summarize(*builds)
    ctx.provision_offers.clear()
    builds.clear()
    return receipt
