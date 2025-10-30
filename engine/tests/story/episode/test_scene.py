"""Tests for :mod:`tangl.story.reference_domain.scene`."""

from __future__ import annotations

from uuid import UUID

from pip._internal.resolution.resolvelib import provider

from tangl.core import Graph, Node, CallReceipt
from tangl.story.episode import Block, Scene
from tangl.story.concepts import Concept
from tangl.vm import (
    Affordance,
    ChoiceEdge,
    Dependency,
    Frame,
    ProvisioningPolicy,
    Requirement,
    ResolutionPhase as P,
)
from tangl.vm.vm_dispatch.on_get_ns import do_get_ns


def _destination_ids(node: Node) -> set[UUID]:
    return {
        edge.destination.uid
        for edge in node.edges_out(is_instance=ChoiceEdge)
        if edge.destination is not None
    }


def test_scene_creates_source_and_sink() -> None:
    g = Graph(label="test")
    first = Block(graph=g, label="first")
    second = Block(graph=g, label="second")

    scene = Scene(graph=g, label="scene", member_ids=[first.uid, second.uid])

    assert scene.source in g
    assert scene.sink in g
    assert scene.source.label.endswith("_SOURCE")
    assert scene.sink.label.endswith("_SINK")


def test_scene_links_source_to_entry_blocks() -> None:
    g = Graph(label="test")
    entry_one = Block(graph=g, label="entry_one")
    entry_two = Block(graph=g, label="entry_two")
    middle = Block(graph=g, label="middle")

    scene = Scene(
        graph=g,
        label="scene",
        member_ids=[entry_one.uid, entry_two.uid, middle.uid],
        entry_ids=[entry_one.uid, entry_two.uid],
    )

    destinations = _destination_ids(scene.source)

    assert entry_one.uid in destinations
    assert entry_two.uid in destinations
    assert middle.uid not in destinations


def test_scene_links_exit_blocks_to_sink() -> None:
    g = Graph(label="test")
    middle = Block(graph=g, label="middle")
    exit_one = Block(graph=g, label="exit_one")
    exit_two = Block(graph=g, label="exit_two")

    scene = Scene(
        graph=g,
        label="scene",
        member_ids=[middle.uid, exit_one.uid, exit_two.uid],
        exit_ids=[exit_one.uid, exit_two.uid],
    )

    assert scene.sink.uid in _destination_ids(exit_one)
    assert scene.sink.uid in _destination_ids(exit_two)


def test_scene_defaults_entry_exit_to_first_last() -> None:
    g = Graph(label="test")
    first = Block(graph=g, label="first")
    middle = Block(graph=g, label="middle")
    last = Block(graph=g, label="last")

    scene = Scene(graph=g, label="scene", member_ids=[first.uid, middle.uid, last.uid])

    assert scene.entry_node_ids == [first.uid]
    assert scene.exit_node_ids == [last.uid]
    assert scene.entry_blocks == [first]
    assert scene.exit_blocks == [last]


def test_get_member_blocks_returns_only_blocks() -> None:
    g = Graph(label="test")
    block_one = Block(graph=g, label="block_one")
    block_two = Block(graph=g, label="block_two")
    concept = Concept(graph=g, label="concept", content="text")

    scene = Scene(
        graph=g,
        label="scene",
        member_ids=[block_one.uid, concept.uid, block_two.uid],
    )

    members = scene.get_member_blocks()

    assert members == [block_one, block_two]


def test_refresh_ns_for_dependencies() -> None:
    g = Graph(label="test")
    block = Block(graph=g, label="block")
    companion = Node(graph=g, label="companion")

    requirement = Requirement[Node](
        graph=g,
    )
    dependency = Dependency[Node](
        graph=g,
        source_id=block.uid,
        requirement=requirement,
        label="companion",
    )
    dependency.requirement.provider = companion

    ns = do_get_ns(block, ctx=None)
    assert ns["companion"] is companion


def test_refresh_edge_projections_for_affordances() -> None:
    g = Graph(label="test")
    block = Block(graph=g, label="block")
    provider = Node(graph=g, label="provider")

    requirement = Requirement[Node](
        graph=g,
    )
    affordance = Affordance[Node](
        graph=g,
        destination_id=provider.uid,
        requirement=requirement,
        label="service",
    )
    affordance.requirement.provider = block
    ns = do_get_ns(block, ctx=None)

    assert ns["service"] is provider


