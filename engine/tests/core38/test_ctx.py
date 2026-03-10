"""Contract tests for ``tangl.core.ctx``."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from uuid import uuid4

from tangl.core.ctx import CoreCtx, Ctx, DispatchCtx, get_ctx, resolve_ctx, using_ctx


def test_ctx_implements_dispatch_and_core_protocols() -> None:
    ctx = Ctx(correlation_id=uuid4(), logger=logging.getLogger("test.ctx"), meta={"k": "v"})
    assert isinstance(ctx, DispatchCtx)
    assert isinstance(ctx, CoreCtx)


def test_get_authorities_merges_dispatch_and_explicit_registries_without_duplicates() -> None:
    a = object()
    b = object()
    ctx = Ctx(dispatch=[a, b], registries=(b,))
    assert ctx.get_authorities() == [b, a]


def test_resolve_ctx_prefers_explicit_then_ambient() -> None:
    explicit = Ctx(correlation_id="explicit")
    ambient = Ctx(correlation_id="ambient")
    with using_ctx(ambient):
        assert get_ctx() is ambient
        assert resolve_ctx(explicit) is explicit
        assert resolve_ctx() is ambient


def test_resolve_ctx_appends_authorities_to_explicit_ctx() -> None:
    a = object()
    b = object()
    ctx = Ctx(registries=(a,))

    resolved = resolve_ctx(ctx, authorities=(b, a))

    assert isinstance(resolved, Ctx)
    assert resolved is not ctx
    assert resolved.get_authorities() == [a, b]


def test_resolve_ctx_creates_ctx_when_only_authorities_are_provided() -> None:
    a = object()

    resolved = resolve_ctx(authorities=(a,))

    assert isinstance(resolved, Ctx)
    assert resolved.get_authorities() == [a]


def test_resolve_ctx_wraps_custom_ctx_with_extra_authorities() -> None:
    a = object()
    b = object()
    base = SimpleNamespace(
        get_authorities=lambda: [a],
        get_inline_behaviors=lambda: ["inline"],
        correlation_id="corr-1",
    )

    resolved = resolve_ctx(base, authorities=(b,))

    assert resolved is not base
    assert resolved.correlation_id == "corr-1"
    assert resolved.get_authorities() == [a, b]
    assert resolved.get_inline_behaviors() == ["inline"]


def test_with_meta_keeps_other_fields_and_merges_meta() -> None:
    ctx = Ctx(correlation_id="corr-1", meta={"a": 1})
    updated = ctx.with_meta(b=2)
    assert updated.correlation_id == "corr-1"
    assert updated.get_meta() == {"a": 1, "b": 2}
