from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field, replace
from html import escape
import json
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterable, Mapping

from tangl.core import Edge, EntityTemplate, Node, Selector, TemplateRegistry
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.vm import Dependency, Fanout, ResolutionPhase, TraversableEdge, TraversableNode

from .concepts import Actor, Location, Role, Setting
from .episode import Action, Block, Scene
from .fabula import InitMode, World, WorldBuilder
from .fabula.compiler import StoryTemplateBundle
from .story_graph import StoryGraph


ProjectedGraphProcessor = Callable[["ProjectedGraph"], "ProjectedGraph"]
NodeStylePolicy = Callable[["ProjectedNode", Any | None], Mapping[str, object] | None]


@dataclass(slots=True)
class ProjectedNode:
    id: str
    label: str
    source_id: str | None
    source_kind: str | None
    attrs: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ProjectedEdge:
    id: str
    source_id: str
    target_id: str
    label: str
    source_edge_id: str | None
    source_kind: str | None
    edge_role: str
    attrs: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ProjectedGroup:
    id: str
    label: str
    group_kind: str
    member_node_ids: list[str]
    source_id: str | None
    source_kind: str | None
    attrs: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ProjectedGraph:
    nodes: list[ProjectedNode]
    edges: list[ProjectedEdge]
    groups: list[ProjectedGroup]
    _source_nodes_by_id: dict[str, Any] = field(default_factory=dict, repr=False)
    _source_edges_by_id: dict[str, Any] = field(default_factory=dict, repr=False)
    _projected_node_id_by_source_id: dict[str, str] = field(default_factory=dict, repr=False)


@dataclass(slots=True)
class ScriptGraphNode:
    id: str
    label: str
    kind: str
    gate_type: str | None
    scene_id: str | None
    is_entry: bool
    is_terminal: bool


@dataclass(slots=True)
class ScriptGraphEdge:
    source_id: str
    target_id: str
    kind: str
    label: str


@dataclass(slots=True)
class ScriptGraphReport:
    nodes: list[ScriptGraphNode]
    edges: list[ScriptGraphEdge]


@dataclass(slots=True)
class _ProjectionContext:
    graph: StoryGraph
    template_registry: TemplateRegistry | None
    template_by_hash: dict[bytes, EntityTemplate]


@dataclass(slots=True)
class _NodeSeed:
    source: Node
    label: str
    source_id: str
    source_kind: str
    template_label: str | None
    path: str | None


@dataclass(slots=True)
class _EdgeSeed:
    source: Edge
    source_id: str
    source_kind: str
    template_label: str | None
    predecessor_id: str
    successor_id: str
    label: str
    edge_role: str


_GATE_COLORS: dict[str | None, str] = {
    "INPUT": "#f5d90a",
    "OUTPUT": "#3ac47d",
    "XOR": "#4f83ff",
    "AND": "#ff8c42",
    "OR": "#d946ef",
    None: "#9aa4b2",
}


def structural_selector() -> Selector:
    """Return the default structural source-graph selector."""

    return Selector.chain_or(
        Selector(has_kind=TraversableNode),
        Selector(has_kind=TraversableEdge),
    )


def episode_only_selector() -> Selector:
    """Return one selector limited to episode nodes and traversal edges."""

    return Selector.chain_or(
        Selector(has_kind=Scene),
        Selector(has_kind=Block),
        Selector(has_kind=Action),
    )


def episode_plus_concepts_selector() -> Selector:
    """Return one selector that adds concept/provider structure to episode views."""

    return Selector.chain_or(
        structural_selector(),
        Selector(has_kind=Actor),
        Selector(has_kind=Location),
        Selector(has_kind=Role),
        Selector(has_kind=Setting),
    )


def project_story_graph(
    graph: StoryGraph,
    *,
    selector: Selector | None = None,
    node_selector: Selector | None = None,
    edge_selector: Selector | None = None,
    processors: Iterable[ProjectedGraphProcessor] = (),
) -> ProjectedGraph:
    """Project one live :class:`StoryGraph` into a filtered deterministic graph view."""

    if graph.template_registry is not None and (
        not graph.template_by_entity_id or not graph.template_lineage_by_entity_id
    ):
        graph.rebuild_template_lineage()

    resolved_selector = selector or structural_selector()
    selected_items = list(graph.find_all(selector=resolved_selector))

    node_candidates = [item for item in selected_items if isinstance(item, Node)]
    edge_candidates = [item for item in selected_items if isinstance(item, Edge)]

    if node_selector is not None:
        node_candidates = list(node_selector.filter(node_candidates))
    if edge_selector is not None:
        edge_candidates = list(edge_selector.filter(edge_candidates))

    context = _projection_context(graph)
    projected = _project_selected_items(
        context=context,
        node_candidates=node_candidates,
        edge_candidates=edge_candidates,
    )

    for processor in processors:
        projected = processor(projected)
    return _sorted_projected_graph(projected)


