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

from tangl.core import Node, global_domain, JobReceipt
from tangl.vm import ResolutionPhase as P, Context, ProvisioningPolicy
from .open_edge import Dependency, Affordance
from .offer import ProvisionOffer, BuildReceipt, PlanningReceipt
from .provisioning import Provisioner
from .requirement import Requirement

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
    offers: list[ProvisionOffer] = []

    def provisioners() -> list[Provisioner]:
        discovered = [
            h for h in ctx.get_handlers(is_instance=Provisioner)
            if isinstance(h, Provisioner)
        ]
        has_default = any(isinstance(p, Provisioner) and type(p) is Provisioner for p in discovered)
        if not has_default:
            discovered.append(Provisioner())
        return discovered

    provs = provisioners()

    def _label_for(requirement: Requirement, prefix: str) -> str:
        base = requirement.get_label()
        if not base:
            base = requirement.identifier or requirement.uid.hex[:8]
        return f"{prefix}:{base}"

    def _collect(requirement: Requirement, *, source: str, prefix: str) -> None:
        for prov in provs:
            for offer in prov.get_offers(requirement, ctx=ctx):
                offer.label = offer.label or _label_for(requirement, prefix)
                if "source" not in offer.selection_criteria:
                    offer.selection_criteria = dict(offer.selection_criteria)
                    offer.selection_criteria["source"] = source
                offers.append(offer)

    # Affordances visible in scope should be evaluated before dependencies so
    # existing resources can satisfy requirements without provisioning new ones.
    affordances = sorted(
        (
            edge
            for edge in ctx.scope.find_all(
                is_instance=Affordance,
                destination_id=cursor.uid,
            )
            if edge.requirement.provider is None
        ),
        key=lambda edge: edge.requirement.uid.int,
    )
    for edge in affordances:
        _collect(edge.requirement, source="affordance", prefix="aff")

    # Dependencies on the frontier
    dependencies = sorted(
        (
            edge
            for edge in ctx.scope.find_all(
                is_instance=Dependency,
                source_id=cursor.uid,
            )
            if edge.requirement.provider is None
        ),
        key=lambda edge: edge.requirement.uid.int,
    )
    for edge in dependencies:
        _collect(edge.requirement, source="dependency", prefix="dep")

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

    # Coalesce by requirement uid and remember requirements on the frontier
    offers_by_req: dict[UUID, list[ProvisionOffer]] = {}
    requirements: dict[UUID, Requirement] = {}

    def include_requirement(req: Requirement) -> None:
        requirements.setdefault(req.uid, req)

    for off in all_offers:
        offers_by_req.setdefault(off.requirement.uid, []).append(off)
        include_requirement(off.requirement)

    # Include unresolved frontier requirements even when no offers were published
    for edge in cursor.edges_out(is_instance=Dependency):
        if edge.requirement.provider is not None:
            continue
        include_requirement(edge.requirement)
    for edge in cursor.edges_in(is_instance=Affordance):
        if edge.requirement.provider is not None:
            continue
        include_requirement(edge.requirement)

    # Evaluate requirements in a deterministic order for testability/debuggability.
    ordered_requirements = sorted(
        requirements.values(),
        key=lambda req: req.uid.int,
    )

    builds: list[BuildReceipt] = []
    for requirement in ordered_requirements:
        candidates = offers_by_req.get(requirement.uid, [])

        if requirement.provider is not None and not candidates:
            # Already satisfied and no new offers to evaluate.
            requirement.is_unresolvable = False
            continue

        if not candidates:
            if requirement.hard_requirement:
                requirement.is_unresolvable = True
                builds.append(
                    BuildReceipt(
                        provisioner_id=cursor.uid,
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=True,
                        reason="no_offers",
                    )
                )
            else:
                builds.append(
                    BuildReceipt(
                        provisioner_id=cursor.uid,
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=False,
                        reason="waived_soft",
                    )
                )
            continue

        def _candidate_sort_key(offer: ProvisionOffer) -> tuple[int, int, int]:
            source = (offer.selection_criteria or {}).get("source")
            source_rank = 0 if source == "affordance" else 1
            return (source_rank, offer.priority, offer.uid.int)

        candidates.sort(key=_candidate_sort_key)

        chosen_offer: ProvisionOffer | None = None
        provider: Node | None = None
        for offer in candidates:
            candidate_provider = offer.accept(ctx=ctx)
            if candidate_provider is None:
                continue
            chosen_offer = offer
            provider = candidate_provider
            break

        if provider is None or chosen_offer is None:
            provisioner_id = (
                candidates[0].provisioner.uid if candidates else cursor.uid
            )
            if requirement.hard_requirement:
                requirement.is_unresolvable = True
                builds.append(
                    BuildReceipt(
                        provisioner_id=provisioner_id,
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=True,
                        reason="unresolvable",
                    )
                )
            else:
                builds.append(
                    BuildReceipt(
                        provisioner_id=provisioner_id,
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=False,
                        reason="waived_soft",
                    )
                )
            continue

        # Successful binding: attach provider and clear any prior failures.
        requirement.provider = provider
        if requirement.hard_requirement:
            requirement.is_unresolvable = False

        builds.append(
            BuildReceipt(
                provisioner_id=chosen_offer.provisioner.uid,
                requirement_id=requirement.uid,
                provider_id=provider.uid,
                operation=chosen_offer.operation or ProvisioningPolicy.NOOP,
                accepted=True,
                hard_req=requirement.hard_requirement,
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
