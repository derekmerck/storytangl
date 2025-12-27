"""Test that template dicts auto-convert to BaseScriptItem with correct paths."""

from tangl.ir.core_ir import BaseScriptItem
from tangl.ir.story_ir import StoryScript


def test_templates_convert_to_basescriptitem():
    """Verify Pydantic converts dict → BaseScriptItem in templates field."""
    script_data = {
        "label": "test_world",
        "metadata": {"title": "Test World", "author": "Tests"},
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {"start": {}},
                "templates": {
                    "guard": {
                        "label": "guard",
                        "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                        "custom_field": "preserved",
                    }
                },
            }
        },
    }

    script = StoryScript(**script_data)

    village = script.scenes["village"]
    assert "guard" in village.templates

    guard = village.templates["guard"]
    assert isinstance(guard, BaseScriptItem)
    assert guard.label == "guard"

    assert hasattr(guard, "custom_field")
    assert guard.custom_field == "preserved"


def test_template_path_computation():
    """Verify templates get correct hierarchical paths."""
    script_data = {
        "label": "world",
        "metadata": {"title": "Test World", "author": "Tests"},
        "templates": {
            "global_npc": {},
        },
        "scenes": {
            "village": {
                "label": "village",
                "templates": {
                    "guard": {"label": "guard"},
                },
                "blocks": {
                    "tavern": {
                        "label": "tavern",
                        "templates": {
                            "bartender": {"label": "bartender"},
                        },
                    }
                },
            }
        },
    }

    script = StoryScript(**script_data)

    global_npc = script.templates["global_npc"]
    assert global_npc.path == "world.global_npc"
    assert global_npc.get_path_pattern() == "*"

    guard = script.scenes["village"].templates["guard"]
    assert guard.path == "world.village.guard"
    assert guard.get_path_pattern() == "village.*"

    bartender = script.scenes["village"].blocks["tavern"].templates["bartender"]
    assert bartender.path == "world.village.tavern.bartender"
    assert bartender.get_path_pattern() == "village.tavern"
