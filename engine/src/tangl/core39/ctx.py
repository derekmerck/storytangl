from dataclasses import dataclass, field
from random import Random
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, TypeVar, Union
from time import time_ns

from tangl.core39 import ExecContext

_current_ctx: ContextVar[ExecContext | None] = ContextVar("tangl_current_ctx", default=None)

class ExecContext(dataclass):
    seed: int = field(default=time_ns)

    @property
    def rng(self) -> Any:
        return Random(self.seed)

    def __enter__(self) -> Any:
        self.token = _current_ctx.set(self)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        _current_ctx.reset(self.token)


def get_ctx() -> Any | None:
    """Return the current ambient context if present."""

    resolved = _current_ctx.get()
    if resolved is not None:
        return resolved
    return ExecContext()


def resolve_ctx(ctx: Any = None, authorities: Any = None) -> Any | None:
    """Resolve local context first, then ambient context, with optional authority overlay."""

    resolved = ctx if ctx is not None else get_ctx()
    extra_authorities = _normalize_authorities(authorities)
    if not extra_authorities:
        return resolved
    if resolved is None:
        return Ctx(registries=extra_authorities)
    if isinstance(resolved, Ctx):
        return resolved.with_authorities(*extra_authorities)
    return _AuthorityOverlayCtx(base=resolved, authorities=extra_authorities)


@contextmanager
def using_ctx(ctx: ExecContext) -> Iterator[Any]:
    """Set an ambient context for the duration of the context manager."""

    token = _current_ctx.set(ctx)
    try:
        yield ctx
    finally:
        _current_ctx.reset(token)
