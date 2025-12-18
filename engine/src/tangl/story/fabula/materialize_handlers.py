"""Default materialization handlers for StoryTangl."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tangl.core import Entity
from tangl.core.graph import GraphItem, Node
from tangl.vm.dispatch import vm_dispatch
from tangl.vm.dispatch.materialize_task import MaterializePhase, MaterializeTask

if TYPE_CHECKING:  # pragma: no cover - import-time registration only
    from tangl.story.fabula.world import World
    from tangl.vm.context import MaterializationContext


@vm_dispatch.register(
    task=MaterializeTask.MATERIALIZE,
    priority=MaterializePhase.NORMAL,
)
def instantiation_handler(
    caller: Entity,
    *,
    ctx: "MaterializationContext",
    **_: Any,
) -> Node | None:
    """NORMAL phase handler: create the graph item from the template payload."""

    template = ctx.template
    graph = ctx.graph
    world: "World | None" = getattr(graph, "world", None)
    domain_manager = getattr(world, "domain_manager", None)

    cls: type[Any] = Node
    if domain_manager is not None:
        cls = domain_manager.resolve_class(template.obj_cls or "tangl.core.graph.Node") or Node
        if cls is Node and getattr(template, "obj_cls", None) is None and hasattr(template, "block_cls"):
            cls = domain_manager.resolve_class(template.block_cls) or Node
        if cls is Node and template.__class__.__name__ == "BlockScript":
            cls = domain_manager.resolve_class("tangl.story.episode.block.Block") or Node
    else:
        obj_cls = getattr(template, "obj_cls", None)
        if isinstance(obj_cls, type):
            cls = obj_cls

    wirable_fields = ("actions", "continues", "redirects", "media", "roles", "settings")
    drop_keys = tuple(field for field in wirable_fields if getattr(template, field, None))

    payload = ctx.payload or {}
    prepared = _prepare_payload(world, cls, payload, graph, drop_keys)
    prepared.setdefault("label", template.label)

    node = cls.structure(prepared)
    if ctx.parent_container is not None:
        ctx.parent_container.add_member(node)
    else:
        graph.add(node)

    ctx.payload = prepared
    ctx.node = node
    return node


@vm_dispatch.register(
    task=MaterializeTask.MATERIALIZE,
    priority=MaterializePhase.LATE,
)
def standard_wiring_handler(
    caller: Entity,
    *,
    ctx: "MaterializationContext",
    **_: Any,
) -> None:
    """LATE phase handler: wire StoryTangl dependencies for the created node."""

    node = ctx.node
    if node is None:
        return

    world: "World | None" = getattr(ctx.graph, "world", None)
    if world is None:
        return

    template = ctx.template

    # Persist BlockScript lookup
    try:
        from tangl.ir.story_ir.scene_script_models import BlockScript
    except Exception:  # pragma: no cover - defensive
        BlockScript = None  # type: ignore[assignment]

    if BlockScript is not None and isinstance(template, BlockScript):
        world._block_scripts[node.uid] = template

    if getattr(template, "media", None):
        from tangl.story.fabula.media import attach_media_deps_for_block

        attach_media_deps_for_block(ctx.graph, node, template)

    for edge_type in ("actions", "continues", "redirects"):
        edge_scripts = getattr(template, edge_type, None)
        if edge_scripts:
            world._attach_action_requirements(ctx.graph, node, edge_scripts, template.scope)

    if getattr(template, "roles", None):
        world._wire_roles(
            graph=ctx.graph,
            source_node=node,
            roles_data=template.roles,
            actor_map={},
        )

    if getattr(template, "settings", None):
        world._wire_settings(
            graph=ctx.graph,
            source_node=node,
            settings_data=template.settings,
            location_map={},
        )


def _prepare_payload(
    world: "World | None",
    cls: type[Any],
    payload: dict[str, Any],
    graph: GraphItem,
    drop_keys: tuple[str, ...],
) -> dict[str, Any]:
    if world is not None:
        return world._prepare_payload(cls, payload, graph, drop_keys=drop_keys)

    filtered = {key: value for key, value in payload.items() if key not in drop_keys}
    if _is_graph_item(cls):
        filtered["graph"] = graph
    else:
        filtered.pop("graph", None)
    return filtered


def _is_graph_item(cls: type[Any]) -> bool:
    try:
        return issubclass(cls, GraphItem)
    except TypeError:  # pragma: no cover - defensive fallback
        return False

