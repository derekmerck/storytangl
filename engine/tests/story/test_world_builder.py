from __future__ import annotations

from types import SimpleNamespace

from tangl.core import BehaviorRegistry, EntityTemplate, TemplateRegistry
from tangl.story import WorldBuilder
from tangl.story.concepts import Actor
from tangl.story.fabula import StoryCompiler


def _script() -> dict[str, object]:
    return {
        "label": "builder_world",
        "metadata": {"title": "Builder World", "author": "Tests", "start_at": "intro.start"},
        "globals": {"gold": 7},
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Start",
                    }
                }
            }
        },
    }


def test_world_builder_populates_canonical_fields_and_aliases() -> None:
    bundle = StoryCompiler().compile(_script())
    dispatch = BehaviorRegistry(label="builder_dispatch")
    extra = SimpleNamespace(label="builder_extra_authority")
    assets = SimpleNamespace(label="assets")
    resources = SimpleNamespace(label="resources")
    projector = SimpleNamespace(project=lambda *, ledger: ledger)

    world = WorldBuilder().build(
        label="builder_world_runtime",
        bundle=bundle,
        assets=assets,
        resources=resources,
        dispatch=dispatch,
        extra_authorities=[extra],
        class_registry={"Actor": Actor},
        modules=["builder.domain"],
        story_info_projector=projector,
    )

    assert world.templates is bundle.template_registry
    assert world.bundle is bundle
    assert world.metadata == bundle.metadata
    assert world.locals == bundle.locals
    assert world.entry_template_ids == bundle.entry_template_ids
    assert world.find_template("intro.start") is not None
    assert world.assets is assets
    assert world.resources is resources
    assert world.class_registry["Actor"] is Actor
    assert world.dispatch is dispatch
    assert world.get_story_info_projector() is projector
    assert world.get_authorities() == [dispatch, extra]


def test_world_builder_coerces_legacy_domain_and_extra_template_registries() -> None:
    bundle = StoryCompiler().compile(_script())
    extra_templates = TemplateRegistry(label="builder_extra_templates")
    _ = EntityTemplate(
        label="world.extra.actor",
        payload=Actor(label="npc", name="NPC"),
        registry=extra_templates,
    )
    projector = SimpleNamespace(project=lambda *, ledger: ledger)
    domain = SimpleNamespace(
        dispatch_registry=BehaviorRegistry(label="legacy_domain_dispatch"),
        class_registry={"Actor": Actor},
        modules=["legacy.domain"],
        get_authorities=lambda: [],
        get_story_info_projector=lambda: projector,
    )

    world = WorldBuilder().build(
        label="builder_world_legacy",
        bundle=bundle,
        domain=domain,
        extra_template_registries=[extra_templates],
    )

    registries = world.get_template_scope_groups()

    assert world.templates is bundle.template_registry
    assert world.class_registry["Actor"] is Actor
    assert world.dispatch.label == "legacy_domain_dispatch"
    assert world.get_story_info_projector() is projector
    assert registries[0] is bundle.template_registry
    assert extra_templates in registries
