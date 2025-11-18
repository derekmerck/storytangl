from __future__ import annotations

from tangl.core import Graph, Node
from tangl.vm.context import Context
from tangl.core import Graph, Node
from tangl.story.episode.action import Action
from tangl.story.episode.block import Block
from tangl.story.story_graph import StoryGraph
from tangl.vm import Context
from tangl.vm.provision import Dependency, Requirement, ProvisioningPolicy


def _make_graph() -> tuple[Graph, Node, Node]:
    graph = Graph(label="action_choice_test")
    source = graph.add_node(label="source")
    destination = graph.add_node(label="destination")
    return graph, source, destination


def test_choice_fragment_prefers_content() -> None:
    graph, source, destination = _make_graph()
    action = Action(
        graph=graph,
        source_id=source.uid,
        destination_id=destination.uid,
        content="Display Text",
        label="internal_label",
    )
    ctx = Context(graph=graph, cursor_id=source.uid, step=1)

    fragment = action.choice_fragment(ctx=ctx)

    assert fragment is not None
    assert fragment.content == "Display Text"
    assert fragment.source_id == action.uid
    assert fragment.fragment_type == "choice"


def test_choice_fragment_falls_back_to_label() -> None:
    graph, source, destination = _make_graph()
    action = Action(
        graph=graph,
        source_id=source.uid,
        destination_id=destination.uid,
        label="LabelOnly",
    )
    ctx = Context(graph=graph, cursor_id=source.uid, step=2)

    fragment = action.choice_fragment(ctx=ctx)

    assert fragment is not None
    assert fragment.content == "LabelOnly"
    assert fragment.source_id == action.uid


def test_choice_fragment_defaults_to_continue() -> None:
    graph, source, destination = _make_graph()
    action = Action(
        graph=graph,
        source_id=source.uid,
        destination_id=destination.uid,
    )
    ctx = Context(graph=graph, cursor_id=source.uid, step=3)

    fragment = action.choice_fragment(ctx=ctx)

    assert fragment is not None
    assert fragment.content == "continue"
    assert fragment.source_id == action.uid


def test_action_is_available_inherits_block_namespace() -> None:
    story = StoryGraph(label="action_namespace")
    start = story.add_node(obj_cls=Block, label="start")
    start.locals["has_hint"] = True
    destination = story.add_node(obj_cls=Block, label="destination")

    action = story.add_edge(
        start,
        destination,
        obj_cls=Action,
        label="Proceed",
        content="Proceed",
    )
    action.conditions = ["has_hint"]

    ctx = Context(graph=story, cursor_id=start.uid, step=1)

    assert action in start.get_choices(ctx=ctx, is_instance=Action)

    start.locals["has_hint"] = False
    ctx_after = Context(graph=story, cursor_id=start.uid, step=2)

    assert action not in start.get_choices(ctx=ctx_after, is_instance=Action)


def test_choice_fragment_marks_unavailable_with_reason() -> None:
    graph = StoryGraph(label="action_choice_unavailable")
    block = Block(graph=graph, label="block")
    target = Block(graph=graph, label="target")
    block.locals["has_key"] = False

    action = Action(
        graph=graph,
        source_id=block.uid,
        destination_id=target.uid,
        label="locked_door",
        conditions=["False"],
    )

    requirement = Requirement(
        graph=graph,
        identifier="keycard",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=True,
    )
    Dependency(graph=graph, source_id=target.uid, requirement=requirement, label="keycard")

    ctx = Context(graph=graph, cursor_id=block.uid)
    fragment = action.choice_fragment(ctx=ctx)

    assert fragment is not None
    assert fragment.active is False
    assert fragment.unavailable_reason is not None
    assert "keycard" in fragment.unavailable_reason.lower()
