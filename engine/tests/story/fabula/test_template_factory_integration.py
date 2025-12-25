"""Test that templates are registered via visit() traversal."""

from tangl.ir.story_ir import StoryScript
from tangl.story.fabula import ScriptManager


def test_factory_registers_templates_via_visit():
    """Verify from_root_templ includes template dictionaries."""
    script_data = {
        "label": "test_world",
        "metadata": {"title": "Test World", "author": "Tests"},
        "templates": {
            "global_npc": {
                "label": "npc",
                "obj_cls": "tangl.core.graph.node.Node",
            },
        },
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {
                    "start": {},
                    "tavern": {
                        "label": "tavern",
                        "templates": {
                            "bartender": {
                                "label": "bartender",
                                "obj_cls": "tangl.core.graph.node.Node",
                            },
                        },
                    },
                },
                "templates": {
                    "guard": {
                        "label": "guard",
                        "obj_cls": "tangl.core.graph.node.Node",
                    },
                },
            },
        },
    }

    script = StoryScript(**script_data)
    manager = ScriptManager.from_master_script(script)
    factory = manager.template_factory

    labels = {template.label for template in factory.data.values()}

    assert "npc" in labels
    assert "guard" in labels
    assert "bartender" in labels

    npc = factory.find_one(label="npc")
    assert npc.path == "test_world.npc"

    guard = factory.find_one(label="guard")
    assert guard.path == "test_world.village.guard"
    assert guard.get_path_pattern() == "village.*"

    bartender = factory.find_one(label="bartender")
    assert bartender.path == "test_world.village.tavern.bartender"
    assert bartender.get_path_pattern() == "village.tavern"


def test_templates_coexist_with_typed_fields():
    """Verify templates field works alongside actors/locations fields."""
    script_data = {
        "label": "world",
        "metadata": {"title": "Test World", "author": "Tests"},
        "actors": {
            "alice": {
                "label": "alice",
                "name": "Alice",
            },
        },
        "templates": {
            "generic_item": {
                "label": "item",
                "obj_cls": "tangl.core.graph.node.Node",
            },
        },
        "scenes": {
            "intro": {
                "label": "intro",
                "blocks": {"start": {}},
            },
        },
    }

    script = StoryScript(**script_data)
    manager = ScriptManager.from_master_script(script)

    labels = {template.label for template in manager.template_factory.data.values()}
    assert "alice" in labels
    assert "item" in labels
