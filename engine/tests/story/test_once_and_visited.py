"""Where the reader has been is the ledger's business.

The ledger records the cursor history, so that is what answers "has this been
visited?" - for ``visited(ref)`` in an authored condition, and for an edge
marked ``once``. A node carries ``_visited`` locals as a convenience, but they
are an annotation, not the record: a hub reached by another route has still
been visited, and a restored ledger still knows where its reader has been.

``once`` is the word sandbox interactions have always used for this.
"""

from __future__ import annotations

from tangl.core import Selector
from tangl.journal.fragments import ChoiceFragment
from tangl.story import InitMode
from tangl.story.episode import Action
from tangl.story.fabula.world import World
from tangl.vm import Ledger


def _script() -> dict:
    return {
        "label": "once_world",
        "metadata": {"title": "Once", "start_at": "s.start"},
        "scenes": {
            "s": {
                "blocks": {
                    "start": {
                        "label": "start",
                        "content": "Start",
                        "actions": [
                            {"text": "Straight to the hub", "successor": "hub", "once": True},
                            {"text": "The long way", "successor": "detour"},
                        ],
                    },
                    "detour": {
                        "label": "detour",
                        "content": "A detour.",
                        "actions": [{"text": "On to the hub", "successor": "hub"}],
                    },
                    "hub": {
                        "label": "hub",
                        "content": "The hub.",
                        "actions": [{"text": "Back", "successor": "start"}],
                    },
                }
            }
        },
    }


def _graph(label: str):
    world = World.from_script_data(script_data=_script())
    return world.create_story(label, init_mode=InitMode.EAGER).graph


def _node(graph, label: str):
    return next(n for n in graph.find_nodes(Selector()) if n.get_label() == label)


def _edge(graph, source: str, text: str):
    return next(
        edge
        for edge in _node(graph, source).edges_out(Selector(has_kind=Action))
        if edge.text == text
    )


def _offered(ledger) -> dict[str, bool]:
    """The choices standing at the cursor now, by text, to whether they are open."""
    return {
        fragment.text: bool(fragment.available)
        for fragment in ledger.get_journal()
        if isinstance(fragment, ChoiceFragment)
        and fragment.step >= ledger.current_update_start_step
    }


def _ns_at(ledger, label: str):
    node = _node(ledger.graph, label)
    return ledger.get_frame()._make_ctx().get_ns(node)


def test_a_once_edge_is_open_until_its_destination_is_visited() -> None:
    graph = _graph("once_open")
    ledger = Ledger.from_graph(graph=graph, entry_id=_node(graph, "start").uid)
    ledger.resolve_choice(_edge(graph, "start", "The long way").uid)

    # At the detour, the hub has not been reached yet.
    assert _offered(ledger) == {"On to the hub": True}


def test_a_once_edge_closes_after_any_route_reaches_its_destination() -> None:
    graph = _graph("once_closed")
    ledger = Ledger.from_graph(graph=graph, entry_id=_node(graph, "start").uid)
    ledger.resolve_choice(_edge(graph, "start", "The long way").uid)
    ledger.resolve_choice(_edge(graph, "detour", "On to the hub").uid)
    ledger.resolve_choice(_edge(graph, "hub", "Back").uid)

    # Back at the start, having reached the hub the long way round.
    offered = _offered(ledger)
    assert offered["Straight to the hub"] is False
    assert offered["The long way"] is True


def test_visited_answers_for_any_node_by_label_or_by_node() -> None:
    graph = _graph("visited_query")
    ledger = Ledger.from_graph(graph=graph, entry_id=_node(graph, "start").uid)
    hub = _node(graph, "hub")

    visited = _ns_at(ledger, "start")["visited"]
    assert visited("hub") is False
    assert visited(hub) is False
    assert visited(hub.uid) is False

    ledger.resolve_choice(_edge(graph, "start", "The long way").uid)
    ledger.resolve_choice(_edge(graph, "detour", "On to the hub").uid)

    visited = _ns_at(ledger, "hub")["visited"]
    assert visited("hub") is True
    assert visited(hub) is True
    assert visited(hub.uid) is True
    assert visited("detour") is True
    assert visited("nowhere_in_particular") is False
