"""Dispatch hook integration tests for ``tangl.core38.dispatch``."""

from __future__ import annotations

from types import SimpleNamespace

from tangl.core38.behavior import BehaviorRegistry, DispatchLayer
from tangl.core38.dispatch import (
    do_add_item,
    do_create,
    do_get_item,
    do_init,
    on_add_item,
    on_create,
    on_get_item,
    on_init,
)
from tangl.core38.entity import Entity
from tangl.core38.registry import Registry


class ChildEntity(Entity):
    """Entity subtype for caller kind filtering."""


class TestDispatchFunctions:
    def test_do_init_chains_ctx_registry_and_inline(self, null_ctx) -> None:
        events: list[str] = []

        on_init(func=lambda *, caller, ctx=None, **_: events.append("global"))
        app_registry = BehaviorRegistry(default_dispatch_layer=DispatchLayer.APPLICATION)
        app_registry.register(task="init", func=lambda *, caller, ctx=None, **_: events.append("ctx"))

        ctx = SimpleNamespace(
            get_registries=lambda: [app_registry],
            get_inline_behaviors=lambda: [lambda *, caller, ctx=None, **_: events.append("inline")],
        )
        do_init(caller=Entity(label="x"), ctx=ctx)
        assert events == ["global", "ctx", "inline"]

    def test_do_init_selector_filters_by_caller_kind(self, null_ctx) -> None:
        calls: list[str] = []
        on_init(func=lambda *, caller, **_: calls.append("base"), wants_caller_kind=Entity)
        on_init(func=lambda *, caller, **_: calls.append("child"), wants_caller_kind=ChildEntity)

        do_init(caller=Entity(label="e"), ctx=null_ctx)
        assert calls == ["base"]

    def test_do_create_merges_results(self, null_ctx) -> None:
        on_create(func=lambda *, data, **_: {"a": 1})
        on_create(func=lambda *, data, **_: {"b": 2})
        assert do_create(data={"label": "x"}, ctx=null_ctx) == {"label": "x", "a": 1, "b": 2}

    def test_do_add_item_uses_falsy_non_none_result(self, null_ctx) -> None:
        on_add_item(func=lambda *, registry, item, **_: "")
        item = Entity(label="x")
        assert do_add_item(Registry(), item, null_ctx) == ""

    def test_do_get_item_uses_falsy_non_none_result(self, null_ctx) -> None:
        on_get_item(func=lambda *, registry, item, **_: 0)
        item = Entity(label="x")
        assert do_get_item(Registry(), item, null_ctx) == 0
