from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.core import BehaviorRegistry, EntityTemplate, TemplateRegistry
from tangl.story import Block, StoryGraph, WorldBuilder
from tangl.story.concepts import Actor
from tangl.story.fabula import StoryCompiler
from tangl.story.fabula import builder as builder_module
from tangl.vm.runtime.frame import PhaseCtx


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

    world = WorldBuilder().build(
        label="builder_world_runtime",
        bundle=bundle,
        assets=assets,
        resources=resources,
        dispatch=dispatch,
        extra_authorities=[extra],
        class_registry={"Actor": Actor},
        modules=["builder.domain"],
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
    assert world.get_authorities() == [dispatch, extra]


def test_world_builder_coerces_legacy_domain_and_extra_template_registries() -> None:
    bundle = StoryCompiler().compile(_script())
    extra_templates = TemplateRegistry(label="builder_extra_templates")
    _ = EntityTemplate(
        label="world.extra.actor",
        payload=Actor(label="npc", name="NPC"),
        registry=extra_templates,
    )
    domain = SimpleNamespace(
        dispatch_registry=BehaviorRegistry(label="legacy_domain_dispatch"),
        class_registry={"Actor": Actor},
        modules=["legacy.domain"],
        get_authorities=lambda: [],
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
    assert registries[0] is bundle.template_registry
    assert extra_templates in registries


@pytest.mark.parametrize("guard_assembly", [False, True])
def test_world_builder_preserves_distinct_equal_authorities(
    monkeypatch: pytest.MonkeyPatch, guard_assembly: bool,
) -> None:
    bundle = StoryCompiler().compile(_script())
    events: list[str] = []
    first = BehaviorRegistry(label="builder_identity")
    first.register(task="builder_identity", func=lambda **_kw: events.append("shared"))
    equal = first.model_copy()
    last = BehaviorRegistry(label="builder_last")
    last.register(task="builder_identity", func=lambda **_kw: events.append("last"))
    marker = object()
    assert first is not equal and first.uid == equal.uid and first == equal

    if guard_assembly:
        original = builder_module._dedupe

        def forbidden(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("authority dedup must not compare or serialize values")

        def guarded(values: list[object]) -> list[object]:
            # Guard only dedup, not World construction or later dispatch.
            with monkeypatch.context() as patch:
                for name in ("__eq__", "eq_by_value", "value_hash", "unstructure"):
                    patch.setattr(BehaviorRegistry, name, forbidden)
                return original(values)

        monkeypatch.setattr(builder_module, "_dedupe", guarded)

    world = WorldBuilder().build(
        label="builder_identity_world", bundle=bundle, dispatch=first,
        extra_authorities=[None, equal, first, marker, last, equal, None],
    )
    assert [id(a) for a in world.extra_authorities] == [id(equal), id(marker), id(last)]
    assert [id(a) for a in world.get_authorities()] == [
        id(first), id(equal), id(marker), id(last),
    ]
    graph = StoryGraph(factory=world)
    caller = Block(label="caller", registry=graph)
    ctx = PhaseCtx(graph=graph, cursor_id=caller.uid)
    receipts = list(BehaviorRegistry.chain_execute_all(
        ctx=ctx, task="builder_identity", call_kwargs={"caller": caller},
    ))
    assert len(receipts) == 3
    assert events == ["shared", "shared", "last"]