def project_world_graph(
    world: World,
    *,
    selector: Selector | None = None,
    node_selector: Selector | None = None,
    edge_selector: Selector | None = None,
    processors: Iterable[ProjectedGraphProcessor] = (),
    story_label: str = "projection_inspection",
) -> ProjectedGraph:
    """Project one world by first creating an eager frozen inspection story."""

    graph = _make_projection_story(world=world, story_label=story_label)
    return project_story_graph(
        graph,
        selector=selector,
        node_selector=node_selector,
        edge_selector=edge_selector,
        processors=processors,
    )


def cluster_by_scene() -> ProjectedGraphProcessor:
    """Return one processor that adds scene cluster groups."""

    def processor(projected_graph: ProjectedGraph) -> ProjectedGraph:
        grouped: dict[str, dict[str, Any]] = {}
        for node in projected_graph.nodes:
            source = projected_graph._source_nodes_by_id.get(node.id)
            scene = _runtime_scene_for_node(source)
            if scene is None:
                continue

            group_id = _scene_group_id(scene=scene, projected_graph=projected_graph)
            bucket = grouped.setdefault(
                group_id,
                {
                    "label": getattr(scene, "title", None) or scene.get_label(),
                    "member_node_ids": [],
                    "source_id": _stringify_identifier(getattr(scene, "uid", None)),
                    "source_kind": _qualified_kind(scene),
                },
            )
            if node.id not in bucket["member_node_ids"]:
                bucket["member_node_ids"].append(node.id)

        if not grouped:
            return projected_graph

        groups = list(projected_graph.groups)
        for group_id in sorted(grouped):
            bucket = grouped[group_id]
            groups.append(
                ProjectedGroup(
                    id=group_id,
                    label=bucket["label"],
                    group_kind="cluster",
                    member_node_ids=sorted(bucket["member_node_ids"]),
                    source_id=bucket["source_id"],
                    source_kind=bucket["source_kind"],
                    attrs={},
                )
            )
        return _replace_projected_graph(projected_graph, groups=groups)

    return processor


def attach_media_preview(media_role: str | None = None) -> ProjectedGraphProcessor:
    """Return one processor that annotates nodes with previewable media paths."""

    def processor(projected_graph: ProjectedGraph) -> ProjectedGraph:
        updated_nodes: list[ProjectedNode] = []
        changed = False
        for node in projected_graph.nodes:
            source = projected_graph._source_nodes_by_id.get(node.id)
            preview_attrs = _preview_attrs_for_source_node(source=source, media_role=media_role)
            if not preview_attrs:
                updated_nodes.append(node)
                continue
            attrs = dict(node.attrs)
            attrs.update(preview_attrs)
            updated_nodes.append(replace(node, attrs=attrs))
            changed = True
        if not changed:
            return projected_graph
        return _replace_projected_graph(projected_graph, nodes=updated_nodes)

    return processor


def mark_node_styles(style_policy: NodeStylePolicy) -> ProjectedGraphProcessor:
    """Return one processor that annotates projected nodes with style attrs."""

    def processor(projected_graph: ProjectedGraph) -> ProjectedGraph:
        updated_nodes: list[ProjectedNode] = []
        changed = False
        for node in projected_graph.nodes:
            source = projected_graph._source_nodes_by_id.get(node.id)
            additions = dict(style_policy(node, source) or {})
            if not additions:
                updated_nodes.append(node)
                continue

            attrs = dict(node.attrs)
            for key, value in sorted(additions.items()):
                if value is None:
                    continue
                attrs[key] = value
            updated_nodes.append(replace(node, attrs=attrs))
            changed = True
        if not changed:
            return projected_graph
        return _replace_projected_graph(projected_graph, nodes=updated_nodes)

    return processor


