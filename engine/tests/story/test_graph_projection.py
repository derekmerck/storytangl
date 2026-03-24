"""Projection, processor, and DOT tests for the phase-2 graph adapter."""

from __future__ import annotations

from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.media.media_resource import MediaDep
from tangl.story import (
    Action,
    Actor,
    Block,
    InitMode,
    Location,
    ProjectedEdge,
    ProjectedGraph,
    ProjectedGroup,
    ProjectedNode,
    Role,
    Scene,
    Setting,
    StoryGraph,
    World,
    attach_media_preview,
    cluster_by_scene,
    episode_only_selector,
    episode_plus_concepts_selector,
    project_story_graph,
    project_world_graph,
    projected_graph_to_dict,
    render_dot,
    structural_selector,
    to_dot,
)
from tangl.story.system_handlers import render_block_media
from tangl.vm import Ledger, Requirement


def _logic_root() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds" / "logic_demo"


def _compile_logic_world() -> World:
    bundle = WorldBundle.load(_logic_root())
    return WorldCompiler().compile(bundle)


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


def _choice_by_text(ledger: Ledger, text: str) -> Action:
    return next(
        action
        for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if action.text == text
    )


def _concept_graph() -> StoryGraph:
    graph = StoryGraph(label="concept_projection")
    scene = Scene(label="intro", registry=graph, title="Introduction")
    start = Block(label="start", registry=graph, content="Start")
    end = Block(label="end", registry=graph, content="End")
    scene.add_child(start)
    scene.add_child(end)
    scene.finalize_container_contract()

    actor = Actor(label="guide", registry=graph, name="Guide")
    location = Location(label="camp", registry=graph, name="Camp")

    action = Action(
        registry=graph,
        label="go_end",
        predecessor_id=start.uid,
        successor_id=end.uid,
        text="Go",
    )
    role = Role(
        registry=graph,
        label="host",
        predecessor_id=start.uid,
        requirement=Requirement(has_kind=Actor, has_identifier="guide"),
    )
    role.set_successor(actor)

    setting = Setting(
        registry=graph,
        label="place",
        predecessor_id=start.uid,
        requirement=Requirement(has_kind=Location, has_identifier="camp"),
    )
    setting.set_successor(location)

    graph.initial_cursor_id = start.uid
    graph.initial_cursor_ids = [start.uid]
    _ = action
    return graph


def _dot_fixture_graph() -> ProjectedGraph:
    return ProjectedGraph(
        nodes=[
            ProjectedNode(
                id="n1",
                label="Start",
                source_id=None,
                source_kind="tests.Start",
                attrs={},
            ),
            ProjectedNode(
                id="n2",
                label="Result",
                source_id=None,
                source_kind="tests.Result",
                attrs={
                    "media.preview_path": "/tmp/thumb.svg",
                    "style.shape": "diamond",
                },
            ),
        ],
        edges=[
            ProjectedEdge(
                id="n1:choice:n2",
                source_id="n1",
                target_id="n2",
                label="advance",
                source_edge_id=None,
                source_kind="tests.Edge",
                edge_role="choice",
                attrs={},
            )
        ],
        groups=[
            ProjectedGroup(
                id="clustered",
                label="Clustered",
                group_kind="cluster",
                member_node_ids=["n1"],
                source_id=None,
                source_kind=None,
                attrs={},
            ),
            ProjectedGroup(
                id="logical",
                label="Logical",
                group_kind="group",
                member_node_ids=["n2"],
                source_id=None,
                source_kind=None,
                attrs={},
            ),
        ],
    )


def test_project_story_graph_is_deterministic_for_one_live_graph() -> None:
    world = _compile_logic_world()
    story = world.create_story("logic_demo_projection", init_mode=InitMode.EAGER).graph

    first = projected_graph_to_dict(project_story_graph(story))
    second = projected_graph_to_dict(project_story_graph(story))

    assert first == second


def test_project_world_graph_has_stable_structural_ids_across_runs() -> None:
    world = _compile_logic_world()

    first = project_world_graph(world)
    second = project_world_graph(world)

    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [(node.label, node.source_kind) for node in first.nodes] == [
        (node.label, node.source_kind) for node in second.nodes
    ]
    assert [
        (edge.id, edge.source_id, edge.target_id, edge.edge_role, edge.label)
        for edge in first.edges
    ] == [
        (edge.id, edge.source_id, edge.target_id, edge.edge_role, edge.label)
        for edge in second.edges
    ]


def test_default_structural_selector_includes_scenes_blocks_and_actions() -> None:
    world = _compile_logic_world()

    projected = project_world_graph(world)

    assert any(source_kind and source_kind.endswith(".Scene") for source_kind in (n.source_kind for n in projected.nodes))
    assert any(source_kind and source_kind.endswith("LogicBlock") for source_kind in (n.source_kind for n in projected.nodes))
    assert any(edge.source_kind and edge.source_kind.endswith(".Action") for edge in projected.edges)


