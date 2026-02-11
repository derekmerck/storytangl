# tangl/core/ctx.py
from __future__ import annotations
from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional

@dataclass(frozen=True)
class Ctx:
    """Opaque dispatch context."""
    dispatch: Any | None = None  # e.g., BehaviorRegistry or resolver bundle
    meta: dict[str, Any] | None = None

_current_ctx: ContextVar[Optional[Ctx]] = ContextVar("tangl_current_ctx", default=None)

def get_ctx() -> Optional[Ctx]:
    return _current_ctx.get()

def resolve_ctx(ctx=None):
    """
    prefer a locally provided ctx for hooks, otherwise
    use ambient ctx, if it exists

    Example:
        >>> def foo(ctx=None): return resolve_ctx(ctx)
        >>> foo() is None
        True
        >>> foo(ctx="bar")
        'bar'
        >>> with using_ctx(ctx="foobar"): foo()
        'foobar'
    """
    return ctx if ctx is not None else get_ctx()

@contextmanager
def using_ctx(ctx: Ctx) -> Iterator[Ctx]:
    token = _current_ctx.set(ctx)
    try:
        yield ctx
    finally:
        _current_ctx.reset(token)