"""End-to-end tests for template factory population and queries."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from tangl.ir.core_ir.script_metadata_model import ScriptMetadata
from tangl.ir.story_ir import ActorScript, BlockScript, LocationScript, SceneScript, StoryScript
# from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.story.concepts.actor import Actor
from tangl.story.concepts.location import Location
from tangl.story.episode.block import Block
from tangl.story.fabula.asset_manager import AssetManager
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.story.story_graph import StoryGraph

ACTOR_CLASS = "tangl.story.concepts.actor.actor.Actor"
LOCATION_CLASS = "tangl.story.concepts.location.location.Location"


@pytest.fixture(autouse=True)
def clear_world_singleton() -> None:
    """Reset the ``World`` singleton registry between tests."""

    World.clear_instances()
    yield
    World.clear_instances()


def build_world(story_data: dict[str, Any]) -> World:
    """Helper that validates ``story_data`` and instantiates a ``World``."""

    script = StoryScript.model_validate(story_data)
    manager = ScriptManager.from_master_script(master_script=script)
    return World(
        label=story_data["label"],
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=story_data.get("metadata", {}),
    )


def _collect_templates(world: World) -> dict[str, ActorScript | LocationScript | BlockScript]:
    return {
        template.label: template
        for template in world.script_manager.find_templates()
        if template.is_instance((Actor, Location, Block))
    }


def test_world_level_templates_have_global_scope() -> None:
    """Top-level templates should be registered without scope constraints."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "global.guard": {"obj_cls": ACTOR_CLASS, "tags": {"global"}},
        },
        "scenes": {},
    }

    world = build_world(story_data)
    templates = _collect_templates(world)

    assert set(templates) == {"global.guard"}
    assert templates["global.guard"].get_selection_criteria().get("has_path") == "*"


def test_scene_level_templates_have_parent_scope() -> None:
    """Scene templates should inherit a ``parent_label`` constraint."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {},
                "templates": {
                    "scene.guard": {"obj_cls": ACTOR_CLASS},
                },
            }
        },
    }

    world = build_world(story_data)
    templates = _collect_templates(world)

    scene_template = templates["scene.guard"]
    assert scene_template.is_instance(Actor)
    assert scene_template.get_selection_criteria().get("has_path") == "village.*"

    graph = StoryGraph(label="scene_scope", world=world)
    village = graph.add_subgraph(label="village")
    cursor = graph.add_node(label="start")
    village.add_member(cursor)
    factory = world.script_manager.template_factory
    scoped = factory.find_one(identifier="scene.guard", selector=cursor)
    assert scoped == scene_template


def test_block_level_templates_have_parent_scope() -> None:
    """Block templates should inherit a ``parent_label`` constraint."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {
                    "market": {
                        "label": "market",
                        "templates": {
                            "block.market": {"obj_cls": LOCATION_CLASS},
                        },
                    }
                },
            }
        },
    }

    world = build_world(story_data)
    templates = _collect_templates(world)

    block_template = templates["block.market"]
    assert block_template.is_instance(Location)
    assert block_template.get_selection_criteria().get("has_path") == "village.market"

    graph = StoryGraph(label="block_scope", world=world)
    village = graph.add_subgraph(label="village")
    cursor = graph.add_node(label="market")
    village.add_member(cursor)
    factory = world.script_manager.template_factory
    scoped = factory.find_one(identifier="block.market", selector=cursor)
    assert scoped == block_template


def test_block_scripts_default_to_scene_scope() -> None:
    """Block scripts registered in the factory should inherit scene scope."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {
                    "market": {
                        "label": "market",
                        "block_cls": "tangl.story.episode.block.Block",
                    }
                },
            }
        },
    }

    world = build_world(story_data)
    factory = world.script_manager.template_factory

    block_script = factory.find_one(label="market", is_instance=BlockScript)
    assert block_script is not None
    criteria = block_script.get_selection_criteria()
    assert criteria.get("has_path") == "village.*"


def test_explicit_scope_overrides_inferred() -> None:
    """Explicit ``scope`` entries from content should not be overridden."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {},
                "templates": {
                    "scene.guard": {"obj_cls": ACTOR_CLASS, "path_pattern": None},
                },
            }
        },
    }

    world = build_world(story_data)
    templates = _collect_templates(world)

    explicit_template = templates["scene.guard"]
    assert explicit_template.get_selection_criteria().get("has_path") is None