def test_episode_only_and_episode_plus_concepts_selectors_filter_registry_items() -> None:
    graph = _concept_graph()

    episode_only = project_story_graph(graph, selector=episode_only_selector())
    plus_concepts = project_story_graph(graph, selector=episode_plus_concepts_selector())

    assert {node.id for node in episode_only.nodes} == {"intro", "intro.start", "intro.end"}
    assert {node.id for node in plus_concepts.nodes} == {
        "intro",
        "intro.start",
        "intro.end",
        "guide",
        "camp",
    }
    assert all(edge.source_kind and not edge.source_kind.endswith(".Role") for edge in episode_only.edges)
    assert all(edge.source_kind and not edge.source_kind.endswith(".Setting") for edge in episode_only.edges)
    assert any(edge.source_kind and edge.source_kind.endswith(".Role") for edge in plus_concepts.edges)
    assert any(edge.source_kind and edge.source_kind.endswith(".Setting") for edge in plus_concepts.edges)


def test_edges_drop_when_endpoints_are_not_projected() -> None:
    graph = _concept_graph()

    projected = project_story_graph(
        graph,
        selector=episode_plus_concepts_selector(),
        node_selector=Selector(has_kind=Block),
    )

    assert {node.id for node in projected.nodes} == {"intro.start", "intro.end"}
    assert len(projected.edges) == 1
    assert projected.edges[0].edge_role == "choice"


def test_projection_uses_template_labels_and_edge_roles_for_logic_demo_world() -> None:
    world = _compile_logic_world()

    projected = project_world_graph(world, selector=episode_only_selector())
    node_ids = {node.id for node in projected.nodes}
    edge_roles = {
        (edge.source_id, edge.target_id): edge.edge_role
        for edge in projected.edges
    }
    node_by_id = {node.id: node for node in projected.nodes}

    assert "demo.choose_machine" in node_ids
    assert "parity.parity_even_output" in node_ids
    assert node_by_id["half_adder.half_adder_and_11"].source_kind is not None
    assert node_by_id["half_adder.half_adder_and_11"].source_kind.endswith("LogicBlock")
    assert edge_roles[("demo.choose_machine", "parity.parity_first_input")] == "choice"
    assert edge_roles[("half_adder.half_adder_xor_11", "half_adder.half_adder_and_11")] == "continue"


def test_cluster_by_scene_adds_stable_scene_groups() -> None:
    world = _compile_logic_world()

    projected = project_world_graph(
        world,
        selector=episode_only_selector(),
        processors=(cluster_by_scene(),),
    )

    assert projected.groups
    parity_group = next(group for group in projected.groups if "parity.parity_first_input" in group.member_node_ids)
    assert parity_group.group_kind == "cluster"
    assert parity_group.source_kind is not None and parity_group.source_kind.endswith(".Scene")
    assert parity_group.source_id is not None


def test_attach_media_preview_annotates_only_when_media_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )

    world = _compile_logic_world()
    story = world.create_story("logic_demo_projection_media", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(story, entry_id=story.initial_cursor_id)

    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the parity checker").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "First bit = 1").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "Second bit = 1").uid)

    deps = [edge for edge in ledger.cursor.edges_out() if isinstance(edge, MediaDep)]
    assert len(deps) == 1

    render_block_media(
        caller=ledger.cursor,
        ctx=SimpleNamespace(get_ns=lambda _caller: {}),
    )

    projected = project_story_graph(
        story,
        selector=episode_only_selector(),
        processors=(attach_media_preview(media_role="logic_badge"),),
    )
    node_by_id = {node.id: node for node in projected.nodes}

    assert "media.preview_path" in node_by_id["parity.parity_even_output"].attrs
    assert "media.preview_path" not in node_by_id["parity.parity_odd_state"].attrs


def test_to_dot_emits_clusters_logical_groups_and_optional_media_attrs() -> None:
    dot_text = to_dot(_dot_fixture_graph())

    assert 'subgraph "cluster_clustered"' in dot_text
    assert 'subgraph "logical"' in dot_text
    assert 'image="/tmp/thumb.svg"' in dot_text
    assert '"n1" -> "n2" [label="advance"]' in dot_text


@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz dot is not installed")
def test_render_dot_renders_svg_bytes() -> None:
    dot_text = to_dot(_dot_fixture_graph())

    rendered = render_dot(dot_text, format="svg")

    assert rendered.startswith(b"<?xml")
    assert b"<svg" in rendered


def test_structural_selector_matches_traversable_nodes_and_edges() -> None:
    graph = _concept_graph()
    selected = list(structural_selector().filter(graph.values()))

    assert any(isinstance(item, Scene) for item in selected)
    assert any(isinstance(item, Block) for item in selected)
    assert any(isinstance(item, Action) for item in selected)
    assert all(not isinstance(item, Actor) for item in selected)
    assert all(not isinstance(item, Role) for item in selected)