def to_dot(projected_graph: ProjectedGraph, *, include_groups: bool = True) -> str:
    """Return one deterministic DOT script for a projected graph."""

    node_by_id = {node.id: node for node in projected_graph.nodes}
    lines = [
        "digraph tangl {",
        '  graph [rankdir="LR", bgcolor="#f8fafc"];',
        '  node [fontname="monospace", shape="box", style="rounded"];',
        '  edge [fontname="monospace"];',
    ]

    emitted_node_ids: set[str] = set()
    if include_groups:
        for group in projected_graph.groups:
            member_ids = [node_id for node_id in group.member_node_ids if node_id in node_by_id]
            if not member_ids:
                continue

            subgraph_id = f"cluster_{group.id}" if group.group_kind == "cluster" else group.id
            lines.append(f"  subgraph {_dot_quote(subgraph_id)} {{")
            for attr_name, attr_value in _dot_group_attrs(group).items():
                lines.append(f"    {attr_name}={_dot_quote(attr_value)};")
            for node_id in member_ids:
                emitted_node_ids.add(node_id)
                lines.append(f"    {_dot_node_statement(node_by_id[node_id])}")
            lines.append("  }")

    for node in projected_graph.nodes:
        if node.id in emitted_node_ids:
            continue
        lines.append(f"  {_dot_node_statement(node)}")

    for edge in projected_graph.edges:
        lines.append(f"  {_dot_edge_statement(edge)}")

    lines.append("}")
    return "\n".join(lines)


def render_dot(dot_text: str, *, prog: str = "dot", format: str = "svg") -> bytes:
    """Render DOT text through a local Graphviz executable."""

    try:
        result = subprocess.run(
            [prog, f"-T{format}"],
            input=dot_text.encode("utf-8"),
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Graphviz program {prog!r} is not available") from exc

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Graphviz {prog!r} failed: {stderr}")
    return result.stdout


def projected_graph_to_dict(projected_graph: ProjectedGraph) -> dict[str, object]:
    """Return one JSON-safe dictionary representation of a projected graph."""

    return {
        "nodes": [
            {
                "id": node.id,
                "label": node.label,
                "source_id": node.source_id,
                "source_kind": node.source_kind,
                "attrs": dict(node.attrs),
            }
            for node in projected_graph.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "label": edge.label,
                "source_edge_id": edge.source_edge_id,
                "source_kind": edge.source_kind,
                "edge_role": edge.edge_role,
                "attrs": dict(edge.attrs),
            }
            for edge in projected_graph.edges
        ],
        "groups": [
            {
                "id": group.id,
                "label": group.label,
                "group_kind": group.group_kind,
                "member_node_ids": list(group.member_node_ids),
                "source_id": group.source_id,
                "source_kind": group.source_kind,
                "attrs": dict(group.attrs),
            }
            for group in projected_graph.groups
        ],
    }


def build_script_report(bundle_or_world: StoryTemplateBundle | World) -> ScriptGraphReport:
    """Return the phase-1 compatibility block report via live graph projection."""

    world = _coerce_world(bundle_or_world)
    graph = _make_projection_story(world=world, story_label="script_report_inspection")
    projected = project_story_graph(
        graph,
        selector=episode_only_selector(),
        node_selector=Selector(has_kind=Block),
        edge_selector=Selector(has_kind=Action),
    )

    entry_ids = {str(cursor_id) for cursor_id in graph.initial_cursor_ids}
    outgoing_by_id: dict[str, int] = defaultdict(int)
    for edge in projected.edges:
        outgoing_by_id[edge.source_id] += 1

    nodes: list[ScriptGraphNode] = []
    for node in projected.nodes:
        source = projected._source_nodes_by_id.get(node.id)
        kind = source.__class__.__name__ if source is not None else "Node"
        nodes.append(
            ScriptGraphNode(
                id=node.id,
                label=node.label,
                kind=kind,
                gate_type=_gate_type(source),
                scene_id=_runtime_scene_id(source),
                is_entry=node.source_id in entry_ids,
                is_terminal=outgoing_by_id.get(node.id, 0) == 0,
            )
        )

    edges = [
        ScriptGraphEdge(
            source_id=edge.source_id,
            target_id=edge.target_id,
            kind=_compat_edge_kind(edge.edge_role),
            label=edge.label,
        )
        for edge in projected.edges
    ]
    return ScriptGraphReport(nodes=nodes, edges=edges)


