from uuid import uuid4

from tangl.story.concepts.actor.actor import Actor
from tangl.story.episode.block import Block
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm.provision import ProvisioningPolicy, Requirement, TemplateProvisioner


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


def test_lazy_story_materializes_start_block_only() -> None:
    script = {
        "label": "lazy_world",
        "metadata": {"title": "Lazy World", "author": "Tester", "start_at": "intro.start"},
        "globals": {"gold": 3},
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
    story = world.create_story("lazy_story", mode="lazy")

    blocks = list(story.find_all(is_instance=Block))
    assert len(blocks) == 1

    start_block = blocks[0]
    assert story.initial_cursor_id == start_block.uid
    assert start_block.content == "Welcome!"

    print(world.script_manager.master_script.locals)
    print(world.script_manager.get_story_globals())
    print(story.locals)

    assert story.locals.get("gold") == 3

    assert story.edges == []


def test_lazy_story_scoped_templates_respect_cursor_scope() -> None:
    script = {
        "label": "lazy_world_templates",
        "metadata": {"title": "Lazy Templates", "author": "Tester", "start_at": "intro.start"},
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "obj_cls": "tangl.story.episode.block.Block",
                        "templates": {
                            "start_actor": {
                                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                                "name": "Starter",
                            }
                        },
                    }
                }
            },
            "elsewhere": {
                "blocks": {
                    "later": {
                        "obj_cls": "tangl.story.episode.block.Block",
                        "templates": {
                            "late_actor": {
                                "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                                "name": "Elsewhere",
                            }
                        },
                    }
                }
            },
        },
    }

    world = _build_world(script)
    story = world.create_story("lazy_story", mode="lazy")

    start_block = story.find_one(is_instance=Block)
    assert start_block is not None

    provisioner = TemplateProvisioner(template_registry=world.template_registry, layer="local")
    ctx = type("Ctx", (), {"graph": story, "cursor": start_block, "cursor_id": start_block.uid})()

    in_scope_req = Requirement(
        graph=story,
        template_ref="start_actor",
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )
    offers = list(provisioner.get_dependency_offers(in_scope_req, ctx=ctx))
    assert len(offers) == 1

    out_of_scope_req = Requirement(
        graph=story,
        template_ref="late_actor",
        policy=ProvisioningPolicy.CREATE_TEMPLATE,
    )
    out_of_scope_offers = list(provisioner.get_dependency_offers(out_of_scope_req, ctx=ctx))
    assert out_of_scope_offers == []

