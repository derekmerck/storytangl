from __future__ import annotations

from tangl.core import BehaviorRegistry, DispatchLayer

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


__all__ = [
    "on_compose_journal",
    "story_dispatch",
    "on_gather_ns",
    "on_journal",
]
