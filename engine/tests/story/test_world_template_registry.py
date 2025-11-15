"""Tests for template compilation and helpers on :class:`World`."""

from tangl.ir.core_ir import MasterScript, ScriptMetadata
from tangl.ir.story_ir import ActorScript, LocationScript, StoryScript
from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World


def test_world_initializes_template_registry_without_templates() -> None:
    World.clear_instances()

    metadata = ScriptMetadata(title="Example", author="Tests")
    master_script = MasterScript(label="example", metadata=metadata)
    manager = ScriptManager(master_script=master_script)

    try:
        world = World(label="example", script_manager=manager)

        assert world.template_registry.label == "example_templates"
        assert list(world.template_registry.find_all()) == []
    finally:
        World.clear_instances()


def test_world_compiles_templates_with_scope_inference() -> None:
    World.clear_instances()

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "global.guard": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "tags": {"global"},
            }
        },
        "scenes": {
            "town": {
                "label": "town",
                "blocks": {
                    "town.intro": {
                        "label": "town.intro",
                        "templates": {
                            "block.market": {
                                "obj_cls": "tangl.story.concepts.location.location.Location",
                                "tags": {"market"},
                            }
                        },
                    }
                },
                "templates": {
                    "scene.guard": {
                        "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                        "tags": {"scene"},
                    }
                },
            }
        },
    }
    script = StoryScript.model_validate(story_data)
    manager = ScriptManager(master_script=script)

    try:
        world = World(label="example", script_manager=manager)

        templates = {template.label: template for template in world.template_registry.find_all()}

        assert set(templates) == {"global_guard", "scene_guard", "block_market"}

        global_template = templates["global_guard"]
        assert isinstance(global_template, ActorScript)
        assert global_template.scope is None

        scene_template = templates["scene_guard"]
        assert isinstance(scene_template, ActorScript)
        assert scene_template.scope is not None
        assert scene_template.scope.model_dump() == ScopeSelector(parent_label="town").model_dump()

        block_template = templates["block_market"]
        assert isinstance(block_template, LocationScript)
        assert block_template.scope is not None
        assert block_template.scope.model_dump() == ScopeSelector(source_label="town_intro").model_dump()

        actor_labels = sorted(template.label for template in world.actor_templates)
        assert actor_labels == ["global_guard", "scene_guard"]

        location_labels = [template.label for template in world.location_templates]
        assert location_labels == ["block_market"]

        assert world.find_template("scene_guard") is scene_template
    finally:
        World.clear_instances()