def test_inline_templates_respect_explicit_none_scope() -> None:
    """Inline script instances should preserve ``scope=None`` even in nested contexts."""

    inline_template = ActorScript(label="scene_guard", path_pattern=None)
    block = BlockScript.model_construct(label="village.market")
    scene_script = SceneScript.model_construct(
        label="village",
        blocks={"village.market": block},
        templates={"scene_guard": inline_template},
    )
    script = StoryScript.model_construct(
        label="example",
        metadata=ScriptMetadata(title="Example", author="Tests"),
        scenes={"village": scene_script},
    )

    manager = ScriptManager.from_master_script(master_script=script)
    world = World(
        label="example",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=manager.get_story_metadata(),
    )
    templates = _collect_templates(world)

    inline_scene_template = templates["scene_guard"]
    assert inline_scene_template.get_selection_criteria().get("has_path") is None


def test_template_factory_queries() -> None:
    """Factory helpers should expose type, tag, and attribute filtering."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "global.guard": {
                "obj_cls": ACTOR_CLASS,
                "tags": {"npc", "guard"},
                "archetype": "guard",
            },
            "global.merchant": {
                "obj_cls": ACTOR_CLASS,
                "tags": {"npc"},
                "archetype": "merchant",
            },
        },
        "scenes": {
            "market": {
                "label": "market",
                "blocks": {},
                "templates": {
                    "scene.booth": {"obj_cls": LOCATION_CLASS, "tags": {"shop"}},
                },
            }
        },
    }

    world = build_world(story_data)

    guard = world.find_template("global.guard")
    assert guard is not None
    assert guard.archetype == "guard"

    actor_templates = list(world.script_manager.find_actors())
    assert sorted(template.label for template in actor_templates) == ["global.guard", "global.merchant"]

    npc_templates = list(world.script_manager.find_templates(has_tags={"npc"}))
    assert {template.label for template in npc_templates} == {"global.guard", "global.merchant"}

    guard_archetypes = list(world.script_manager.find_templates(archetype="guard"))
    assert [template.label for template in guard_archetypes] == ["global.guard"]


def test_templates_are_records_with_uids() -> None:
    """Registered templates should expose record semantics such as ``uid``."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "global.guard": {
                "obj_cls": ACTOR_CLASS,
                "tags": {"npc"},
                "archetype": "guard",
            }
        },
        "scenes": {},
    }

    world = build_world(story_data)
    templates = _collect_templates(world)

    guard = templates["global.guard"]
    assert isinstance(guard.uid, UUID)
    assert guard.matches(archetype="guard")
    assert guard.get_label() == "global.guard"