def report_to_dict(report: ScriptGraphReport | ProjectedGraph) -> dict[str, object]:
    """Return one JSON-safe dictionary for a compatibility report or projection."""

    if isinstance(report, ProjectedGraph):
        return projected_graph_to_dict(report)

    return {
        "nodes": [
            {
                "id": node.id,
                "label": node.label,
                "kind": node.kind,
                "gate_type": node.gate_type,
                "scene_id": node.scene_id,
                "is_entry": node.is_entry,
                "is_terminal": node.is_terminal,
            }
            for node in report.nodes
        ],
        "edges": [
            {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "kind": edge.kind,
                "label": edge.label,
            }
            for edge in report.edges
        ],
    }


def render_basic_svg(report: ScriptGraphReport) -> str:
    """Render one phase-1 compatibility report as a deterministic inspection SVG."""

    if not report.nodes:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="120" viewBox="0 0 240 120">'
            '<rect x="0" y="0" width="240" height="120" fill="#f8fafc"/>'
            '<text x="120" y="60" text-anchor="middle" font-family="monospace" '
            'font-size="14" fill="#102a43">empty graph</text>'
            "</svg>"
        )

    positions = _layout_positions(report)
    node_width = 140
    node_height = 56
    pad_x = 48
    pad_y = 40

    max_x = max(x for x, _y in positions.values()) + node_width + pad_x
    max_y = max(y for _x, y in positions.values()) + node_height + pad_y

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{max_x}" height="{max_y}" '
            f'viewBox="0 0 {max_x} {max_y}">'
        ),
        f'<rect x="0" y="0" width="{max_x}" height="{max_y}" fill="#f8fafc"/>',
    ]

    node_by_id = {node.id: node for node in report.nodes}
    for edge in report.edges:
        source_x, source_y = positions[edge.source_id]
        target_x, target_y = positions[edge.target_id]
        x1 = source_x + node_width
        y1 = source_y + (node_height / 2)
        x2 = target_x
        y2 = target_y + (node_height / 2)
        label = escape(edge.label or edge.kind)
        parts.append(
            (
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#486581" '
                'stroke-width="2" marker-end="url(#arrow)"/>'
            )
        )
        if label:
            mid_x = (x1 + x2) / 2
            mid_y = ((y1 + y2) / 2) - 6
            parts.append(
                (
                    f'<text x="{mid_x}" y="{mid_y}" text-anchor="middle" font-family="monospace" '
                    f'font-size="10" fill="#334e68">{label}</text>'
                )
            )

    parts.insert(
        2,
        (
            "<defs>"
            '<marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">'
            '<polygon points="0 0, 10 3.5, 0 7" fill="#486581"/>'
            "</marker>"
            "</defs>"
        ),
    )

    for node in sorted(report.nodes, key=lambda item: (positions[item.id][0], positions[item.id][1], item.id)):
        x, y = positions[node.id]
        gate_type = node.gate_type
        fill = _GATE_COLORS.get(gate_type, _GATE_COLORS[None])
        shape = _shape_name(gate_type)
        parts.append(
            (
                f'<g class="node" data-node-id="{escape(node.id)}" '
                f'data-gate-type="{escape(gate_type or "")}" data-node-shape="{shape}">'
            )
        )
        parts.append(_shape_svg(shape=shape, x=x, y=y, width=node_width, height=node_height, fill=fill))
        parts.append(
            (
                f'<text x="{x + (node_width / 2)}" y="{y + 24}" text-anchor="middle" '
                'font-family="monospace" font-size="12" fill="#102a43">'
                f"{escape(node.label)}</text>"
            )
        )
        parts.append(
            (
                f'<text x="{x + (node_width / 2)}" y="{y + 42}" text-anchor="middle" '
                'font-family="monospace" font-size="10" fill="#243b53">'
                f"{escape(gate_type or node.kind)}</text>"
            )
        )
        parts.append("</g>")

    parts.append("</svg>")
    return "".join(parts)


def _projection_context(graph: StoryGraph) -> _ProjectionContext:
    template_registry = graph.template_registry
    template_by_hash: dict[bytes, EntityTemplate] = {}
    if template_registry is not None:
        for template in template_registry.values():
            if isinstance(template, EntityTemplate):
                template_by_hash[template.content_hash()] = template
    return _ProjectionContext(
        graph=graph,
        template_registry=template_registry,
        template_by_hash=template_by_hash,
    )


