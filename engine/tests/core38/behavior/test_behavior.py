"""Contract tests for ``tangl.core38.behavior`` chain assembly."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.core38.behavior import (
    Behavior,
    BehaviorRegistry,
    CallReceipt,
    DispatchLayer,
    Priority,
)
from tangl.core38.entity import Entity
from tangl.core38.selector import Selector


class SpecialEntity(Entity):
    """Entity subtype used for caller kind matching tests."""


class TestBehaviorCallerKind:
    def test_caller_kind_uses_wants_caller_kind(self) -> None:
        behavior = Behavior(
            func=lambda **_: True,
            wants_caller_kind=Entity,
            wants_exact_kind=False,
        )
        assert behavior.caller_kind(Entity)
        assert behavior.caller_kind(SpecialEntity)

    def test_caller_kind_exact_rejects_subclass(self) -> None:
        behavior = Behavior(
            func=lambda **_: True,
            wants_caller_kind=Entity,
            wants_exact_kind=True,
        )
        assert not behavior.caller_kind(SpecialEntity)


class TestBehaviorRegistryChainExecute:
    def test_execute_all_delegates_to_chain_execute(self) -> None:
        registry = BehaviorRegistry()
        registry.register(task="t", func=lambda *, ctx=None: "ok")
        receipts = list(registry.execute_all(task="t"))
        assert [receipt.result for receipt in receipts] == ["ok"]

    def test_chain_execute_extends_ctx_authorities(self) -> None:
        order: list[str] = []
        base = BehaviorRegistry(default_dispatch_layer=DispatchLayer.GLOBAL)
        app = BehaviorRegistry(default_dispatch_layer=DispatchLayer.APPLICATION)
        base.register(task="x", func=lambda *, ctx=None: order.append("base"))
        app.register(task="x", func=lambda *, ctx=None: order.append("app"))

        ctx = SimpleNamespace(get_authorities=lambda: [app], get_inline_behaviors=lambda: [])
        CallReceipt.gather_results(*base.chain_execute(base, task="x", ctx=ctx))
        assert order == ["base", "app"]

    def test_chain_execute_supports_legacy_ctx_registries_alias(self) -> None:
        order: list[str] = []
        base = BehaviorRegistry(default_dispatch_layer=DispatchLayer.GLOBAL)
        app = BehaviorRegistry(default_dispatch_layer=DispatchLayer.APPLICATION)
        base.register(task="x", func=lambda *, ctx=None: order.append("base"))
        app.register(task="x", func=lambda *, ctx=None: order.append("app"))

        ctx = SimpleNamespace(get_registries=lambda: [app], get_inline_behaviors=lambda: [])
        CallReceipt.gather_results(*base.chain_execute(base, task="x", ctx=ctx))
        assert order == ["base", "app"]

    def test_chain_execute_wraps_ctx_inline_behaviors_as_local(self) -> None:
        layers: list[int] = []
        base = BehaviorRegistry(default_dispatch_layer=DispatchLayer.GLOBAL)
        base.register(task="x", func=lambda *, ctx=None: layers.append(DispatchLayer.GLOBAL))

        ctx = SimpleNamespace(
            get_authorities=lambda: [],
            get_inline_behaviors=lambda: [lambda *, ctx=None: layers.append(DispatchLayer.LOCAL)],
        )
        CallReceipt.gather_results(*base.chain_execute(base, task="x", ctx=ctx))
        assert layers == [DispatchLayer.GLOBAL, DispatchLayer.LOCAL]

    def test_chain_execute_deduplicates_registries(self) -> None:
        calls = {"n": 0}
        reg = BehaviorRegistry()
        reg.register(task="x", func=lambda *, ctx=None: calls.__setitem__("n", calls["n"] + 1))

        ctx = SimpleNamespace(get_authorities=lambda: [reg], get_inline_behaviors=lambda: [])
        CallReceipt.gather_results(*BehaviorRegistry.chain_execute(reg, reg, ctx=ctx, task="x"))
        assert calls["n"] == 1

    def test_chain_execute_accepts_ctx_without_inline_method(self) -> None:
        registry = BehaviorRegistry()
        registry.register(task="x", func=lambda *, ctx=None: "ok")
        ctx = SimpleNamespace(get_authorities=lambda: [])
        receipts = list(BehaviorRegistry.chain_execute(registry, ctx=ctx, task="x"))
        assert receipts[0].result == "ok"

    def test_wrap_inline_rejects_non_callable(self) -> None:
        with pytest.raises(TypeError):
            BehaviorRegistry._wrap_inline(["bad"])

    def test_chain_inline_behaviors_param_is_wrapped(self) -> None:
        results = list(
            BehaviorRegistry.chain_execute(
                BehaviorRegistry(),
                inline_behaviors=[Behavior(func=lambda *, ctx=None: "b", task="inline"), lambda *, ctx=None: "a"],
            )
        )
        assert {r.result for r in results} == {"a", "b"}

    def test_selector_caller_kind_matches_behavior_field(self) -> None:
        behavior = Behavior(func=lambda **_: True, wants_caller_kind=Entity)
        assert Selector(caller_kind=Entity).matches(behavior)

    def test_sort_key_still_orders_priority_and_layer(self) -> None:
        first = Behavior(func=lambda **_: True, dispatch_layer=DispatchLayer.GLOBAL, priority=Priority.FIRST)
        later = Behavior(func=lambda **_: True, dispatch_layer=DispatchLayer.LOCAL, priority=Priority.LAST)
        assert first.sort_key < later.sort_key
