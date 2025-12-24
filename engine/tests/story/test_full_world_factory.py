from __future__ import annotations

from uuid import uuid4

from tangl.story.concepts.actor.actor import Actor
from tangl.story.episode.block import Block
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World


def _build_world(script: dict) -> World:
    World.clear_instances()
    manager = ScriptManager.from_data(script)
    return World(
        label=f"world_{uuid4().hex}",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=manager.get_story_metadata(),
    )


def test_full_story_materializes_blocks_with_scope() -> None:
    script = {
        "label": "full_world",
        "metadata": {"title": "Full World", "author": "Tester", "start_at": "intro.start"},
        "templates": {
            "guard": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "name": "Guard",
            }
        },
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "obj_cls": "tangl.story.episode.block.Block",
                        "content": "Welcome!",
                    }
                }
            }
        },
    }

    world = _build_world(script)
    story = world.create_story("full_story", mode="full")

    block = story.find_one(is_instance=Block, label="start")
    assert block is not None
    assert block.parent is not None
    assert block.parent.label == "intro"

    guard = story.find_one(is_instance=Actor, label="guard")
    assert guard is not None
