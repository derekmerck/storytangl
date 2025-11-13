"""Tests covering concept-driven gating for actors and locations."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from tangl.core import StreamRegistry
from tangl.story.concepts.actor.actor import Actor
from tangl.story.concepts.location.location import Location
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


def test_actor_presence_gates_choice() -> None:
    data = {
        "label": "actor_gating",
        "metadata": {"title": "Actor Gating", "author": "Tester"},
        "actors": {
            "guide": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "name": "The Guide",
                "tags": ["npc", "helpful"],
            }
        },
        "scenes": {
            "crossroads": {
                "roles": {
                    "guide": {
                        "obj_cls": "tangl.story.concepts.actor.role.Role",
                        "actor_ref": "guide",
                    }
                },
                "blocks": {
                    "start": {
                        "content": "You stand at a crossroads.",
                        "actions": [
                            {
                                "text": "Ask the Guide for advice",
                                "successor": "guide_advice",
                                "conditions": [
                                "'guide' in [c.label for c in ctx.cursor.get_concepts()]",
                                ],
                            },
                            {
                                "text": "Take the left path",
                                "successor": "left",
                            },
                        ],
                    },
                    "guide_advice": {
                        "content": "The Guide points toward the safest road.",
                        "continues": [
                            {"successor": "start", "trigger": "last"},
                        ],
                    },
                    "left": {
                        "content": "You choose the left path.",
                    },
                },
            }
        },
    }

    ledger = _build_ledger(data)

    frame = ledger.get_frame()
    cursor = frame.cursor
    concepts = cursor.get_concepts()
    guide_actor = next((concept for concept in concepts if concept.label == "guide"), None)
    assert isinstance(guide_actor, Actor)
    assert "guide" in {concept.label for concept in concepts}

    choices = [choice.get_content().replace("_", " ") for choice in cursor.get_choices(ctx=frame.context)]
    assert "Ask the Guide for advice" in choices

    scene = cursor.parent
    assert scene is not None
    roles = getattr(scene, "roles", [])
    assert roles
    role = roles[0]
    assert role.actor is guide_actor

    role.actor = None

    frame = ledger.get_frame()
    refreshed_concepts = frame.cursor.get_concepts()
    assert "guide" not in {concept.label for concept in refreshed_concepts}

    choices = [choice.get_content().replace("_", " ") for choice in frame.cursor.get_choices(ctx=frame.context)]
    assert "Ask the Guide for advice" not in choices


def test_location_based_conditions() -> None:
    data = {
        "label": "location_gating",
        "metadata": {"title": "Location Gating", "author": "Tester"},
        "locations": {
            "camp": {
                "obj_cls": "tangl.story.concepts.location.location.Location",
                "name": "Forest Camp",
                "tags": ["campsite"],
            }
        },
        "scenes": {
            "camp_scene": {
                "settings": {
                    "camp_setting": {
                        "obj_cls": "tangl.story.concepts.location.setting.Setting",
                        "location_ref": "camp",
                    }
                },
                "blocks": {
                    "campfire": {
                        "content": "You arrive at the campfire clearing.",
                        "actions": [
                            {
                                "text": "Rest by the fire",
                                "successor": "rested",
                                "conditions": [
                                "ctx.current_location and ctx.current_location.has_tags({'campsite'})",
                                ],
                            },
                            {
                                "text": "Leave camp",
                                "successor": "trail",
                            },
                        ],
                    },
                    "rested": {
                        "content": "You rest and recover your strength.",
                    },
                    "trail": {
                        "content": "You head back onto the forest trail.",
                    },
                },
            }
        },
    }

    ledger = _build_ledger(data)

    frame = ledger.get_frame()
    assert isinstance(frame.context.current_location, Location)
    assert frame.context.current_location.label == "camp"

    concepts = frame.cursor.get_concepts()
    assert "camp" in {concept.label for concept in concepts}

    choices = [choice.get_content().replace("_", " ") for choice in frame.cursor.get_choices(ctx=frame.context)]
    assert "Rest by the fire" in choices
    assert "Leave camp" in choices

    camp_location = ledger.graph.find_one(label="camp")
    assert isinstance(camp_location, Location)
    camp_location.tags.discard("campsite")

    frame = ledger.get_frame()
    refreshed_concepts = frame.cursor.get_concepts()
    assert "camp" in {concept.label for concept in refreshed_concepts}

    choices = [choice.get_content().replace("_", " ") for choice in frame.cursor.get_choices(ctx=frame.context)]
    assert "Rest by the fire" not in choices
    assert "Leave camp" in choices

    assert frame.context.current_location is camp_location