def _project_selected_items(
    *,
    context: _ProjectionContext,
    node_candidates: list[Node],
    edge_candidates: list[Edge],
) -> ProjectedGraph:
    node_seeds = [_node_seed(node=node, context=context) for node in node_candidates]
    node_seeds.sort(key=_node_seed_sort_key)

    projected_nodes: list[ProjectedNode] = []
    source_nodes_by_id: dict[str, Any] = {}
    projected_node_id_by_source_id: dict[str, str] = {}
    node_counts: dict[str, int] = defaultdict(int)

    for seed in node_seeds:
        base_id = _node_base_id(seed)
        node_counts[base_id] += 1
        projected_id = base_id if node_counts[base_id] == 1 else f"{base_id}:{node_counts[base_id]}"
        projected_node = ProjectedNode(
            id=projected_id,
            label=seed.label,
            source_id=seed.source_id,
            source_kind=seed.source_kind,
            attrs={},
        )
        projected_nodes.append(projected_node)
        source_nodes_by_id[projected_id] = seed.source
        projected_node_id_by_source_id[seed.source_id] = projected_id

    edge_seeds: list[_EdgeSeed] = []
    for edge in edge_candidates:
        predecessor = edge.predecessor
        successor = edge.successor
        if predecessor is None or successor is None:
            continue
        predecessor_id = projected_node_id_by_source_id.get(_stringify_identifier(predecessor.uid))
        successor_id = projected_node_id_by_source_id.get(_stringify_identifier(successor.uid))
        if predecessor_id is None or successor_id is None:
            continue
        edge_seeds.append(
            _EdgeSeed(
                source=edge,
                source_id=_stringify_identifier(edge.uid),
                source_kind=_qualified_kind(edge),
                template_label=_template_label_for_entity(entity=edge, context=context),
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                label=_edge_label(edge),
                edge_role=_edge_role(edge),
            )
        )

    edge_seeds.sort(key=_edge_seed_sort_key)
    projected_edges: list[ProjectedEdge] = []
    source_edges_by_id: dict[str, Any] = {}
    edge_counts: dict[str, int] = defaultdict(int)
    for seed in edge_seeds:
        base_id = f"{seed.predecessor_id}:{seed.edge_role}:{seed.successor_id}"
        edge_counts[base_id] += 1
        edge_id = base_id if edge_counts[base_id] == 1 else f"{base_id}:{edge_counts[base_id]}"
        projected_edge = ProjectedEdge(
            id=edge_id,
            source_id=seed.predecessor_id,
            target_id=seed.successor_id,
            label=seed.label,
            source_edge_id=seed.source_id,
            source_kind=seed.source_kind,
            edge_role=seed.edge_role,
            attrs={},
        )
        projected_edges.append(projected_edge)
        source_edges_by_id[edge_id] = seed.source

    return ProjectedGraph(
        nodes=projected_nodes,
        edges=projected_edges,
        groups=[],
        _source_nodes_by_id=source_nodes_by_id,
        _source_edges_by_id=source_edges_by_id,
        _projected_node_id_by_source_id=projected_node_id_by_source_id,
    )


def _replace_projected_graph(
    projected_graph: ProjectedGraph,
    *,
    nodes: list[ProjectedNode] | None = None,
    edges: list[ProjectedEdge] | None = None,
    groups: list[ProjectedGroup] | None = None,
) -> ProjectedGraph:
    return ProjectedGraph(
        nodes=list(projected_graph.nodes if nodes is None else nodes),
        edges=list(projected_graph.edges if edges is None else edges),
        groups=list(projected_graph.groups if groups is None else groups),
        _source_nodes_by_id=dict(projected_graph._source_nodes_by_id),
        _source_edges_by_id=dict(projected_graph._source_edges_by_id),
        _projected_node_id_by_source_id=dict(projected_graph._projected_node_id_by_source_id),
    )


def _sorted_projected_graph(projected_graph: ProjectedGraph) -> ProjectedGraph:
    nodes = sorted(projected_graph.nodes, key=lambda node: (node.id, node.label, node.source_kind or ""))
    edges = sorted(
        projected_graph.edges,
        key=lambda edge: (edge.source_id, edge.target_id, edge.edge_role, edge.label, edge.id),
    )
    groups = sorted(
        projected_graph.groups,
        key=lambda group: (group.group_kind, group.label, group.id),
    )
    return _replace_projected_graph(projected_graph, nodes=nodes, edges=edges, groups=groups)


