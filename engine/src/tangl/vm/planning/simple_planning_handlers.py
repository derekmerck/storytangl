# tangl.vm.planning.simple_planning_handlers.py
"""
Default planning handlers (reference implementation).

The planning phase is wired in three small steps:

1. ``plan_collect_offers`` (EARLY) – enumerate open frontier requirements and
   publish :class:`~tangl.vm.planning.ProvisionOffer` objects.
2. ``plan_select_and_apply`` (LATE) – coalesce offers per requirement, select by
   lowest priority, accept, and return :class:`~tangl.vm.planning.BuildReceipt`.
3. ``plan_compose_receipt`` (LAST) – summarize into a
   :class:`~tangl.vm.planning.PlanningReceipt`.

Domains can register additional builders/selectors at different priorities to
enrich or override behavior.
"""
from uuid import UUID

from tangl.core import Node, Graph, global_domain, JobReceipt
from tangl.vm import ResolutionPhase as P, Context, ProvisioningPolicy
from .open_edge import Dependency, Affordance
from .offer import ProvisionOffer, BuildReceipt, PlanningReceipt
from .provisioning import Provisioner

# todo: lets introduce a sub-phase here: PLANNING_OFFER
#       handlers of type provisioner that want phase_offer and
#       match the selector produce offers, which get processed
#       in the apply step.
#       Provisioners need to implement "get_offers" and include a
#       phase=PLANNING_OFFER selector

# 1) Collect offers (EARLY)
@global_domain.handlers.register(phase=P.PLANNING, priority=25)
def plan_collect_offers(cursor: Node, *, ctx: Context, **kwargs):
    """Publish offers for open :class:`~tangl.vm.planning.open_edge.Dependency` edges."""
    g: Graph = ctx.graph
    offers: list[ProvisionOffer] = []

    # todo: Affordances visible in scope → analogous offers here.
    #       Should do in two passes?, want to accept affordances _before_ looking
    #       for deps, as closest affordance may satisfy deps without relinking
    #       a more distant resource or creating a new one.

    # Dependencies on the frontier
    for e in list(cursor.edges_out(is_instance=Dependency, satisfied=False)):
        prov = Provisioner()
        off = ProvisionOffer(
            label=f"dep:{e.requirement.get_label()}",
            requirement=e.requirement,
            provisioner=prov,
            priority=50,
            operation=ProvisioningPolicy.NOOP,
            selection_criteria={},   # let selectors filter if needed
        )
        offers.append(off)

    return offers

# 2) Select + apply (NORMAL/LATE)
@global_domain.handlers.register(phase=P.PLANNING, priority=75)
def plan_select_and_apply(cursor: Node, *, ctx: Context, **kwargs):
    """Select offers, bind providers, and emit :class:`BuildReceipt` records.

    ``ProvisionOffer.accept`` now returns a provider without side effects. This
    selector performs the binding, updates :attr:`Requirement.is_unresolvable`,
    and constructs receipts summarizing the outcome for each requirement.
    """
    # Gather offers from earlier receipts
    all_offers: list[ProvisionOffer] = []
    for r in ctx.job_receipts:
        if isinstance(r.result, list):
            all_offers.extend([x for x in r.result if isinstance(x, ProvisionOffer)])
        elif isinstance(r.result, ProvisionOffer):
            all_offers.append(r.result)

    # Coalesce by requirement uid
    by_req: dict[UUID, list[ProvisionOffer]] = {}
    for off in all_offers:
        by_req.setdefault(off.requirement.uid, []).append(off)

    builds: list[BuildReceipt] = []
    for req_id, cand in by_req.items():
        # choose lowest priority; then stable by insertion
        cand.sort(key=lambda o: o.priority)
        chosen = cand[0]
        provider = chosen.accept(ctx=ctx)

        if provider is None:
            chosen.requirement.is_unresolvable = True
            builds.append(
                BuildReceipt(
                    provisioner_id=chosen.provisioner.uid,
                    requirement_id=chosen.requirement.uid,
                    provider_id=None,
                    operation=ProvisioningPolicy.NOOP,
                    accepted=False,
                    hard_req=chosen.requirement.hard_requirement,
                    reason='unresolvable',
                )
            )
            continue

        # Successful binding: attach provider and clear prior failures.
        chosen.requirement.provider = provider
        chosen.requirement.is_unresolvable = False
        builds.append(
            BuildReceipt(
                provisioner_id=chosen.provisioner.uid,
                requirement_id=chosen.requirement.uid,
                result=provider.uid,
                operation=chosen.operation or ProvisioningPolicy.NOOP,
                accepted=True,
            )
        )

    return builds

# 3) Compose a PlanningReceipt (LAST)
@global_domain.handlers.register(phase=P.PLANNING, priority=100)
def plan_compose_receipt(cursor: Node, *, ctx: Context, **kwargs):
    """Summarize build receipts into a :class:`~tangl.vm.planning.PlanningReceipt`."""
    builds: list[BuildReceipt] = []
    for r in ctx.job_receipts:
        if isinstance(r.result, list):
            builds.extend([x for x in r.result if isinstance(x, BuildReceipt)])
        elif isinstance(r.result, BuildReceipt):
            builds.append(r.result)
    return PlanningReceipt.summarize(*builds)


# Prior automatic-accept-first version

# class FrontierPlanner(Handler):
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
