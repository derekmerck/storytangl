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
from warnings import warn

from tangl.core import Entity, Node
from tangl.core.behavior import HandlerPriority as Prio, CallReceipt, ContextP
from tangl.core.dispatch import scoped_dispatch
from tangl.vm import ResolutionPhase as P, Context, ChoiceEdge
from tangl.vm.provision import Provisioner, ProvisionOffer, Dependency
from .vm_dispatch import vm_dispatch

logger = logging.getLogger(__name__)

get_dependencies = Dependency.get_dependencies
# todo: this should check that each dependency label is used only once per node

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

def _sort_offers(offers: list[ProvisionOffer],
                 provisioners: list[Provisioner]) -> list[ProvisionOffer]:
    """
    Sort offers by:
    1. Priority (higher first) - from provisioner
    2. Proximity (closer first) - from provisioner's location
    3. Cost (lower first) - from offer
    """
    prov_ids = [p.uid for p in provisioners]

    def prox(o: ProvisionOffer):
        return prov_ids.index(o.blame_id)

    return sorted(
        offers,
        key=lambda o: ( -prox(o),
                        getattr(o, 'cost', 1.0)
        )
    )

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

    provisioners = do_get_provisioners(cursor, ctx=ctx)
    offers: dict[UUID|str, list[ProvisionOffer]] = defaultdict(list)

    # Gather broadcast affordance offers (not responsive to specific reqs)
    for prox, provisioner in enumerate( provisioners ):
        _offers = provisioner.get_offers()
        offers['*'].extend(_offers)

    # Gather responsive/unicast offers for each frontier node's dependencies
    for edge in cursor.edges_out(is_instance=ChoiceEdge):
        # All possible structural successors
        frontier_node = edge.destination
        if frontier_node is None:
            warn("Skipped missing frontier node, this should only happen in testing.")
            continue
        for dep in get_dependencies(frontier_node, satsified=False):
            for provisioner in provisioners:
                offers[dep.uid].extend(provisioner.get_offers(dep))

    offers = { k: _sort_offers(v, provisioners) for k, v in offers.items() }

    # Stash provision offers across sub-phases
    if hasattr(ctx, "provision_offers"):
        ctx.provision_offers.update(offers)  # frozen, don't reassign, update
    return offers
    # Offers are also be wrapped in a call receipt and added to ctx.call_receipts

# ------------------
# 2. Handle affordances

def _unstash_offers(ctx: ContextP) -> dict[UUID, ProvisionOffer]:
    if hasattr(ctx, "provision_offers"):
        return ctx.provision_offers
    if hasattr(ctx, "call_receipts"):
        return ctx.call_receipts[-1].result
    raise RuntimeError(f"Unsupported context, can't find provision offers: {ctx}")

@on_planning(priority=Prio.NORMAL)
def _planning_link_affordances(cursor: Node, *, ctx: Context, **kwargs):

    offers = _unstash_offers(ctx)
    affordance_offers = offers.get('*', [])
    # default dict, returns [] on missing, regardless

    # Track which affordance labels have been used per frontier node
    used_labels: dict[UUID, set[str]] = defaultdict(set)

    # for each affordance offer, try to link to all frontier nodes
    for offer in affordance_offers:
        for edge in cursor.edges_out(is_instance=ChoiceEdge):
            # All possible structural successors
            frontier_node = edge.destination
            ns = ctx.get_ns(frontier_node)

            if offer.satisfied_by(frontier_node) and \
                    offer.available(ns) and \
                    offer.get_label() not in used_labels[frontier_node.uid]:
                aff = offer.accept()  # type: Edge
                # todo: affordances may have _many_ sources or need to be copied
                #       when attached?  add_source() func that copies the edge?
                aff.sources.append(frontier_node)
                used_labels[frontier_node.uid].add(offer.get_label())

                for dep in get_dependencies(frontier_node, satisfied=False):
                    if dep.satsified_by(aff.destination):
                        dep.destination = aff.destination
                        # satisfy dependencies if possible

# --------------------------
# 3. accept offers and link

@on_planning(priority=Prio.LATE)
def _planning_link_dependencies(cursor: Node, *, ctx: Context, **kwargs):

    offers = _unstash_offers(ctx)

    # for each frontier node, try to link its deps with provide offers
    for edge in cursor.edges_out(is_instance=ChoiceEdge):
        # All possible structural successors
        frontier_node = edge.destination
        ns = ctx.get_ns(frontier_node)

        for dep in get_dependencies(frontier_node, satisfied=False):
            for offer in offers.get(dep.uid, []):
                # how do we sort offers by cost/prox
                # only accept one per dependency label?
                if offer.available(ns):  # responsive, guaranteed satisfied
                    provider = offer.accept()
                    dep.destination = provider  # calls on-link

                    # satisfy other dependencies if able
                    for dep_ in get_dependencies(frontier_node, satisfied=False):
                        if dep_.satsified_by(provider):
                            dep_.destination = provider

# --------------------------
# 4. Provide a summary job receipt

@on_planning(priority=Prio.LAST)
def _planning_job_receipt(cursor: Node, *, ctx: Context, **kwargs):
    """Summarize build receipts into a :class:`~tangl.vm.planning.PlanningReceipt`."""
    ...
