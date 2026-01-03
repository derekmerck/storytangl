from __future__ import annotations

from uuid import uuid4

from tangl.story.episode.block import Block
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.world import World
from tangl.loaders.compilers.script_compiler import ScriptCompiler


def _build_world(script: dict) -> World:
    World.clear_instances()
    manager = ScriptCompiler().compile(script)
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
            "intro": {
                "obj_cls": "tangl.story.episode.scene.Scene",
                "label": "intro",
                "templates": {
                    "start": {
                        "obj_cls": "tangl.story.episode.block.Block",
                        "content": "Welcome!",
                        "declares_instance": True,
                    }
                },
            },
            "guard": {
                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                "name": "Guard",
            }
        },
        "scenes": {},
    }

    world = _build_world(script)
    story = world.create_story("full_story", mode="full")

    block = story.find_one(is_instance=Block, label="start")
    assert block is not None
    assert block.path == "intro.start"
    assert story.find_one(label="guard") is None
    assert world.script_manager.template_factory.find_one(label="guard") is not None
