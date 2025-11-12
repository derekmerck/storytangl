from __future__ import annotations

from tangl.core import Graph, Node
from tangl.vm.context import Context
from tangl.story.episode.action import Action


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
