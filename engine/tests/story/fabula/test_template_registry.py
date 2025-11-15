"""End-to-end tests for ``World.template_registry`` population and queries."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from tangl.ir.core_ir.script_metadata_model import ScriptMetadata
from tangl.ir.story_ir import ActorScript, LocationScript, StoryScript
from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World

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
    manager = ScriptManager(master_script=script)
    return World(label=story_data["label"], script_manager=manager)


def _collect_templates(world: World) -> dict[str, ActorScript | LocationScript]:
    return {template.label: template for template in world.template_registry.find_all()}


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

    assert set(templates) == {"global_guard"}
    assert templates["global_guard"].scope is None


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

    scene_template = templates["scene_guard"]
    assert isinstance(scene_template, ActorScript)
    assert scene_template.scope is not None
    assert scene_template.scope.model_dump() == ScopeSelector(parent_label="village").model_dump()


def test_block_level_templates_have_source_scope() -> None:
    """Block templates should inherit a ``source_label`` constraint."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {
                    "market": {
                        "label": "village.market",
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

    block_template = templates["block_market"]
    assert isinstance(block_template, LocationScript)
    assert block_template.scope is not None
    assert block_template.scope.model_dump() == ScopeSelector(source_label="village_market").model_dump()


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
                    "scene.guard": {"obj_cls": ACTOR_CLASS, "scope": None},
                },
            }
        },
    }

    world = build_world(story_data)
    templates = _collect_templates(world)

    explicit_template = templates["scene_guard"]
    assert explicit_template.scope is None


def test_template_registry_queries() -> None:
    """Registry helpers should expose type, tag, and attribute filtering."""

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

    guard = world.find_template("global_guard")
    assert guard is not None
    assert guard.archetype == "guard"

    actor_templates = list(world.actor_templates)
    assert sorted(template.label for template in actor_templates) == ["global_guard", "global_merchant"]

    npc_templates = list(world.template_registry.find_all(has_tags={"npc"}))
    assert {template.label for template in npc_templates} == {"global_guard", "global_merchant"}

    guard_archetypes = list(world.template_registry.find_all(archetype="guard"))
    assert [template.label for template in guard_archetypes] == ["global_guard"]


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

    guard = templates["global_guard"]
    assert isinstance(guard.uid, UUID)
    assert guard.matches(archetype="guard")
    assert guard.get_label() == "global_guard"


def test_duplicate_template_labels_raise_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Duplicate labels should be ignored with a descriptive warning."""

    story_data = {
        "label": "example",
        "metadata": {"title": "Example", "author": "Tests"},
        "templates": {
            "duplicate": {"obj_cls": ACTOR_CLASS},
        },
        "scenes": {
            "village": {
                "label": "village",
                "blocks": {},
                "templates": {
                    "duplicate": {"obj_cls": ACTOR_CLASS},
                },
            }
        },
    }

    with caplog.at_level("WARNING"):
        world = build_world(story_data)

    templates = _collect_templates(world)
    assert list(templates) == ["duplicate"]
    assert any("Duplicate template label duplicate skipped" in message for message in caplog.messages)


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
    manager = ScriptManager(master_script=script)
    world = World(label="example", script_manager=manager)

    template = world.find_template("hideout")
    assert isinstance(template, LocationScript)

    location_labels = {location.label for location in world.location_templates}
    assert location_labels == {"hideout"}
