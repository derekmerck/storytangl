"""Contract tests for ``tangl.core38.ctx``."""

from __future__ import annotations

import logging
from uuid import uuid4

from tangl.core38.ctx import CoreCtx, Ctx, DispatchCtx, get_ctx, resolve_ctx, using_ctx


def test_ctx_implements_dispatch_and_core_protocols() -> None:
    ctx = Ctx(correlation_id=uuid4(), logger=logging.getLogger("test.ctx"), meta={"k": "v"})
    assert isinstance(ctx, DispatchCtx)
    assert isinstance(ctx, CoreCtx)


def test_get_registries_merges_dispatch_and_explicit_registries_without_duplicates() -> None:
    a = object()
    b = object()
    ctx = Ctx(dispatch=[a, b], registries=(b,))
    assert ctx.get_registries() == [b, a]


def test_resolve_ctx_prefers_explicit_then_ambient() -> None:
    explicit = Ctx(correlation_id="explicit")
    ambient = Ctx(correlation_id="ambient")
    with using_ctx(ambient):
        assert get_ctx() is ambient
        assert resolve_ctx(explicit) is explicit
        assert resolve_ctx() is ambient


def test_with_meta_keeps_other_fields_and_merges_meta() -> None:
    ctx = Ctx(correlation_id="corr-1", meta={"a": 1})
    updated = ctx.with_meta(b=2)
    assert updated.correlation_id == "corr-1"
    assert updated.get_meta() == {"a": 1, "b": 2}