def test_duplicate_labels_allowed_with_different_scopes() -> None:
    """Templates with same label but different scopes should both register."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "guard": {"obj_cls": ACTOR_CLASS, "tags": {"global"}},
        },
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {},
                "templates": {
                    "guard": {"obj_cls": ACTOR_CLASS, "tags": {"village"}},
                },
            }
        },
    }

    world = build_world(story_data)
    all_guards = list(world.script_manager.find_templates(identifier="guard"))

    assert len(all_guards) == 2

    global_guard = next(t for t in all_guards if "global" in t.tags)
    village_guard = next(t for t in all_guards if "village" in t.tags)

    assert global_guard.get_selection_criteria().get("has_path") == "*"
    assert village_guard.get_selection_criteria().get("has_path") == "village.*"

    factory = world.script_manager.template_factory
    graph = StoryGraph(label="village_scope", world=world)
    village = graph.add_subgraph(label="village")
    cursor = graph.add_node(label="marker")
    village.add_member(cursor)

    assert factory.find_one(identifier="guard") is not None
    scoped = world.script_manager.find_template(identifier="guard", selector=cursor)
    assert scoped == village_guard


def test_registry_finds_template_by_path() -> None:
    """Registry should resolve templates by qualified label identifier."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "scenes": {
            "scene1": {
                "label": "scene1",
                "blocks": {},
                "templates": {
                    "start": {"obj_cls": ACTOR_CLASS},
                },
            },
            "scene2": {
                "label": "scene2",
                "blocks": {},
                "templates": {
                    "start": {"obj_cls": ACTOR_CLASS},
                },
            }
        },
    }

    world = build_world(story_data)

    all_templates = list(world.script_manager.find_templates(identifier="start"))
    assert len(all_templates) == 2

    graph = StoryGraph(label="registry_path", world=world)
    scene1 = graph.add_subgraph(label="scene1")
    scene2 = graph.add_subgraph(label="scene2")
    scene1_cursor = graph.add_node(label="start_one")
    scene2_cursor = graph.add_node(label="start_two")
    scene1.add_member(scene1_cursor)
    scene2.add_member(scene2_cursor)

    scene1_start = world.script_manager.find_template(
        identifier="start",
        selector=scene1_cursor,
    )
    scene2_start = world.script_manager.find_template(
        identifier="start",
        selector=scene2_cursor,
    )

    assert scene1_start is not None
    assert scene2_start is not None
    assert scene1_start.uid != scene2_start.uid
    assert scene1_start.get_selection_criteria().get("has_path") == "scene1.*"
    assert scene2_start.get_selection_criteria().get("has_path") == "scene2.*"


def test_block_scripts_registered_as_templates() -> None:
    """BlockScript objects should be registered in template registry."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "scenes": {
            "scene1": {
                "label": "scene1",
                "blocks": {
                    "start": {
                        "label": "start",
                        "text": "Beginning of story",
                    },
                    "next": {
                        "label": "next",
                        "text": "Second block",
                    },
                },
            }
        },
    }

    world = build_world(story_data)

    factory = world.script_manager.template_factory
    start_template = factory.find_one(path="example.scene1.start")
    next_template = factory.find_one(path="example.scene1.next")

    assert start_template is not None
    assert isinstance(start_template, BlockScript)
    assert start_template.text == "Beginning of story"

    assert next_template is not None
    assert isinstance(next_template, BlockScript)
    assert next_template.text == "Second block"

    assert start_template.get_selection_criteria().get("has_path") == "scene1.*"
    assert next_template.get_selection_criteria().get("has_path") == "scene1.*"


def test_block_templates_coexist_with_concept_templates() -> None:
    """Block templates and concept templates should coexist in registry."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "guard": {"obj_cls": ACTOR_CLASS},
        },
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {
                    "start": {"label": "start", "text": "Village square"},
                },
                "templates": {
                    "elder": {"obj_cls": ACTOR_CLASS},
                },
            }
        },
    }

    world = build_world(story_data)
    all_templates = _collect_templates(world)

    assert len(all_templates) == 3

    labels = set(all_templates)
    assert labels == {"guard", "elder", "start"}

    start_block = world.script_manager.find_template(identifier="village.start")
    assert isinstance(start_block, BlockScript)


def test_block_script_has_template_interface() -> None:
    """BlockScript should implement required template interface."""

    block = BlockScript(
        label="test",
        path_pattern="scene1.*",
        text="Test block",
    )

    assert hasattr(block, "uid")
    assert hasattr(block, "label")
    assert block.has_identifier("test")

    assert hasattr(block, "matches")
    assert hasattr(block, "get_selection_criteria")

    assert hasattr(block, "content_hash")

    assert block.path == "test"
    assert block.get_selection_criteria().get("has_path") == "scene1.*"


def test_block_script_scope_is_immutable() -> None:
    """Modifying BlockScript should not mutate original object."""

    original = BlockScript(label="test", text="Original")
    assert original.get_selection_criteria().get("has_path") is None

    modified = original.model_copy(
        update={"req_path_pattern": "scene1.*"}
    )

    assert original.get_selection_criteria().get("has_path") is None
    assert modified.get_selection_criteria().get("has_path") == "scene1.*"

    assert original is not modified


