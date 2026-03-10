"""Core context protocols and ambient context helpers."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class DispatchCtx(Protocol):
    """Minimal dispatch context contract for hook execution chains."""

    def get_authorities(self) -> Iterable[Any]: ...
    def get_inline_behaviors(self) -> Iterable[Any]: ...


@runtime_checkable
class CoreCtx(DispatchCtx, Protocol):
    """Optional core-level context metadata surface.

    Dispatch only requires :class:`DispatchCtx`.  This protocol adds stable
    metadata fields used across layers for tracing and observability.
    """

    correlation_id: UUID | str | None
    logger: Any | None
    meta: Mapping[str, Any] | None

    def get_meta(self) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class Ctx:
    """Default concrete context implementing :class:`CoreCtx`.

    ``Ctx`` remains intentionally lightweight and interoperable with duck-typed
    context objects used throughout v38.
    """

    dispatch: Any | None = None
    """Optional legacy dispatch holder (single registry or iterable)."""

    registries: tuple[Any, ...] = ()
    inline_behaviors: tuple[Any, ...] = ()

    correlation_id: UUID | str | None = None
    logger: Any | None = None
    meta: Mapping[str, Any] | None = field(default_factory=dict)

    def _dispatch_registries(self) -> list[Any]:
        if self.dispatch is None:
            return []
        if isinstance(self.dispatch, (list, tuple, set)):
            return [item for item in self.dispatch if item is not None]
        return [self.dispatch]

    def get_authorities(self) -> list[Any]:
        values: list[Any] = list(self.registries)
        for registry in self._dispatch_registries():
            if registry not in values:
                values.append(registry)
        return values

    def get_inline_behaviors(self) -> list[Any]:
        return list(self.inline_behaviors)

    def get_meta(self) -> Mapping[str, Any]:
        return dict(self.meta or {})

    def with_meta(self, **updates: Any) -> "Ctx":
        merged = dict(self.meta or {})
        merged.update(updates)
        return Ctx(
            dispatch=self.dispatch,
            registries=tuple(self.registries),
            inline_behaviors=tuple(self.inline_behaviors),
            correlation_id=self.correlation_id,
            logger=self.logger,
            meta=merged,
        )


_current_ctx: ContextVar[Any | None] = ContextVar("tangl_current_ctx", default=None)


def get_ctx() -> Any | None:
    """Return the current ambient context if present."""

    return _current_ctx.get()


def resolve_ctx(ctx: Any = None) -> Any | None:
    """Resolve local context first, then ambient context."""

    return ctx if ctx is not None else get_ctx()


@contextmanager
def using_ctx(ctx: Any) -> Iterator[Any]:
    """Set an ambient context for the duration of the context manager."""

    token = _current_ctx.set(ctx)
    try:
        yield ctx
    finally:
        _current_ctx.reset(token)


__all__ = [
    "CoreCtx",
    "Ctx",
    "DispatchCtx",
    "get_ctx",
    "resolve_ctx",
    "using_ctx",
]
