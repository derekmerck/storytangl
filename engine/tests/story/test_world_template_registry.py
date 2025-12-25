"""Tests for template compilation and helpers on :class:`World`."""

from tangl.ir.core_ir import MasterScript, ScriptMetadata
from tangl.ir.story_ir import ActorScript, BlockScript, LocationScript, StoryScript
# from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.story.concepts.actor import Actor
from tangl.story.concepts.location import Location
from tangl.story.episode.block import Block
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World


def test_world_initializes_template_factory_without_templates() -> None:
    World.clear_instances()

    metadata = ScriptMetadata(title="Example", author="Tests")
    master_script = MasterScript(label="example", metadata=metadata)
    manager = ScriptManager.from_master_script(master_script=master_script)

    try:
        world = World(
            label="example",
            script_manager=manager,
            domain_manager=DomainManager(),
            asset_manager=AssetManager(),
            resource_manager=None,
            metadata=manager.get_story_metadata(),
        )

        factory = world.script_manager.template_factory
        assert factory.label == "example_factory"
        templates = [
            template
            for template in factory.find_all()
            if template.is_instance((Actor, Location, Block))
        ]
        assert templates == []
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
    manager = ScriptManager.from_master_script(master_script=script)

    try:
        world = World(
            label="example",
            script_manager=manager,
            domain_manager=DomainManager(),
            asset_manager=AssetManager(),
            resource_manager=None,
            metadata=manager.get_story_metadata(),
        )

        factory = world.script_manager.template_factory
        templates = {
            template.label: template
            for template in factory.find_all()
            if template.is_instance((Actor, Location, Block))
        }

        assert set(templates) == {"global.guard", "scene.guard", "block.market", "town_intro"}

        global_template = templates["global.guard"]
        assert global_template.is_instance(Actor)
        assert global_template.get_selection_criteria().get("has_path") == "*"

        scene_template = templates["scene.guard"]
        assert scene_template.is_instance(Actor)
        assert scene_template.get_selection_criteria().get("has_path") == "town.*"

        block_template = templates["block.market"]
        assert block_template.is_instance(Location)
        assert block_template.get_selection_criteria().get("has_path") == "town.town_intro"

        block_script = templates["town_intro"]
        assert isinstance(block_script, BlockScript)
        assert block_script.get_selection_criteria().get("has_path") == "town.*"

        actor_labels = sorted(
            template.label for template in world.script_manager.find_actors()
        )
        assert actor_labels == ["global.guard", "scene.guard"]

        location_labels = [
            template.label for template in world.script_manager.find_locations()
        ]
        assert location_labels == ["block.market"]

        assert world.find_template("scene.guard") is scene_template
    finally:
        World.clear_instances()