def _node_seed(node: Node, *, context: _ProjectionContext) -> _NodeSeed:
    label = node.get_label() if hasattr(node, "get_label") else _qualified_kind(node).rsplit(".", 1)[-1]
    return _NodeSeed(
        source=node,
        label=label,
        source_id=_stringify_identifier(getattr(node, "uid", None)),
        source_kind=_qualified_kind(node),
        template_label=_template_label_for_entity(entity=node, context=context),
        path=_path_for_entity(node),
    )


def _node_seed_sort_key(seed: _NodeSeed) -> tuple[int, str, str, str, str, str]:
    return (
        0 if seed.template_label is not None else 1,
        seed.template_label or "",
        seed.path or "",
        seed.source_kind,
        seed.label,
        seed.source_id,
    )


def _node_base_id(seed: _NodeSeed) -> str:
    if seed.template_label:
        return seed.template_label
    if seed.path:
        return seed.path
    if seed.label:
        return seed.label
    return seed.source_id


def _edge_seed_sort_key(seed: _EdgeSeed) -> tuple[int, str, str, str, str, str, str]:
    return (
        0 if seed.template_label is not None else 1,
        seed.template_label or "",
        seed.predecessor_id,
        seed.successor_id,
        seed.edge_role,
        seed.label,
        seed.source_id,
    )


def _template_label_for_entity(*, entity: Any, context: _ProjectionContext) -> str | None:
    entity_uid = getattr(entity, "uid", None)
    if entity_uid is None or context.template_registry is None:
        return None

    template_uid = context.graph.template_by_entity_id.get(entity_uid)
    if template_uid is not None:
        template = context.template_registry.get(template_uid)
        if isinstance(template, EntityTemplate):
            return template.get_label()

    lineage = context.graph.template_lineage_by_entity_id.get(entity_uid, [])
    for template_uid in lineage:
        template = context.template_registry.get(template_uid)
        if isinstance(template, EntityTemplate):
            return template.get_label()

    templ_hash = getattr(entity, "templ_hash", None)
    if isinstance(templ_hash, bytes):
        template = context.template_by_hash.get(templ_hash)
        if isinstance(template, EntityTemplate):
            return template.get_label()
    return None


def _qualified_kind(value: Any) -> str | None:
    if value is None:
        return None
    cls = value if isinstance(value, type) else value.__class__
    return f"{cls.__module__}.{cls.__qualname__}"


def _stringify_identifier(value: Any) -> str:
    return "" if value is None else str(value)


def _path_for_entity(entity: Any) -> str | None:
    path = getattr(entity, "path", None)
    if isinstance(path, str) and path:
        return path
    return None


def _edge_label(edge: Edge) -> str:
    if isinstance(edge, Action):
        return edge.text or edge.get_label() or ""
    return edge.get_label() if hasattr(edge, "get_label") else ""


def _edge_role(edge: Edge) -> str:
    if isinstance(edge, Action):
        if edge.trigger_phase is None:
            return "choice"
        if edge.trigger_phase == ResolutionPhase.PREREQS:
            return "redirect"
        if edge.trigger_phase == ResolutionPhase.POSTREQS:
            return "continue"
    if isinstance(edge, MediaDep):
        return "media"
    if isinstance(edge, Fanout):
        return "fanout"
    if isinstance(edge, (Role, Setting, Dependency)):
        return "dependency"
    return "edge"


def _runtime_scene_for_node(node: Any) -> Scene | None:
    current = node
    while current is not None:
        if isinstance(current, Scene):
            return current
        current = getattr(current, "parent", None)
    return None


def _runtime_scene_id(node: Any) -> str | None:
    scene = _runtime_scene_for_node(node)
    if scene is None:
        return None
    return scene.get_label()


def _scene_group_id(*, scene: Scene, projected_graph: ProjectedGraph) -> str:
    source_id = _stringify_identifier(scene.uid)
    projected_id = projected_graph._projected_node_id_by_source_id.get(source_id)
    if projected_id is not None:
        return f"scene:{projected_id}"

    template_registry = getattr(getattr(scene, "graph", None), "template_registry", None)
    context = _ProjectionContext(
        graph=scene.graph,
        template_registry=template_registry,
        template_by_hash={},
    )
    template_label = _template_label_for_entity(entity=scene, context=context)
    if template_label:
        return f"scene:{template_label}"
    path = _path_for_entity(scene)
    if path:
        return f"scene:{path}"
    return f"scene:{scene.get_label()}"


