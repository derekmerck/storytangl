"""``return: true`` makes a choice a call: go there, then come back.

The VM has had call edges since it was written - the sandbox builds them for an
interaction with ``return_to_location`` - but nothing carried the field from an
authored script, so a gamebook's "return to the paragraph from which you came"
could only be compiled as a dead end.

The call is one-shot: the destination's content and effects land, and the reader
is returned to the caller in the same step. So a destination with choices of its
own cannot stop there and offer them, and it does not journal them either - they
could never be taken from where the reader ends up. A call that waits for the
reader needs the ledger's call stack to survive the step.
"""

from __future__ import annotations

from tangl.core import Selector
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
                    "town": {"label": "town", "content": "Town."},
                }
            }
        },
    }


def _graph(label: str, *, clinic: dict | None = None, call: dict | None = None):
    world = World.from_script_data(
        script_data=_script(clinic or {}, call if call is not None else {"return": True})
    )
    return world.create_story(label, init_mode=InitMode.EAGER).graph


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


def test_a_called_destination_does_not_offer_choices_the_reader_cannot_take() -> None:
    """The reader returns in the same step, so the destination's choices are moot.

    Journalled, they would reach the client as live buttons beside the caller's
    - and a choice id is accepted without checking that its edge starts at the
    cursor, so taking one would jump from the caller along the callee's edge.
    The destination's content still lands; only its choices are withheld.
    """
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

    assert ledger.cursor.get_label() == "road"
    assert offered == {"Get medical help", "Drive on"}
    assert "Ask about the scar" not in offered
    content = [
        getattr(fragment, "content", None)
        for fragment in ledger.get_journal()
        if getattr(fragment, "step", -1) >= ledger.current_update_start_step
    ]
    assert "The doctor patches you up." in content


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
