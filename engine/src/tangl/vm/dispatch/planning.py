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
from tangl.vm.provision import Provisioner, ProvisionOffer, Dependency, Affordance
from .vm_dispatch import vm_dispatch

logger = logging.getLogger(__name__)

get_dependencies = Dependency.get_dependencies

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
    return CallReceipt.merge_results(*receipts)

    # todo: implement a flatten merge for list inputs
    return CallReceipt.merge_results(*receipts)

# --------------------------
# 1. Get offers (req get provisioners)

on_planning = partial(vm_dispatch.register, task=P.PLANNING)

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
    for provisioner in provisioners:
        offers['*'].extend(provisioner.get_offers())

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

    return offers


# ------------------
# 2. Handle affordances

@on_planning(priority=Prio.NORMAL)
def _planning_link_affordances(cursor: Node, *, ctx: Context, **kwargs):
    offers = ctx.call_receipts[-1].result
    affordance_offers = offers.get('*', [])
    # default dict, returns [] on missing, regardless

    # for each affordance offer, try to link to all frontier nodes
    for offer in affordance_offers:
        for edge in cursor.edges_out(is_instance=ChoiceEdge):
            # All possible structural successors
            frontier_node = edge.destination
            ns = ctx.get_ns(frontier_node)

            if offer.satisfied_by(frontier_node) and offer.available(ns):
                aff = offer.accept()  # type: Edge
                # affordances may have _many_ sources
                aff.sources.append(frontier_node)

                for dep in get_dependencies(frontier_node, satisfied=False):
                    if dep.satsified_by(aff.destination):
                        dep.destination = aff.destination
                        # satisfy dependencies if possible

    # how do we sort by cost/proximity
    # how do we restrict to a single aff of a given label?


# --------------------------
# 3. accept offers and link

@on_planning(priority=Prio.LATE)
def _planning_link_dependencies(cursor: Node, *, ctx: Context, **kwargs):

    offers = ctx.call_receipts[-1].result

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

        # sort dep discovery by which offers are cheapest
        # sort offers by cost/prox

# --------------------------
# 4. Provide a summary job receipt

@on_planning(priority=Prio.LAST)
def _planning_job_receipt(cursor: Node, *, ctx: Context, **kwargs):
    ...


