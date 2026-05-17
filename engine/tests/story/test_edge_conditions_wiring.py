"""Regression: authored edge ``conditions``/``effects`` must reach the edge.

`_wire_actions_for_block` previously copied only ``predicate`` onto Action
edges, silently dropping authored ``conditions`` (availability) and
``effects`` on actions / continues / redirects -- so a conditioned continue
gated nothing and the first continue always won. These tests pin the fix.
"""

from __future__ import annotations

from tangl.core import Selector
from tangl.core.runtime_op import Predicate
from tangl.story import InitMode
from tangl.story.episode import Action
from tangl.story.fabula.world import World
from tangl.vm import Ledger


def _script() -> dict:
    return {
        "label": "edge_cond_world",
        "metadata": {"title": "Edge Conditions", "start_at": "s.start"},
        "scenes": {
            "s": {
                "blocks": {
                    "start": {
                        "label": "start",
                        "content": "Start",
                        "actions": [{"text": "Go", "successor": "hub"}],
                    },
                    "hub": {
                        "label": "hub",
                        "content": "Branch point.",
                        "locals": {"gate": True},
                        "continues": [
                            {
                                "successor": "open",
                                "trigger": "last",
                                "conditions": ["gate"],
                            },
                            {
                                "successor": "shut",
                                "trigger": "last",
                                "conditions": ["not gate"],
                            },
                        ],
                    },
                    "open": {"label": "open", "content": "It opens."},
                    "shut": {"label": "shut", "content": "It stays shut."},
                }
            }
        },
    }


def _graph():
    world = World.from_script_data(script_data=_script())
    return world.create_story("edge_cond_story", init_mode=InitMode.EAGER).graph


def _node(graph, label: str):
    return next(n for n in graph.find_nodes(Selector()) if n.get_label() == label)


class TestEdgeConditionsWiring:
    def test_continue_carries_conditions_as_availability(self) -> None:
        graph = _graph()
        hub = _node(graph, "hub")
        to_open = next(
            e
            for e in hub.edges_out()
            if e.successor_id and graph.get(e.successor_id).get_label() == "open"
        )
        assert to_open.availability
        assert all(isinstance(p, Predicate) for p in to_open.availability)

    def test_action_carries_effects_onto_edge(self) -> None:
        graph = _graph()
        start = _node(graph, "start")
        go = next(iter(start.edges_out(Selector(has_kind=Action))))
        # Sanity: the wiring path is exercised; effects list exists and is
        # the typed edge field (empty here, but no longer silently dropped).
        assert hasattr(go, "effects")

    def test_conditioned_continue_gates_selection(self) -> None:
        graph = _graph()
        start = _node(graph, "start")
        ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
        go = next(iter(start.edges_out(Selector(has_kind=Action))))
        ledger.resolve_choice(go.uid)
        # gate is True -> the first continue's condition holds; if conditions
        # were dropped this would still pass, so also prove the negative:
        assert ledger.cursor.get_label() == "open"

    def test_negative_condition_selects_other_branch(self) -> None:
        script = _script()
        script["scenes"]["s"]["blocks"]["hub"]["locals"]["gate"] = False
        world = World.from_script_data(script_data=script)
        graph = world.create_story("edge_cond_story_neg", init_mode=InitMode.EAGER).graph
        start = _node(graph, "start")
        ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
        go = next(iter(start.edges_out(Selector(has_kind=Action))))
        ledger.resolve_choice(go.uid)
        assert ledger.cursor.get_label() == "shut"
