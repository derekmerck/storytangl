"""What a block's UPDATE changes, the rest of its own pass reads.

A pass runs UPDATE, then JOURNAL, FINALIZE and the triggered continues, all
against one cached namespace per node. When that cache was built before UPDATE,
everything after it read pre-update state: a block that set a key could not
continue on it, and its content rendered the old value. The effects are set in
code because authored YAML cannot yet place an effect at FINALIZE.
"""

from __future__ import annotations

from tangl.story import InitMode
from tangl.story.fabula.world import World
from tangl.vm import Ledger, ResolutionPhase
from tangl.vm.traversable import TraversableEffect


def _script() -> dict:
    return {
        "label": "update_visibility",
        "metadata": {"title": "Update visibility", "start_at": "s.start"},
        "globals": {"seen": False, "mood": "quiet"},
        "scenes": {
            "s": {
                "blocks": {
                    "start": {
                        "content": "The room is {mood}.",
                        "continues": [
                            {"successor": "saw_it", "trigger": "last", "conditions": ["seen"]},
                            {"successor": "missed_it", "trigger": "last"},
                        ],
                    },
                    "saw_it": {"content": "Saw it."},
                    "missed_it": {"content": "Missed it."},
                }
            }
        },
    }


def _enter(*, seen_at: ResolutionPhase = ResolutionPhase.UPDATE) -> Ledger:
    world = World.from_script_data(script_data=_script())
    graph = world.create_story("update_visibility", init_mode=InitMode.EAGER).graph
    start = graph.get(graph.initial_cursor_id)
    start.effects = [
        TraversableEffect(expr="graph.locals['seen'] = True", trigger_phase=seen_at),
        TraversableEffect(expr="graph.locals['mood'] = 'loud'"),
    ]
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame.goto_node(ledger.cursor)
    ledger.cursor_id = frame.cursor.uid
    ledger.output_stream = frame.output_stream
    return ledger


def test_a_block_continues_on_the_key_its_own_update_set() -> None:
    ledger = _enter()

    assert ledger.graph.locals["seen"] is True
    assert ledger.cursor.get_label() == "saw_it"


def test_a_block_renders_the_value_its_own_update_set() -> None:
    ledger = _enter()

    text = [getattr(r, "content", "") for r in ledger.output_stream]
    assert "The room is loud." in text


def test_a_block_continues_on_the_key_its_own_finalize_set() -> None:
    ledger = _enter(seen_at=ResolutionPhase.FINALIZE)

    assert ledger.graph.locals["seen"] is True
    assert ledger.cursor.get_label() == "saw_it"
