# tangl.vm.dispatch.planning
"""Planning handlers orchestrating provisioning via ``provision_node``."""

from functools import partial
import logging
from uuid import UUID

from tangl.core import Entity, Graph, Node
from tangl.core.behavior import CallReceipt, ContextP, HandlerPriority as Prio
from tangl.core.dispatch import scoped_dispatch
from tangl.vm import ChoiceEdge, Context, ResolutionPhase as P
from tangl.vm.provision import (
    BuildReceipt,
    Dependency,
    PlanningReceipt,
    ProvisionOffer,
    Provisioner,
    ProvisioningContext,
    ProvisioningPlan,
    ProvisioningResult,
    GraphProvisioner,
    TemplateProvisioner,
    UpdatingProvisioner,
    CloningProvisioner,
    provision_node,
)
from .vm_dispatch import vm_dispatch

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

def get_dependencies(*args, **kwargs) -> list[Dependency]:
    return list(Dependency.get_dependencies(*args, **kwargs))

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
    """Return frontier destinations reachable from ``cursor`` via choices."""

    return [
        edge.destination
        for edge in cursor.edges_out(is_instance=ChoiceEdge)
        if edge.destination is not None
    ]


# --------------------------
# Planning phase handlers

on_planning = partial(vm_dispatch.register, task=P.PLANNING)
on_finalize = partial(vm_dispatch.register, task=P.FINALIZE)


@on_planning(priority=Prio.FIRST, label="orchestrate_frontier")
def _planning_orchestrate_frontier(cursor: Node, *, ctx: Context, **_):
    """Provision all frontier nodes using the pure resolver."""

    frontier = _iter_frontier(cursor)

    if not frontier:
        logger.debug("No frontier from %s - provisioning cursor", cursor.label)
        frontier = [cursor]

    provisioners = do_get_provisioners(cursor, ctx=ctx)

    if not provisioners:
        logger.warning("No provisioners available for %s", cursor.label)
        ctx.frontier_provision_results.clear()
        ctx.frontier_provision_plans.clear()
        object.__setattr__(ctx, "planning_indexed_provisioners", [])
        return None

    prov_ctx = ProvisioningContext(
        graph=ctx.graph,
        step=ctx.step,
        rng_seed=getattr(ctx, "rng_seed", None),
    )

    frontier_results: dict[UUID, ProvisioningResult] = {}

    for node in frontier:
        logger.debug("Provisioning frontier node: %s", node.label)

        try:
            result = provision_node(node, provisioners, ctx=prov_ctx)
            frontier_results[node.uid] = result

            total_requirements = (
                result.satisfied_count
                + len(result.unresolved_hard_requirements)
                + len(result.waived_soft_requirements)
            )

            if not result.is_viable:
                logger.debug(
                    "  └─ Frontier node %s is NOT viable: %s unresolved hard requirements",
                    node.label,
                    len(result.unresolved_hard_requirements),
                )
            else:
                logger.debug(
                    "  └─ Frontier node %s is viable: %s/%s requirements satisfied",
                    node.label,
                    result.satisfied_count,
                    total_requirements or 1,
                )

        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Error provisioning %s: %s", node.label, exc, exc_info=True)
            frontier_results[node.uid] = ProvisioningResult(node=node)

    viable_nodes: list[Node] = []
    for node in frontier:
        result = frontier_results.get(node.uid)
        if result is not None and result.is_viable:
            viable_nodes.append(node)

    if not viable_nodes:
        logger.warning(
            "⚠️  SOFTLOCK DETECTED at %s: None of the %s frontier nodes are viable.",
            cursor.label,
            len(frontier),
        )

    ctx.frontier_provision_results.clear()
    ctx.frontier_provision_results.update(frontier_results)
    object.__setattr__(ctx, "planning_indexed_provisioners", list(enumerate(provisioners)))

    return frontier_results


@on_planning(priority=Prio.LATE, label="index_frontier_plans")
def _planning_index_frontier_plans(cursor: Node, *, ctx: Context, **_):
    """Cache primary provisioning plans for the finalize phase."""

    frontier_results = getattr(ctx, "frontier_provision_results", {})

    if not frontier_results:
        logger.debug("No frontier provision results to index")
        ctx.frontier_provision_plans.clear()
        return []

    ctx.frontier_provision_plans.clear()
    plans: list[ProvisioningPlan] = []

    for node_uid, result in frontier_results.items():
        plan = result.primary_plan
        if plan is None:
            continue
        ctx.frontier_provision_plans[node_uid] = plan
        plans.append(plan)

    return plans