def test_refresh_edge_projections_marks_unsatisfied() -> None:
    g = Graph(label="test")
    block = Block(graph=g, label="block")

    requirement = Requirement[Node](
        graph=g,
        hard_requirement=True,
    )
    Dependency[Node](graph=g, source_id=block.uid, requirement=requirement, label="missing")

    scene = Scene(graph=g, label="scene", member_ids=[block.uid])

    ns = do_get_ns(block, ctx=None)
    assert "missing" not in ns

    requirement.provider = Block(graph=g, label="provider")
    ns = do_get_ns(block, ctx=None)
    assert "missing" in ns
    assert ns["missing"].get_label() == "provider"


def test_refresh_edge_projections_preserves_existing_vars() -> None:
    g = Graph(label="test")

    scene = Scene(graph=g, label="scene")
    scene.locals["region"] = "Tavern"
    block = Block(graph=g, label="block")
    scene.add_member(block)
    provider = Block(graph=g, label="provider")

    requirement = Requirement[Node](
        graph=g,
    )
    Dependency[Node](graph=g, source_id=block.uid, requirement=requirement, label="prop")

    from tangl.vm.context import Context
    ctx = Context(cursor_id=block.uid, graph=g)
    ns = ctx.get_ns()

    assert ns["region"] == "Tavern"
    assert "prop" not in ns

    requirement.provider = provider
    ns = ctx.get_ns(nocache=True)
    assert ns["prop"] is provider


def test_has_forward_progress_reachable() -> None:
    g = Graph(label="test")
    start = Block(graph=g, label="start")
    middle = Block(graph=g, label="middle")
    end = Block(graph=g, label="end")

    ChoiceEdge(graph=g, source_id=start.uid, destination_id=middle.uid)
    ChoiceEdge(graph=g, source_id=middle.uid, destination_id=end.uid)

    scene = Scene(
        graph=g,
        label="scene",
        member_ids=[start.uid, middle.uid, end.uid],
        entry_ids=[start.uid],
        exit_ids=[end.uid],
    )

    assert scene.has_forward_progress(start) is True
    assert scene.has_forward_progress(middle) is True


def test_has_forward_progress_softlock() -> None:
    g = Graph(label="test")
    start = Block(graph=g, label="start")
    dead_end = Block(graph=g, label="dead_end")
    exit_block = Block(graph=g, label="exit")

    ChoiceEdge(graph=g, source_id=start.uid, destination_id=dead_end.uid)

    scene = Scene(
        graph=g,
        label="scene",
        member_ids=[start.uid, dead_end.uid, exit_block.uid],
        entry_ids=[start.uid],
        exit_ids=[exit_block.uid],
    )

    assert scene.has_forward_progress(dead_end) is False


def test_scene_namespace_available_during_journal() -> None:
    g = Graph(label="test")
    block = Block(graph=g, label="block", content="Hello {{npc_name}}!")
    scene = Scene(graph=g, label="tavern", member_ids=[block.uid])
    scene.locals["npc_name"] = "Bartender Bob"

    frame = Frame(graph=g, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    text = "\n".join(getattr(fragment, "content", "") for fragment in fragments)
    assert "Hello Bartender Bob!" in text


def test_refresh_edge_projections_updates_namespace_in_place() -> None:
    g = Graph(label="test")
    block = Block(graph=g, label="block")
    actor = Node(graph=g, label="villain")

    requirement = Requirement[Node](
        graph=g,
        identifier="npc",
        policy=ProvisioningPolicy.EXISTING,
    )
    dependency = Dependency[Node](
        graph=g,
        source_id=block.uid,
        requirement=requirement,
        label="npc",
    )

    scene = Scene(graph=g, label="scene", member_ids=[block.uid])

    frame = Frame(graph=g, cursor_id=block.uid)

    ns = frame.context.get_ns()

    assert "npc" not in ns

    dependency.destination = actor
    # scene.refresh_edge_projections()
    # assert scene.vars["npc"] is actor

    frame._invalidate_context()
    ns = frame.context.get_ns()
    assert ns["npc"] is actor