def _preview_attrs_for_source_node(*, source: Any, media_role: str | None) -> dict[str, object]:
    if source is None or not hasattr(source, "edges_out"):
        return {}

    deps = sorted(
        source.edges_out(Selector(has_kind=MediaDep)),
        key=lambda dep: (dep.get_label(), _stringify_identifier(dep.uid)),
    )
    for dep in deps:
        if media_role is not None and getattr(dep, "media_role", None) != media_role:
            continue

        provider = getattr(dep, "provider", None)
        if isinstance(provider, MediaRIT) and provider.path is not None:
            attrs = {
                "media.preview_path": str(provider.path),
            }
            if dep.media_role:
                attrs["media.preview_role"] = dep.media_role
            return attrs

        requirement = getattr(dep, "requirement", None)
        path = getattr(requirement, "path", None)
        if isinstance(path, Path):
            attrs = {
                "media.preview_path": str(path),
            }
            if dep.media_role:
                attrs["media.preview_role"] = dep.media_role
            return attrs

        authored_path = getattr(requirement, "authored_path", None)
        if isinstance(authored_path, str) and authored_path:
            attrs = {
                "media.preview_path": authored_path,
            }
            if dep.media_role:
                attrs["media.preview_role"] = dep.media_role
            return attrs
    return {}


def _dot_quote(value: Any) -> str:
    return json.dumps("" if value is None else str(value))


def _dot_group_attrs(group: ProjectedGroup) -> dict[str, object]:
    attrs: dict[str, object] = {"label": group.label}
    for key, value in sorted(group.attrs.items()):
        if key.startswith("style.") and value is not None:
            attrs[key.removeprefix("style.")] = value
    return attrs


def _dot_node_statement(node: ProjectedNode) -> str:
    attrs: dict[str, object] = {"label": node.label}
    for key, value in sorted(node.attrs.items()):
        if value is None or not key.startswith("style."):
            continue
        attrs[key.removeprefix("style.")] = value

    preview_path = node.attrs.get("media.preview_path")
    if isinstance(preview_path, str) and preview_path:
        attrs["image"] = preview_path
        attrs.setdefault("imagescale", "true")
        attrs.setdefault("labelloc", "b")

    attr_text = ", ".join(f"{name}={_dot_quote(value)}" for name, value in attrs.items())
    return f'{_dot_quote(node.id)} [{attr_text}];'


def _dot_edge_statement(edge: ProjectedEdge) -> str:
    attrs: dict[str, object] = {}
    if edge.label:
        attrs["label"] = edge.label
    for key, value in sorted(edge.attrs.items()):
        if value is None or not key.startswith("style."):
            continue
        attrs[key.removeprefix("style.")] = value

    if attrs:
        attr_text = ", ".join(f"{name}={_dot_quote(value)}" for name, value in attrs.items())
        return f'{_dot_quote(edge.source_id)} -> {_dot_quote(edge.target_id)} [{attr_text}];'
    return f"{_dot_quote(edge.source_id)} -> {_dot_quote(edge.target_id)};"


def _coerce_world(bundle_or_world: StoryTemplateBundle | World) -> World:
    if isinstance(bundle_or_world, World):
        return bundle_or_world
    if isinstance(bundle_or_world, StoryTemplateBundle):
        label = (
            getattr(bundle_or_world.template_registry, "label", None)
            or getattr(bundle_or_world, "bundle_id", None)
            or "analysis_bundle"
        )
        return WorldBuilder().build(label=label, bundle=bundle_or_world)
    raise TypeError("expected World or StoryTemplateBundle")


def _make_projection_story(*, world: World, story_label: str) -> StoryGraph:
    result = world.create_story(
        story_label,
        init_mode=InitMode.EAGER,
        freeze_shape=True,
    )
    return result.graph


def _compat_edge_kind(edge_role: str) -> str:
    if edge_role == "choice":
        return "action"
    return edge_role


def _gate_type(value: Any) -> str | None:
    gate_value = getattr(value, "gate_type", None)
    return getattr(gate_value, "value", gate_value)


