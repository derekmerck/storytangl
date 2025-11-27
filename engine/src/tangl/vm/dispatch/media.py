from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from tangl.core.graph.node import Node
from tangl.core.behavior import HandlerPriority as Prio
from tangl.media.media_resource.media_provisioning import MediaProvisioner
from tangl.vm import ChoiceEdge, ResolutionPhase as P
from tangl.vm.context import Context
from tangl.vm.dispatch.vm_dispatch import vm_dispatch

if TYPE_CHECKING:  # pragma: no cover - hinting only
    from tangl.story.episode.block import Block
    from tangl.media.media_resource.media_dependency import MediaDep


logger = logging.getLogger(__name__)


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
                rit = resource_manager.get_rit(alias)
                if rit is None:
                    logger.warning(
                        "MediaDep on block %s could not resolve '%s' in world '%s'",
                        block.uid,
                        alias,
                        getattr(world, "name", ""),
                    )
                    continue
                edge.destination = rit
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