def test_inline_location_template_preserves_concrete_type() -> None:
    """Inline ``LocationScript`` objects should remain locations after registration."""

    inline_location = LocationScript(label="hideout")

    metadata = ScriptMetadata.model_construct(title="Example", author="Tests")
    script = StoryScript.model_construct(
        label="example",
        metadata=metadata,
        templates={"hideout": inline_location},
        scenes={},
    )
    manager = ScriptManager.from_master_script(master_script=script)
    world = World(
        label="example",
        script_manager=manager,
        domain_manager=DomainManager(),
        asset_manager=AssetManager(),
        resource_manager=None,
        metadata=manager.get_story_metadata(),
    )

    template = world.find_template("hideout")
    assert isinstance(template, LocationScript)

    location_labels = {
        location.label for location in world.script_manager.find_locations()
    }
    assert location_labels == {"hideout"}


def test_templates_with_different_scopes_have_different_content_hashes() -> None:
    """Scope changes should alter the content hash."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "global.guard": {
                "obj_cls": ACTOR_CLASS,
                "archetype": "guard",
                "hp": 50,
            }
        },
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {},
                "templates": {
                    "scene.guard": {
                        "obj_cls": ACTOR_CLASS,
                        "archetype": "guard",
                        "hp": 50,
                        "path_pattern": "village.*",
                    }
                },
            }
        },
    }

    world = build_world(story_data)
    templates = _collect_templates(world)

    guard_global = templates["global.guard"]
    guard_scene = templates["scene.guard"]

    assert guard_global.label != guard_scene.label
    assert guard_global.get_selection_criteria().get("has_path") == "*"
    assert guard_scene.get_selection_criteria().get("has_path") == "village.*"
    assert guard_global.content_hash is not None
    assert guard_scene.content_hash is not None
    assert guard_global.content_hash != guard_scene.content_hash


def test_templates_with_different_structure_have_different_hashes() -> None:
    """Distinct template content should produce unique hashes."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "global.guard": {
                "obj_cls": ACTOR_CLASS,
                "archetype": "guard",
                "hp": 50,
            },
            "global.wizard": {
                "obj_cls": ACTOR_CLASS,
                "archetype": "wizard",
                "hp": 30,
            },
        },
        "scenes": {},
    }

    world = build_world(story_data)
    templates = _collect_templates(world)

    guard = templates["global.guard"]
    wizard = templates["global.wizard"]

    assert guard.content_hash is not None
    assert wizard.content_hash is not None
    assert guard.content_hash != wizard.content_hash


def test_template_content_hash_is_deterministic() -> None:
    """Rehydrating the same template data should yield the same hash."""

    template_payload = {
        "obj_cls": ACTOR_CLASS,
        "archetype": "guard",
        "hp": 50,
    }

    template_one = ActorScript.model_validate({**template_payload, "label": "guard"})
    template_two = ActorScript.model_validate({**template_payload, "label": "guard"})

    assert template_one.uid != template_two.uid
    assert template_one.content_hash == template_two.content_hash


def test_template_scope_included_in_content_hash() -> None:
    """Changing scope metadata should alter the hash."""

    template_global = ActorScript.model_validate(
        {
            "label": "guard.global",
            "obj_cls": ACTOR_CLASS,
            "archetype": "guard",
            "path_pattern": None,
        }
    )

    template_scoped = ActorScript.model_validate(
        {
            "label": "guard.scoped",
            "obj_cls": ACTOR_CLASS,
            "archetype": "guard",
            "path_pattern": "village.*",
        }
    )

    assert template_global.get_selection_criteria().get("has_path") is None
    assert template_scoped.get_selection_criteria().get("has_path") == "village.*"
    assert template_global.content_hash != template_scoped.content_hash


def test_template_exposes_content_identifier_helper() -> None:
    """Templates should surface a short content identifier for logging."""

    template = ActorScript.model_validate(
        {
            "label": "guard.identifier",
            "obj_cls": ACTOR_CLASS,
            "archetype": "guard",
        }
    )

    identifier = template.content_identifier()
    assert isinstance(identifier, str)
    assert len(identifier) == 16
    assert identifier == template.content_hash.hex()[:16]
