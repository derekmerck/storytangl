"""``return: true`` makes a choice a call: go there, then come back.

The VM has had call edges since it was written - the sandbox builds them for an
interaction with ``return_to_location`` - but nothing carried the field from an
authored script, so a gamebook's "return to the paragraph from which you came"
could only be compiled as a dead end.

The call remains open when its destination offers a selectable action. The reader
then receives that action as an ordinary choice, and the call returns only after
the selected path reaches a terminal. Automatic continuations still run before
the reader receives control, so their intermediate choices must not be published.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tangl.core import Selector
from tangl.ir.story_ir import ActionScript
from tangl.journal.fragments import ChoiceFragment
from tangl.story import InitMode
from tangl.story.episode import Action
from tangl.story.fabula.world import World
from tangl.vm import Ledger, ResolutionPhase


def _script(clinic: dict, call: dict) -> dict:
    return {
        "label": "call_world",
        "metadata": {"title": "Calls", "start_at": "s.road"},
        "scenes": {
            "s": {
                "blocks": {
                    "road": {
                        "label": "road",
                        "content": "You are on the road.",
                        "locals": {"treated": 0},
                        "actions": [
                            {"text": "Get medical help", "successor": "clinic", **call},
                            {"text": "Drive on", "successor": "town"},
                        ],
                    },
                    "clinic": {"label": "clinic", "content": "The doctor patches you up.", **clinic},
                    "exam": {
                        "label": "exam",
                        "content": "The exam room.",
                        "actions": [{"text": "Stale", "successor": "town"}],
                    },
                    "town": {"label": "town", "content": "Town."},
                }
            }
        },
    }


def _graph(
    label: str,
    *,
    clinic: dict | None = None,
    call: dict | None = None,
    init_mode: InitMode = InitMode.EAGER,
):
    world = World.from_script_data(
        script_data=_script(clinic or {}, call if call is not None else {"return": True})
    )
    return world.create_story(label, init_mode=init_mode).graph


def _node(graph, label: str):
    return next(n for n in graph.find_nodes(Selector()) if n.get_label() == label)


def _edge(graph, source: str, text: str):
    return next(
        edge
        for edge in _node(graph, source).edges_out(Selector(has_kind=Action))
        if edge.text == text
    )


def _visit(graph):
    ledger = Ledger.from_graph(graph=graph, entry_id=_node(graph, "road").uid)
    ledger.resolve_choice(_edge(graph, "road", "Get medical help").uid)
    return ledger


def test_a_call_returns_the_reader_to_the_caller() -> None:
    ledger = _visit(_graph("call_story"))

    assert ledger.cursor.get_label() == "road"
    # It really went through the clinic rather than never leaving.
    assert [ledger.graph.get(uid).get_label() for uid in ledger.cursor_history] == [
        "road",
        "clinic",
        "road",
    ]


def test_the_destination_still_runs_its_effects() -> None:
    # Effects run in the destination's own namespace, as they do anywhere else.
    graph = _graph(
        "call_effects",
        clinic={"locals": {"treated": 0}, "effects": ["treated = treated + 1"]},
    )
    ledger = _visit(graph)

    assert _node(graph, "clinic").locals["treated"] == 1
    assert ledger.cursor.get_label() == "road"


def test_without_return_the_reader_stays_where_the_choice_led() -> None:
    ledger = _visit(_graph("plain_story", call={}))

    assert ledger.cursor.get_label() == "clinic"


def test_the_caller_offers_its_choices_again_on_return() -> None:
    ledger = _visit(_graph("call_choices"))
    offered = {
        fragment.text
        for fragment in ledger.get_journal()
        if isinstance(fragment, ChoiceFragment)
        and fragment.step >= ledger.current_update_start_step
    }

    assert offered == {"Get medical help", "Drive on"}


def test_the_call_is_marked_on_the_edge() -> None:
    graph = _graph("call_edge")

    assert _edge(graph, "road", "Get medical help").return_phase is ResolutionPhase.PLANNING
    assert _edge(graph, "road", "Drive on").return_phase is None


def test_a_called_destination_offers_its_selectable_choices() -> None:
    """A call suspends at its callee until the reader selects its action."""
    graph = _graph(
        "call_nested",
        clinic={"actions": [{"text": "Ask about the scar", "successor": "town"}]},
    )
    ledger = _visit(graph)
    offered = {
        fragment.text
        for fragment in ledger.get_journal()
        if isinstance(fragment, ChoiceFragment)
        and fragment.step >= ledger.current_update_start_step
    }

    assert ledger.cursor.get_label() == "clinic"
    assert ledger.call_stack_ids == [_edge(graph, "road", "Get medical help").uid]
    assert offered == {"Ask about the scar"}
    content = [
        getattr(fragment, "content", None)
        for fragment in ledger.get_journal()
        if getattr(fragment, "step", -1) >= ledger.current_update_start_step
    ]
    assert "The doctor patches you up." in content

    ledger.resolve_choice(_edge(graph, "clinic", "Ask about the scar").uid)

    assert ledger.cursor.get_label() == "road"
    assert _offered_now(ledger) == {"Get medical help", "Drive on"}


def test_the_same_block_reached_without_a_call_still_offers_its_choices() -> None:
    # The withholding is about how the reader arrived, not about the block.
    graph = _graph(
        "plain_nested",
        clinic={"actions": [{"text": "Ask about the scar", "successor": "town"}]},
        call={},
    )
    ledger = _visit(graph)
    offered = {
        fragment.text
        for fragment in ledger.get_journal()
        if isinstance(fragment, ChoiceFragment)
        and fragment.step >= ledger.current_update_start_step
    }

    assert ledger.cursor.get_label() == "clinic"
    assert offered == {"Ask about the scar"}


def _offered_now(ledger) -> set[str]:
    return {
        fragment.text
        for fragment in ledger.get_journal()
        if isinstance(fragment, ChoiceFragment)
        and fragment.step >= ledger.current_update_start_step
    }


def test_redirecting_intermediate_block_does_not_publish_stale_choices() -> None:
    """Only the redirect's final block can publish a live call choice."""
    graph = _graph(
        "call_continues",
        clinic={
            "actions": [{"text": "Stale clinic choice", "successor": "town"}],
            "continues": [{"successor": "exam", "trigger": "last"}],
        },
    )
    ledger = _visit(graph)

    assert [ledger.graph.get(uid).get_label() for uid in ledger.cursor_history] == [
        "road",
        "clinic",
        "exam",
    ]
    assert ledger.cursor.get_label() == "exam"
    assert _offered_now(ledger) == {"Stale"}


