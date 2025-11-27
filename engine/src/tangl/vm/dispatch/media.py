from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from tangl.core.graph.node import Node
from tangl.core.behavior import HandlerPriority as Prio
from tangl.core.behavior import CallReceipt
from tangl.media.dispatch import MediaTask, media_dispatch
from tangl.media.media_resource.media_provisioning import MediaProvisioner
from tangl.vm import ChoiceEdge, ResolutionPhase as P
from tangl.vm.context import Context
from tangl.vm.dispatch.vm_dispatch import vm_dispatch

if TYPE_CHECKING:  # pragma: no cover - hinting only
    from tangl.story.episode.block import Block
    from tangl.media.media_resource.media_dependency import MediaDep


logger = logging.getLogger(__name__)


@vm_dispatch.register(task=P.INIT, priority=Prio.EARLY)
def attach_system_media_manager(cursor: Node, *, ctx: Context, **_: Any) -> None:
    """Attach the shared system media manager to the world if available."""

    world = getattr(ctx.graph, "world", None)
    if world is None:
        return

    if getattr(world, "system_resource_manager", None) is not None:
        return

    receipts = list(
        media_dispatch.dispatch(
            task=MediaTask.GET_SYSTEM_RESOURCE_MANAGER,
            caller=world,
            ctx=ctx,
        )
    )
    system_manager = CallReceipt.first_result(*receipts)
    if system_manager is not None:
        world.system_resource_manager = system_manager


def _iter_frontier_blocks(cursor: Node) -> list[Block]:
    """Return frontier block destinations reachable from ``cursor`` choices."""

    from tangl.story.episode.block import Block  # local import to avoid cycles

    return [
        edge.destination
        for edge in cursor.edges_out(is_instance=ChoiceEdge)
        if isinstance(edge.destination, Block)
    ]


def _media_dep_alias_from_requirement(dep: MediaDep) -> str | None:
    requirement = getattr(dep, "requirement", None)
    criteria = getattr(requirement, "criteria", None)
    if isinstance(criteria, dict) and "path" in criteria:
        return str(criteria["path"])
    return None


def media_dep_kind(dep: MediaDep) -> str:
    """Classify the dependency based on available requirement data."""

    requirement = dep.requirement
    criteria = getattr(requirement, "criteria", None)
    template = getattr(requirement, "template", None) or {}

    if isinstance(criteria, dict) and "path" in criteria:
        return "path"
    if "data" in template or "spec" in template:
        return "template"
    if getattr(requirement, "identifier", None) is not None:
        return "id"
    return "unknown"


@vm_dispatch.register(task=P.PLANNING, priority=Prio.NORMAL)
def plan_media(cursor: Node, *, ctx: Context, **_: Any) -> None:
    """Bind or provision media dependencies during planning."""

    from tangl.story.episode.block import Block  # local import to avoid cycles
    from tangl.media.media_resource.media_dependency import MediaDep

    world = getattr(ctx.graph, "world", None)
    resource_manager = getattr(world, "resource_manager", None)
    if resource_manager is None:
        return

    frontier_blocks = _iter_frontier_blocks(cursor)
    if not frontier_blocks and isinstance(cursor, Block):
        frontier_blocks = [cursor]

    for block in frontier_blocks:
        for edge in block.edges_out():
            if not isinstance(edge, MediaDep) or edge.destination is not None:
                continue

            kind = media_dep_kind(edge)
            if kind == "path":
                alias = _media_dep_alias_from_requirement(edge)
                if alias is None:
                    continue
                managers = [(resource_manager, "world")]
                system_manager = getattr(world, "system_resource_manager", None)
                if system_manager is not None:
                    managers.append((system_manager, "sys"))

                resolved = None
                for manager, scope in managers:
                    rit = manager.get_rit(alias) if manager is not None else None
                    if rit is None:
                        continue
                    resolved = rit
                    edge.scope = scope
                    break

                if resolved is None:
                    logger.warning(
                        "MediaDep on block %s could not resolve '%s' in available registries",
                        block.uid,
                        alias,
                    )
                    continue

                edge.destination = resolved
                continue

            if kind in {"template", "id"}:
                provisioner = MediaProvisioner(
                    requirement=edge.requirement,
                    registries=[resource_manager.registry],
                )
                offers = provisioner.generate_offers(ctx=ctx)
                for offer in offers:
                    provider = offer.accept(ctx=ctx)
                    if provider is None:
                        continue
                    edge.destination = provider
                    break
