from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tangl.core import BehaviorRegistry, CallReceipt, DispatchLayer, Selector

from .episode import Action

story_dispatch = BehaviorRegistry(
    label="story_dispatch",
    default_dispatch_layer=DispatchLayer.APPLICATION,
)


def on_journal(func=None, **kwargs):
    """Register a story-level JOURNAL handler."""
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="render_journal", **kwargs)
    return story_dispatch.register(func=func, task="render_journal", **kwargs)


def on_compose_journal(func=None, **kwargs):
    """Register a story-level post-merge JOURNAL composition handler."""
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="compose_journal", **kwargs)
    return story_dispatch.register(func=func, task="compose_journal", **kwargs)


def on_gather_ns(func=None, **kwargs):
    """Register a story-level namespace contributor."""
    if "has_kind" in kwargs:
        raise TypeError(
            "on_gather_ns no longer accepts 'has_kind'; use 'wants_caller_kind'",
        )
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="gather_ns", **kwargs)
    return story_dispatch.register(func=func, task="gather_ns", **kwargs)


def on_find_edges(func=None, **kwargs):
    """Register a story-level edge-query handler."""
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="find_edges", **kwargs)
    return story_dispatch.register(func=func, task="find_edges", **kwargs)


def do_find_edges(
    caller: object,
    *,
    ctx: object,
    query: Mapping[str, Any],
) -> list[Action]:
    """Return distinct story actions matching a typed client query."""
    receipts = list(
        story_dispatch.execute_all(
            task="find_edges",
            call_kwargs={"caller": caller, "query": query},
            ctx=ctx,
            selector=Selector(caller_kind=type(caller)),
        )
    )
    results = CallReceipt.gather_results(*receipts)
    matches: list[Action] = []
    seen: set[object] = set()
    for result in results:
        candidates = result if isinstance(result, list) else [result]
        for candidate in candidates:
            if not isinstance(candidate, Action):
                raise TypeError(
                    f"find_edges handlers must return Action values, got {type(candidate).__name__}"
                )
            if candidate.uid in seen:
                continue
            seen.add(candidate.uid)
            matches.append(candidate)
    return matches


__all__ = [
    "do_find_edges",
    "on_find_edges",
    "on_compose_journal",
    "story_dispatch",
    "on_gather_ns",
    "on_journal",
]