def test_lazy_called_destination_keeps_a_viable_unresolved_choice_open() -> None:
    """Selection-time provisioning counts as a selectable call continuation."""
    graph = _graph(
        "lazy_call",
        clinic={"actions": [{"text": "Ask about the scar", "successor": "town"}]},
        init_mode=InitMode.LAZY,
    )
    ledger = _visit(graph)

    assert ledger.cursor.get_label() == "clinic"
    assert ledger.call_stack_ids == [_edge(graph, "road", "Get medical help").uid]
    assert _offered_now(ledger) == {"Ask about the scar"}

    ledger.resolve_choice(_edge(graph, "clinic", "Ask about the scar").uid)

    assert ledger.cursor.get_label() == "road"
    assert ledger.call_stack_ids == []


def test_unavailable_called_action_does_not_hold_the_call_open() -> None:
    """A rendered-but-unavailable Story choice is not a call continuation."""
    graph = _graph(
        "locked_call",
        clinic={
            "actions": [
                {
                    "text": "Ask about the scar",
                    "successor": "town",
                    "conditions": ["False"],
                }
            ]
        },
    )
    ledger = _visit(graph)

    assert ledger.cursor.get_label() == "road"
    assert ledger.call_stack_ids == []
    assert _offered_now(ledger) == {"Get medical help", "Drive on"}


def test_return_is_declared_script_vocabulary() -> None:
    action = ActionScript(text="Get medical help", successor="clinic", **{"return": "false"})

    assert action.return_ is False
    assert "return" in ActionScript.model_json_schema()["properties"]


def test_an_authored_return_is_parsed_as_a_bool_not_by_truthiness() -> None:
    graph = _graph("return_false_string", call={"return": "false"})

    assert _edge(graph, "road", "Get medical help").return_phase is None


def test_an_authored_return_that_is_not_a_bool_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _graph("return_nonsense", call={"return": "sometimes"})
