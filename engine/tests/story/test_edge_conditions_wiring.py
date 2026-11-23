"""Regression: authored edge ``conditions``/``effects`` must reach the edge.

`_wire_actions_for_block` previously copied only ``predicate`` onto Action
edges, silently dropping authored ``conditions`` (availability) and
``effects`` on actions / continues / redirects -- so a conditioned continue
gated nothing and the first continue always won. These tests pin the fix.
"""

from __future__ import annotations

import pytest

from tangl.core import Selector
from tangl.core.runtime_op import Predicate
from tangl.journal.fragments import ContentFragment
from tangl.mechanics.sandbox import SandboxLocation
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
                        "actions": [
                            {
                                "text": "Go",
                                "successor": "hub",
                                "effects": ["went = True"],
                            }
                        ],
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


def test_current_action_journals_and_updates_its_receiver() -> None:
    script = _script()
    start = script["scenes"]["s"]["blocks"]["start"]
    start["locals"] = {"hidden": False}
    start["actions"] = [{
        "text": "Hide", "successor": "current", "journal_text": "You hide.",
        "effects": ["hidden = True"],
    }]
    world = World.from_script_data(script_data=script)
    graph = world.create_story("current_action_story", init_mode=InitMode.EAGER).graph
    receiver = _node(graph, "start")
    action = next(receiver.edges_out(Selector(has_kind=Action)))
    assert action.successor is receiver
    ledger = Ledger.from_graph(graph=graph, entry_id=receiver.uid)
    ledger.resolve_choice(action.uid)
    assert receiver.locals["hidden"] is True
    assert any(isinstance(item, ContentFragment) and item.content == "You hide."
               for item in ledger.get_journal())


@pytest.mark.parametrize("kind", [None, SandboxLocation])
def test_offered_current_action_uses_the_shared_action_template(kind) -> None:
    script = _script()
    start = script["scenes"]["s"]["blocks"]["start"]
    start["locals"] = {"hidden": False}
    if kind is not None:
        start["kind"] = kind
        start["wait_enabled"] = False
    start["actions"] = []
    start["offered_actions"] = [{
        "text": "Hide", "successor": "current", "journal_text": "You hide.",
        "effects": ["hidden = True"], "payload": {"source": "cover"},
        "accepts": {"kind": "text", "required": True},
    }]
    world = World.from_script_data(script_data=script)
    graph = world.create_story("offered_current_story", init_mode=InitMode.EAGER).graph
    receiver = _node(graph, "start")
    ledger = Ledger.from_graph(graph=graph, entry_id=receiver.uid)
    from tangl.vm.dispatch import do_provision
    do_provision(receiver, ctx=ledger.get_frame()._make_ctx())
    (action,) = receiver.edges_out(Selector(has_kind=Action))
    assert action.successor is receiver
    assert action.payload == {"source": "cover"}
    with pytest.raises(ValueError):
        ledger.resolve_choice(action.uid, choice_payload={"text": ""})
    ledger.resolve_choice(action.uid, choice_payload={"text": "quietly"})
    assert receiver.locals["hidden"] is True
    assert any(isinstance(item, ContentFragment) and item.content == "You hide."
               for item in ledger.get_journal())


def test_offered_last_self_loop_runs_until_its_guard_closes() -> None:
    script = _script()
    start = script["scenes"]["s"]["blocks"]["start"]
    start["locals"] = {"announced": False}
    start["actions"] = []
    start["offered_actions"] = [{
        "successor": "current", "trigger": "last", "conditions": ["not announced"],
        "effects": ["announced = True"],
    }]
    world = World.from_script_data(script_data=script)
    graph = world.create_story("offered_automatic_story", init_mode=InitMode.EAGER).graph
    receiver = _node(graph, "start")
    ledger = Ledger.from_graph(graph=graph, entry_id=receiver.uid)
    frame = ledger.get_frame()
    frame.goto_node(receiver)
    assert receiver.locals["announced"] is True
    assert frame.cursor.uid == receiver.uid


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
        # The authored effect must actually reach the edge -- not merely that
        # the field exists (the silent-drop bug left it an empty default).
        assert go.effects, "authored effect was dropped during wiring"
        exprs = [getattr(e, "expr", None) or getattr(e, "core_effect", None)
                 for e in go.effects]
        assert any("went = True" in str(x) for x in exprs)

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
