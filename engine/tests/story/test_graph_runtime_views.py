"""Runtime overlay and structural transform tests for phase-3 graph views."""

from __future__ import annotations

from pathlib import Path

import pytest

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import (
    Action,
    InitMode,
    Scene,
    annotate_runtime,
    cluster_by_scene,
    collapse_linear_chains,
    episode_only_selector,
    focus_runtime_window,
    mark_runtime_styles,
    project_story_graph,
    project_world_graph,
    projected_graph_to_dict,
)
from tangl.vm import Ledger


def _logic_root() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds" / "logic_demo"


def _compile_logic_world():
    bundle = WorldBundle.load(_logic_root())
    return WorldCompiler().compile(bundle)


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


@pytest.fixture(autouse=True)
def _install_story_media_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )


def _make_story(world, *, story_label: str):
    return world.create_story(story_label, init_mode=InitMode.EAGER).graph


def _make_ledger(world, *, story_label: str) -> Ledger:
    graph = _make_story(world, story_label=story_label)
    return Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)


def _choice_by_text(ledger: Ledger, text: str) -> Action:
    return next(
        action
        for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if action.text == text
    )


def test_base_projection_populates_single_origin_provenance() -> None:
    world = _compile_logic_world()

    projected = project_world_graph(world, selector=episode_only_selector())

    assert projected.nodes
    assert projected.edges
    assert all(node.synthetic is False for node in projected.nodes)
    assert all(node.origin_node_ids == [node.id] for node in projected.nodes)
    assert all(edge.synthetic is False for edge in projected.edges)
    assert all(edge.origin_edge_ids == [edge.id] for edge in projected.edges)


def test_annotate_runtime_marks_current_visited_followed_and_available() -> None:
    world = _compile_logic_world()
    ledger = _make_ledger(world, story_label="phase3_runtime_annotations")

    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the full adder").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "A = 1").uid)

    projected = project_story_graph(
        ledger.graph,
        selector=episode_only_selector(),
        processors=(annotate_runtime(ledger),),
    )
    node_by_id = {node.id: node for node in projected.nodes}
    edge_by_id = {edge.id: edge for edge in projected.edges}

    assert node_by_id["full_adder.full_adder_a_one"].attrs["runtime.current"] is True
    assert node_by_id["demo.choose_machine"].attrs["runtime.visited"] is True
    assert node_by_id["demo.choose_machine"].attrs["runtime.visit_index"] == 0
    assert node_by_id["full_adder.full_adder_a_one"].attrs["runtime.visit_count"] == 1
    assert edge_by_id["demo.choose_machine:choice:full_adder.full_adder_pick_a"].attrs["runtime.followed"] is True
    assert edge_by_id["full_adder.full_adder_a_one:choice:full_adder.full_adder_ab_10"].attrs["runtime.current_outgoing"] is True
    assert edge_by_id["full_adder.full_adder_a_one:choice:full_adder.full_adder_ab_10"].attrs["runtime.available"] is True


def test_annotate_runtime_noops_when_cursor_is_not_projected() -> None:
    world = _compile_logic_world()
    ledger = _make_ledger(world, story_label="phase3_runtime_noop")

    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the full adder").uid)

    base = project_story_graph(
        ledger.graph,
        selector=episode_only_selector(),
        node_selector=Selector(has_kind=Scene),
    )

    assert projected_graph_to_dict(annotate_runtime(ledger)(base)) == projected_graph_to_dict(base)


