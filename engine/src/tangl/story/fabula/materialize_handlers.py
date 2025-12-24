"""Default materialization handlers for StoryTangl."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from tangl.core import Entity
from tangl.core.graph import GraphItem, Node
from tangl.vm.provision import Dependency, ProvisioningPolicy, Requirement
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
    try:
        from tangl.ir.story_ir.scene_script_models import BlockScript
    except ImportError:  # pragma: no cover - defensive import
        BlockScript = None  # type: ignore[assignment]
    if domain_manager is not None:
        cls = domain_manager.resolve_class(template.obj_cls or "tangl.core.graph.Node") or Node
        if cls is Node and getattr(template, "obj_cls", None) is None and hasattr(template, "block_cls"):
            cls = domain_manager.resolve_class(template.block_cls) or Node
        if (
            cls is Node
            and BlockScript is not None
            and isinstance(template, BlockScript)
        ):
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
            world._attach_action_requirements(
                ctx.graph,
                node,
                edge_scripts,
                getattr(template, "scope", None),
            )

    if getattr(template, "roles", None):
        _wire_roles(node=node, roles_data=template.roles, graph=ctx.graph)

    if getattr(template, "settings", None):
        _wire_settings(node=node, settings_data=template.settings, graph=ctx.graph)


def _wire_roles(*, node: Node, roles_data: Any, graph: GraphItem) -> None:
    """Create :class:`Dependency` edges for each role declaration."""

    _wire_dependency(
        node=node,
        specs=roles_data,
        graph=graph,
        default_label="actor",
        ref_key="actor_ref",
        template_key="actor_template_ref",
        criteria_key="actor_criteria",
    )


def _wire_settings(*, node: Node, settings_data: Any, graph: GraphItem) -> None:
    """Create :class:`Dependency` edges for each setting declaration."""

    _wire_dependency(
        node=node,
        specs=settings_data,
        graph=graph,
        default_label="location",
        ref_key="location_ref",
        template_key="location_template_ref",
        criteria_key="location_criteria",
    )


def _wire_dependency(
    *,
    node: Node,
    specs: Any,
    graph: GraphItem,
    default_label: str,
    ref_key: str,
    template_key: str,
    criteria_key: str,
) -> None:
    """Create :class:`Dependency` edges for a homogeneous dependency type."""

    if not specs:
        return

    for label, spec in _iter_specs(specs, default_label=default_label):
        identifier = _get_spec_value(spec, ref_key)
        template_ref = _get_spec_value(spec, template_key)
        criteria = _get_spec_value(spec, criteria_key)

        if identifier is None and template_ref is not None:
            identifier = template_ref

        policy_value = (
            _get_spec_value(spec, "policy")
            or _get_spec_value(spec, "requirement_policy")
            or ProvisioningPolicy.ANY
        )
        policy = (
            ProvisioningPolicy[policy_value.upper()]
            if isinstance(policy_value, str)
            else policy_value
        )

        requirement = Requirement(
            graph=graph,
            identifier=identifier,
            template_ref=template_ref,
            criteria=criteria,
            policy=policy,
            hard_requirement=bool(_get_spec_value(spec, "hard", default=True)),
        )

        Dependency(
            graph=graph,
            source_id=node.uid,
            requirement=requirement,
            label=label,
        )


def _iter_specs(data: Any, *, default_label: str) -> Iterator[tuple[str, Any]]:
    """Yield ``(label, spec)`` pairs from dict or list forms."""

    if isinstance(data, dict):
        for label, spec in data.items():
            yield (label or default_label), spec
        return

    for entry in data:
        if isinstance(entry, dict):
            label = entry.get("label") or default_label
        else:
            label = getattr(entry, "label", None) or default_label
        yield label, entry


def _get_spec_value(spec: Any, key: str, *, default: Any | None = None) -> Any:
    """Retrieve a value from a spec that may be a dict or model object."""

    if isinstance(spec, dict):
        return spec.get(key, default)
    return getattr(spec, key, default)


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