def _layout_positions(report: ScriptGraphReport) -> dict[str, tuple[int, int]]:
    node_by_id = {node.id: node for node in report.nodes}
    adjacency: dict[str, list[str]] = {node.id: [] for node in report.nodes}
    for edge in report.edges:
        adjacency.setdefault(edge.source_id, []).append(edge.target_id)

    for source_id in adjacency:
        adjacency[source_id] = sorted(
            adjacency[source_id],
            key=lambda target_id: (node_by_id[target_id].label, target_id),
        )

    entry_ids = sorted(
        [node.id for node in report.nodes if node.is_entry],
        key=lambda node_id: (node_by_id[node_id].label, node_id),
    )
    if not entry_ids:
        entry_ids = sorted(node_by_id, key=lambda node_id: (node_by_id[node_id].label, node_id))

    depth_by_id: dict[str, int] = {}
    queue: deque[tuple[str, int]] = deque((node_id, 0) for node_id in entry_ids)
    while queue:
        node_id, depth = queue.popleft()
        if node_id in depth_by_id and depth >= depth_by_id[node_id]:
            continue
        depth_by_id[node_id] = depth
        for target_id in adjacency.get(node_id, []):
            queue.append((target_id, depth + 1))

    next_depth = (max(depth_by_id.values()) + 1) if depth_by_id else 0
    for node_id in sorted(node_by_id, key=lambda item: (node_by_id[item].label, item)):
        if node_id not in depth_by_id:
            depth_by_id[node_id] = next_depth
            next_depth += 1

    columns: dict[int, list[str]] = {}
    for node_id, depth in depth_by_id.items():
        columns.setdefault(depth, []).append(node_id)

    positions: dict[str, tuple[int, int]] = {}
    for depth in sorted(columns):
        column_ids = sorted(columns[depth], key=lambda node_id: (node_by_id[node_id].label, node_id))
        for index, node_id in enumerate(column_ids):
            positions[node_id] = (
                48 + (depth * 220),
                40 + (index * 96),
            )
    return positions


def _shape_name(gate_type: str | None) -> str:
    return {
        "INPUT": "rect",
        "OUTPUT": "ellipse",
        "XOR": "diamond",
        "AND": "hex",
        "OR": "triangle",
    }.get(gate_type, "rect")


def _shape_svg(*, shape: str, x: int, y: int, width: int, height: int, fill: str) -> str:
    if shape == "ellipse":
        return (
            f'<ellipse cx="{x + (width / 2)}" cy="{y + (height / 2)}" rx="{width / 2}" '
            f'ry="{height / 2}" fill="{fill}" stroke="#102a43" stroke-width="2"/>'
        )
    if shape == "diamond":
        points = [
            (x + (width / 2), y),
            (x + width, y + (height / 2)),
            (x + (width / 2), y + height),
            (x, y + (height / 2)),
        ]
        return _polygon(points=points, fill=fill)
    if shape == "hex":
        offset = 18
        points = [
            (x + offset, y),
            (x + width - offset, y),
            (x + width, y + (height / 2)),
            (x + width - offset, y + height),
            (x + offset, y + height),
            (x, y + (height / 2)),
        ]
        return _polygon(points=points, fill=fill)
    if shape == "triangle":
        points = [
            (x + (width / 2), y),
            (x + width, y + height),
            (x, y + height),
        ]
        return _polygon(points=points, fill=fill)
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" fill="{fill}" '
        'stroke="#102a43" stroke-width="2"/>'
    )


def _polygon(*, points: list[tuple[float, float]], fill: str) -> str:
    svg_points = " ".join(f"{x},{y}" for x, y in points)
    return f'<polygon points="{svg_points}" fill="{fill}" stroke="#102a43" stroke-width="2"/>'


__all__ = [
    "ProjectedEdge",
    "ProjectedGraph",
    "ProjectedGroup",
    "ProjectedNode",
    "ScriptGraphEdge",
    "ScriptGraphNode",
    "ScriptGraphReport",
    "attach_media_preview",
    "build_script_report",
    "cluster_by_scene",
    "episode_only_selector",
    "episode_plus_concepts_selector",
    "mark_node_styles",
    "project_story_graph",
    "project_world_graph",
    "projected_graph_to_dict",
    "render_basic_svg",
    "render_dot",
    "report_to_dict",
    "structural_selector",
    "to_dot",
]