def test_focus_runtime_window_keeps_recent_history_and_filters_groups() -> None:
    world = _compile_logic_world()
    ledger = _make_ledger(world, story_label="phase3_runtime_window")

    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the full adder").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "A = 1").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "B = 1").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "Cin = 0").uid)

    clustered = project_story_graph(
        ledger.graph,
        selector=episode_only_selector(),
        processors=(cluster_by_scene(), annotate_runtime(ledger)),
    )
    focused = focus_runtime_window(
        ledger,
        history_steps=2,
        include_current_successors=False,
        include_current_predecessors=True,
    )(clustered)

    node_by_id = {node.id: node for node in focused.nodes}

    assert "full_adder.full_adder_output_110_sc01" in node_by_id
    assert "full_adder.full_adder_xor_110" in node_by_id
    assert "full_adder.full_adder_or_110" in node_by_id
    assert node_by_id["full_adder.full_adder_xor_110"].attrs["runtime.history_anchor"] is True
    assert node_by_id["full_adder.full_adder_or_110"].attrs["runtime.history_anchor"] is True
    assert all(group.member_node_ids for group in focused.groups)
    assert all(
        member_id in node_by_id
        for group in focused.groups
        for member_id in group.member_node_ids
    )


def test_collapse_linear_chains_rewrites_groups_and_source_maps() -> None:
    world = _compile_logic_world()
    collapsed = project_world_graph(
        world,
        selector=episode_only_selector(),
        processors=(cluster_by_scene(), collapse_linear_chains()),
    )

    node_by_id = {node.id: node for node in collapsed.nodes}
    chain_id = "chain:full_adder.full_adder_xor_000->full_adder.full_adder_or_000"
    source_ids = [
        collapsed._origin_source_nodes_by_id["full_adder.full_adder_xor_000"].uid,
        collapsed._origin_source_nodes_by_id["full_adder.full_adder_or_000"].uid,
    ]

    assert chain_id in node_by_id
    assert node_by_id[chain_id].synthetic is True
    assert node_by_id[chain_id].origin_node_ids == [
        "full_adder.full_adder_xor_000",
        "full_adder.full_adder_or_000",
    ]
    assert "full_adder.full_adder_xor_000" not in node_by_id
    assert "full_adder.full_adder_or_000" not in node_by_id
    assert "full_adder.full_adder_xor_000" not in collapsed._source_nodes_by_id
    assert "full_adder.full_adder_or_000" not in collapsed._source_nodes_by_id
    assert all(
        collapsed._projected_node_id_by_source_id[str(source_id)] == chain_id
        for source_id in source_ids
    )
    assert any(chain_id in group.member_node_ids for group in collapsed.groups)


def test_mark_runtime_styles_maps_runtime_attrs_to_dot_attrs() -> None:
    world = _compile_logic_world()
    ledger = _make_ledger(world, story_label="phase3_runtime_styles")

    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the full adder").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "A = 1").uid)

    projected = project_story_graph(
        ledger.graph,
        selector=episode_only_selector(),
        processors=(
            annotate_runtime(ledger),
            focus_runtime_window(ledger, history_steps=2, include_current_predecessors=True),
            cluster_by_scene(),
            collapse_linear_chains(),
            mark_runtime_styles(),
        ),
    )
    node_by_id = {node.id: node for node in projected.nodes}
    edge_by_id = {edge.id: edge for edge in projected.edges}

    assert node_by_id["full_adder.full_adder_a_one"].attrs["style.fillcolor"] == "#2563eb"
    assert node_by_id["full_adder.full_adder_pick_a"].attrs["style.fillcolor"] == "#dbeafe"
    assert edge_by_id["full_adder.full_adder_a_one:choice:full_adder.full_adder_ab_10"].attrs["style.color"] == "#2563eb"
    assert edge_by_id["demo.choose_machine:choice:full_adder.full_adder_pick_a"].attrs["style.color"] == "#0d9488"


def test_full_adder_projection_is_invariant_after_runtime_execution() -> None:
    world = _compile_logic_world()
    graph = _make_story(world, story_label="phase3_projection_invariance")
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)

    before = projected_graph_to_dict(project_story_graph(graph, selector=episode_only_selector()))

    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the full adder").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "A = 1").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "B = 0").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "Cin = 1").uid)

    after = projected_graph_to_dict(project_story_graph(graph, selector=episode_only_selector()))

    assert before == after
