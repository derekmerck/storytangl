from __future__ import annotations

from uuid import uuid4
from typing import Any

from tangl.core import StreamRegistry
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.ledger import Ledger


def _build_ledger(data: dict[str, Any]) -> Ledger:
    World.clear_instances()
    manager = ScriptManager.from_data(data)
    world = World(label=f"world_{uuid4().hex}", script_manager=manager)
    story = world.create_story(f"story_{uuid4().hex}")
    ledger = Ledger(
        graph=story,
        cursor_id=story.initial_cursor_id,
        records=StreamRegistry(),
        label="test-ledger",
    )
    ledger.push_snapshot()
    ledger.init_cursor()
    return ledger


def test_story_globals_seed_namespace() -> None:
    data = {
        "label": "state_story",
        "metadata": {"title": "State Story", "author": "Test Author"},
        "globals": {"has_key": False, "visited": False},
        "scenes": {
            "start": {
                "blocks": {
                    "door": {
                        "content": "You stand before a locked door.",
                    }
                }
            }
        },
    }

    ledger = _build_ledger(data)
    assert ledger.graph.locals == {"has_key": False, "visited": False}

    frame = ledger.get_frame()
    ns = frame.context.get_ns(frame.cursor)
    assert ns["has_key"] is False
    assert ns["visited"] is False


def test_action_conditions_and_effects_update_state() -> None:
    data = {
        "label": "conditional_story",
        "metadata": {"title": "Conditional Story", "author": "Test Author"},
        "globals": {"has_key": False},
        "scenes": {
            "start": {
                "blocks": {
                    "door": {
                        "content": "A heavy door blocks your way.",
                        "actions": [
                            {
                                "text": "Search the room",
                                "successor": "found",
                                "conditions": ["not has_key"],
                                "effects": ["has_key = True"],
                            },
                            {
                                "text": "Unlock the door",
                                "successor": "open",
                                "conditions": ["has_key"],
                            },
                        ],
                    },
                    "found": {
                        "content": "You find a rusty key hidden under a loose stone.",
                        "continues": [
                            {"successor": "door", "trigger": "last"},
                        ],
                    },
                    "open": {
                        "content": "The door swings open and the path is clear.",
                    },
                }
            }
        },
    }

    ledger = _build_ledger(data)

    frame = ledger.get_frame()
    initial_choices = frame.cursor.get_choices(ctx=frame.context)
    assert [choice.get_content().replace("_", " ") for choice in initial_choices] == [
        "Search the room"
    ]

    search_choice = initial_choices[0]
    frame.resolve_choice(search_choice)
    ledger.cursor_id = frame.cursor_id
    ledger.step = frame.step

    assert ledger.graph.locals["has_key"] is True

    frame = ledger.get_frame()
    assert frame.cursor.label == "door"
    updated_ns = frame.context.get_ns(frame.cursor)
    assert updated_ns["has_key"] is True

    updated_choices = frame.cursor.get_choices(ctx=frame.context)
    assert [choice.get_content().replace("_", " ") for choice in updated_choices] == [
        "Unlock the door"
    ]