# def _label_for(requirement: Requirement, prefix: str) -> str:
#     base = requirement.get_label()
#     if not base:
#         base = requirement.identifier or requirement.uid.hex[:8]
#     return f"{prefix}:{base}"
#
# def _collect(requirement: Requirement, *, source: str, prefix: str) -> None:
#     for prov in provs:
#         for offer in prov.get_offers(requirement, ctx=ctx):
#             offer.label = offer.label or _label_for(requirement, prefix)
#             if "source" not in offer.selection_criteria:
#                 offer.selection_criteria = dict(offer.selection_criteria)
#                 offer.selection_criteria["source"] = source
#             offers.append(offer)
#
# # Affordances visible in scope should be evaluated before dependencies so
# # existing resources can satisfy requirements without provisioning new ones.
# affordances = sorted(
#     (
#         edge
#         for edge in ctx.graph.find_all(
#             is_instance=Affordance,
#             destination_id=cursor.uid,
#         )
#         if edge.requirement.provider is None
#     ),
#     key=lambda edge: edge.requirement.uid.int,
# )
# for edge in affordances:
#     _collect(edge.requirement, source="affordance", prefix="aff")
#
# # Dependencies on the frontier
# dependencies = sorted(
#     (
#         edge
#         for edge in ctx.graph.find_all(
#             is_instance=Dependency,
#             source_id=cursor.uid,
#         )
#         if edge.requirement.provider is None
#     ),
#     key=lambda edge: edge.requirement.uid.int,
# )
# for edge in dependencies:
#     _collect(edge.requirement, source="dependency", prefix="dep")
#
# return offers
#
# @on_planning(priority=HandlerPriority.LATE)
# # 2) Select + apply (NORMAL/LATE)
# # @global_domain.handlers.register(phase=P.PLANNING, priority=75)
# def plan_select_and_apply(cursor: Node, *, ctx: Context, **kwargs):
#     """Select offers, bind providers, and emit :class:`BuildReceipt` records.
#
#     ``ProvisionOffer.accept`` now returns a provider without side effects. This
#     selector performs the binding, updates :attr:`Requirement.is_unresolvable`,
#     and constructs receipts summarizing the outcome for each requirement.
#     """
#     # Gather offers from earlier receipts
#     all_offers: list[ProvisionOffer] = []
#     for r in ctx.call_receipts:
#         if isinstance(r.result, list):
#             all_offers.extend([x for x in r.result if isinstance(x, ProvisionOffer)])
#         elif isinstance(r.result, ProvisionOffer):
#             all_offers.append(r.result)
#
#     # Coalesce by requirement uid and remember requirements on the frontier
#     offers_by_req: dict[UUID, list[ProvisionOffer]] = {}
#     requirements: dict[UUID, Requirement] = {}
#
#     def include_requirement(req: Requirement) -> None:
#         requirements.setdefault(req.uid, req)
#
#     for off in all_offers:
#         offers_by_req.setdefault(off.requirement.uid, []).append(off)
#         include_requirement(off.requirement)
#
#     # Include unresolved frontier requirements even when no offers were published
#     for edge in cursor.edges_out(is_instance=Dependency):
#         if edge.requirement.provider is not None:
#             continue
#         include_requirement(edge.requirement)
#     for edge in cursor.edges_in(is_instance=Affordance):
#         if edge.requirement.provider is not None:
#             continue
#         include_requirement(edge.requirement)
#
#     # Evaluate requirements in a deterministic order for testability/debuggability.
#     ordered_requirements = sorted(
#         requirements.values(),
#         key=lambda req: req.uid.int,
#     )
#
#     builds: list[BuildReceipt] = []
#     for requirement in ordered_requirements:
#         candidates = offers_by_req.get(requirement.uid, [])
#
#         if requirement.provider is not None and not candidates:
#             # Already satisfied and no new offers to evaluate.
#             requirement.is_unresolvable = False
#             continue
#
#         if not candidates:
#             if requirement.hard_requirement:
#                 requirement.is_unresolvable = True
#                 builds.append(
#                     BuildReceipt(
#                         provisioner_id=cursor.uid,
#                         requirement_id=requirement.uid,
#                         provider_id=None,
#                         operation=ProvisioningPolicy.NOOP,
#                         accepted=False,
#                         hard_req=True,
#                         reason="no_offers",
#                     )
#                 )
#             else:
#                 builds.append(
#                     BuildReceipt(
#                         provisioner_id=cursor.uid,
#                         requirement_id=requirement.uid,
#                         provider_id=None,
#                         operation=ProvisioningPolicy.NOOP,
#                         accepted=False,
#                         hard_req=False,
#                         reason="waived_soft",
#                     )
#                 )
#             continue
#
#         def _candidate_sort_key(offer: ProvisionOffer) -> tuple[int, int, int]:
#             source = (offer.selection_criteria or {}).get("source")
#             source_rank = 0 if source == "affordance" else 1
#             return (source_rank, offer.priority, offer.uid.int)
#
#         candidates.sort(key=_candidate_sort_key)
#
#         chosen_offer: ProvisionOffer | None = None
#         provider: Node | None = None
#         for offer in candidates:
#             candidate_provider = offer.accept(ctx=ctx)
#             if candidate_provider is None:
#                 continue
#             chosen_offer = offer
#             provider = candidate_provider
#             break
#
#         if provider is None or chosen_offer is None:
#             provisioner_id = (
#                 candidates[0].provisioner.uid if candidates else cursor.uid
#             )
#             if requirement.hard_requirement:
#                 requirement.is_unresolvable = True
#                 builds.append(
#                     BuildReceipt(
#                         provisioner_id=provisioner_id,
#                         requirement_id=requirement.uid,
#                         provider_id=None,
#                         operation=ProvisioningPolicy.NOOP,
#                         accepted=False,
#                         hard_req=True,
#                         reason="unresolvable",
#                     )
#                 )
#             else:
#                 builds.append(
#                     BuildReceipt(
#                         provisioner_id=provisioner_id,
#                         requirement_id=requirement.uid,
#                         provider_id=None,
#                         operation=ProvisioningPolicy.NOOP,
#                         accepted=False,
#                         hard_req=False,
#                         reason="waived_soft",
#                     )
#                 )
#             continue
#
#         # Successful binding: attach provider and clear any prior failures.
#         requirement.provider = provider
#         if requirement.hard_requirement:
#             requirement.is_unresolvable = False
#
#         builds.append(
#             BuildReceipt(
#                 provisioner_id=chosen_offer.provisioner.uid,
#                 requirement_id=requirement.uid,
#                 provider_id=provider.uid,
#                 operation=chosen_offer.operation or ProvisioningPolicy.NOOP,
#                 accepted=True,
#                 hard_req=requirement.hard_requirement,
#             )
#         )
#
#     return builds
#
# @on_planning(priority=HandlerPriority.LAST)
# # 3) Compose a PlanningReceipt (LAST)
# # @global_domain.handlers.register(phase=P.PLANNING, priority=100)
# def plan_compose_receipt(cursor: Node, *, ctx: Context, **kwargs):
#     """Summarize build receipts into a :class:`~tangl.vm.planning.PlanningReceipt`."""
#     builds: list[BuildReceipt] = []
#     for r in ctx.call_receipts:
#         if isinstance(r.result, list):
#             builds.extend([x for x in r.result if isinstance(x, BuildReceipt)])
#         elif isinstance(r.result, BuildReceipt):
#             builds.append(r.result)
#     return PlanningReceipt.summarize(*builds)
#
# from tangl.vm.dispatch import on_get_ns, Namespace as NS
# from tangl.vm.planning import Dependency, Affordance
#
# @on_get_ns()
# def _contribute_deps_to_ns(caller: Node, ctx=None) -> NS:
#     """Build namespace including base vars and satisfied dependencies."""
#     # Automatically include satisfied dependencies/affordances
#     logger.debug(f"Checking deps on caller {caller!r}")
#     dep_names = {}
#     for edge in caller.graph.find_edges(source=caller, is_instance=(Affordance, Dependency)):
#         logger.debug(f"Checking edge sat on edge {edge!r}")
#         if edge.satisfied:
#             dep_names[edge.get_label()] = edge.destination
#     return dep_names

# Prior automatic-accept-first version

# class FrontierPlanner(Behavior):
#
#     def provision_frontier(self, context) -> None:
#         graph = context.graph    # type: Graph
#         cursor = context.anchor  # type: Node
#         ns = context.namespace   # type: StringMap
#         provisioners = context.get_handlers(is_instance=Provisioner)  # type: list[Provisioner]
#
#         # discover open affordances
#         affordances = graph.find_all(is_instance=Affordance, satisfied=False)
#
#         # attach existing affordances first, roles already assigned, etc., they
#         # may satisfy open dependencies
#         for aff in affordances:
#             # try to attach
#             if aff.satisfied_by(cursor):
#                 aff.provider = cursor
#
#         # enumerate frontier deps
#         dependencies = cursor.edges_out(is_instance=Dependency, satisfied=False)  # type: Iterator[Dependency]
#
#         for dep in dependencies:
#             # try to resolve
#             for prov in provisioners:
#                 if prov.can_satisfy(dep):
#                     node = prov.get_satisfier(dep)
#                     dep.provider = node  # adds it automatically
#
#     # This hooks the regular handler call function
#     func = provision_frontier