@on_finalize(priority=Prio.FIRST, label="apply_frontier_provisions")
def _finalize_apply_frontier_provisions(cursor: Node, *, ctx: Context, **_):
    """Execute cached provisioning plans and record build receipts."""

    frontier_results = getattr(ctx, "frontier_provision_results", {})

    if not frontier_results:
        logger.debug("No frontier provision results to apply")
        ctx.provision_builds.clear()
        return []

    all_builds: list[BuildReceipt] = []

    for node_uid, result in frontier_results.items():
        node = ctx.graph.get(node_uid)
        if node is None:
            logger.warning("Frontier node %s not found in graph", node_uid)
            continue

        plan = ctx.frontier_provision_plans.get(node_uid) or result.primary_plan
        if plan is None:
            logger.debug("No provisioning plan available for %s", node.label)
            continue

        logger.debug("Applying provisions for %s:", node.label)
        receipts = plan.execute(ctx=ctx)
        for receipt in receipts:
            logger.debug("  └─ %s", receipt)
        if receipts:
            if not result.builds:
                result.builds.extend(receipts)
            else:
                for receipt in receipts:
                    if receipt not in result.builds:
                        result.builds.append(receipt)
            all_builds.extend(receipts)

    ctx.provision_builds.clear()
    ctx.provision_builds.extend(all_builds)

    return all_builds


@on_finalize(priority=Prio.LAST, label="generate_planning_receipt")
def _planning_job_receipt(cursor: Node, *, ctx: Context, **_):
    """Summarize planning results into a :class:`PlanningReceipt`."""

    builds = list(getattr(ctx, "provision_builds", []))
    frontier_results = getattr(ctx, "frontier_provision_results", {})

    viable_count = sum(1 for result in frontier_results.values() if result.is_viable)
    softlock_detected = bool(frontier_results) and viable_count == 0
    frontier_node_ids = list(frontier_results.keys())

    unresolved_hard_reqs: list[UUID] = []
    for result in frontier_results.values():
        unresolved_hard_reqs.extend(result.unresolved_hard_requirements)

    waived_soft_requirements: list[UUID] = []
    for result in frontier_results.values():
        waived_soft_requirements.extend(result.waived_soft_requirements)
    if not waived_soft_requirements:
        for build in builds:
            if not build.accepted and not build.hard_req and build.caller_id is not None:
                waived_soft_requirements.append(build.caller_id)
    waived_soft_requirements = list(dict.fromkeys(waived_soft_requirements))

    selection_audit: list[dict[str, object]] = []
    for node_uid, result in frontier_results.items():
        node = ctx.graph.get(node_uid)
        node_label = node.label if node is not None else None
        for req_id, metadata in result.selection_metadata.items():
            entry = {
                "node_id": str(node_uid),
                "node_label": node_label,
                "requirement_uid": metadata.get("requirement_uid", str(req_id)),
                "requirement_label": metadata.get("requirement_label"),
                "reason": metadata.get("reason"),
                "num_offers": metadata.get("num_offers"),
                "selected_cost": metadata.get("selected_cost"),
                "selected_provider_id": metadata.get("selected_provider_id"),
                "all_offers": metadata.get("all_offers", []),
            }
            selection_audit.append(entry)

    receipt = PlanningReceipt(
        cursor_id=cursor.uid,
        frontier_node_ids=frontier_node_ids,
        builds=builds,
        unresolved_hard_requirements=unresolved_hard_reqs,
        waived_soft_requirements=waived_soft_requirements,
        softlock_detected=softlock_detected,
        selection_audit=selection_audit,
    )

    if softlock_detected:
        logger.warning(
            "Planning complete for %s: SOFTLOCK - 0/%s frontier nodes viable",
            cursor.label,
            len(frontier_node_ids),
        )
    else:
        logger.debug(
            "Planning complete for %s: %s/%s frontier nodes viable, %s created, %s attached",
            cursor.label,
            viable_count,
            len(frontier_node_ids),
            receipt.created,
            receipt.attached,
        )

    if hasattr(ctx, "provision_offers"):
        ctx.provision_offers.clear()
    if hasattr(ctx, "provision_builds"):
        ctx.provision_builds.clear()
    if hasattr(ctx, "frontier_provision_results"):
        ctx.frontier_provision_results.clear()
    if hasattr(ctx, "frontier_provision_plans"):
        ctx.frontier_provision_plans.clear()
    object.__setattr__(ctx, "planning_indexed_provisioners", [])

    return receipt


def plan_collect_offers(cursor: Node, *, ctx: Context) -> list[ProvisionOffer]:
    """Compatibility helper returning a flattened list of provision offers."""

    results = _planning_orchestrate_frontier(cursor, ctx=ctx)
    if not results:
        return []

    offers: list[ProvisionOffer] = []
    for result in results.values():
        offers.extend(result.affordance_offers)
        for offer_list in result.dependency_offers.values():
            offers.extend(offer_list)
    return offers


def plan_select_and_apply(cursor: Node, *, ctx: Context) -> list[BuildReceipt]:
    """Compatibility helper returning build receipts after finalize execution."""

    frontier_results = getattr(ctx, "frontier_provision_results", None)
    if not frontier_results:
        frontier_results = _planning_orchestrate_frontier(cursor, ctx=ctx) or {}
        ctx.frontier_provision_results.clear()
        ctx.frontier_provision_results.update(frontier_results)

    _planning_index_frontier_plans(cursor, ctx=ctx)
    builds = _finalize_apply_frontier_provisions(cursor, ctx=ctx)
    return list(builds)
