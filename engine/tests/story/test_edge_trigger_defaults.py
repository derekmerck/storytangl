"""A block's edge list declares how its edges fire.

``continues`` follow on their own after the block's content, ``redirects``
before it, and ``actions`` wait for the reader. The script models have said so
since they were written, but only as pydantic defaults; the dict compiler never
applied them, so an entry that did not restate ``trigger`` compiled to a plain
choice. A silently-offered redirect is the worst of it: it is documented as
automatic. Every ``continues`` entry in this repo's worlds writes
``trigger: last`` by hand, which is the workaround, not the contract.
"""

from __future__ import annotations

from tangl.core import Selector
from tangl.story import InitMode
from tangl.story.episode import Action
from tangl.story.fabula.world import World
from tangl.vm import Ledger, ResolutionPhase


def _script(hub: dict) -> dict:
    return {
        "label": "trigger_defaults_world",
        "metadata": {"title": "Trigger Defaults", "start_at": "s.start"},
        "scenes": {
            "s": {
                "blocks": {
                    "start": {
                        "label": "start",
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "hub"}],
                    },
                    "hub": {"label": "hub", "content": "Hub", **hub},
                    "end": {"label": "end", "content": "End"},
                }
            }
        },
    }


def _graph(hub: dict, label: str = "story"):
    world = World.from_script_data(script_data=_script(hub))
    return world.create_story(label, init_mode=InitMode.EAGER).graph


def _node(graph, label: str):
    return next(n for n in graph.find_nodes(Selector()) if n.get_label() == label)


def _walk_into_hub(graph):
    start = _node(graph, "start")
    ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
    go = next(iter(start.edges_out(Selector(has_kind=Action))))
    ledger.resolve_choice(go.uid)
    return ledger


def _edge_to(graph, source: str, target: str):
    node = _node(graph, source)
    return next(
        edge
        for edge in node.edges_out(Selector(has_kind=Action))
        if edge.successor_id and graph.get(edge.successor_id).get_label() == target
    )


def test_an_untriggered_continue_follows_itself() -> None:
    graph = _graph({"continues": [{"successor": "end"}]}, "continue_story")

    assert _walk_into_hub(graph).cursor.get_label() == "end"


def test_an_untriggered_redirect_fires_before_the_block() -> None:
    graph = _graph({"redirects": [{"successor": "end"}]}, "redirect_story")

    assert _walk_into_hub(graph).cursor.get_label() == "end"


def test_an_untriggered_action_still_waits_for_the_reader() -> None:
    graph = _graph({"actions": [{"text": "Onward", "successor": "end"}]}, "action_story")

    assert _walk_into_hub(graph).cursor.get_label() == "hub"
    assert _edge_to(graph, "hub", "end").trigger_phase is None


def test_an_entry_that_names_its_trigger_keeps_it() -> None:
    # The default is what the field name implies, not an override.
    graph = _graph(
        {"continues": [{"successor": "end", "trigger": "first"}]}, "explicit_story"
    )

    assert _edge_to(graph, "hub", "end").trigger_phase is ResolutionPhase.PREREQS


def test_the_restated_trigger_in_the_worlds_still_means_the_same_thing() -> None:
    # 68 authored continues say ``trigger: last``. They must keep working.
    graph = _graph(
        {"continues": [{"successor": "end", "trigger": "last"}]}, "restated_story"
    )

    assert _edge_to(graph, "hub", "end").trigger_phase is ResolutionPhase.POSTREQS
    assert _walk_into_hub(graph).cursor.get_label() == "end"


def test_edges_are_named_for_the_list_they_came_from() -> None:
    # A block's first continue and its first action were both ``action_hub_0``.
    graph = _graph(
        {
            "continues": [{"successor": "end"}],
            "actions": [{"text": "Onward", "successor": "start"}],
        },
        "label_story",
    )
    hub = _node(graph, "hub")
    labels = {edge.get_label() for edge in hub.edges_out(Selector(has_kind=Action))}

    assert labels == {"continue_hub_0", "action_hub_0"}
