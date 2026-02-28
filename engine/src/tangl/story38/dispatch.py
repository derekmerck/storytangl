from __future__ import annotations

from tangl.core38 import BehaviorRegistry, DispatchLayer

story_dispatch = BehaviorRegistry(
    label="story38_dispatch",
    default_dispatch_layer=DispatchLayer.APPLICATION,
)


def on_journal(func=None, **kwargs):
    """Register a story-level JOURNAL handler."""
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="render_journal", **kwargs)
    return story_dispatch.register(func=func, task="render_journal", **kwargs)


def on_gather_ns(func=None, **kwargs):
    """Register a story-level namespace contributor."""
    has_kind = kwargs.pop("has_kind", None)
    if has_kind is not None:
        kwargs.setdefault("wants_caller_kind", has_kind)
        kwargs.setdefault("wants_exact_kind", False)
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="gather_ns", **kwargs)
    return story_dispatch.register(func=func, task="gather_ns", **kwargs)


__all__ = ["story_dispatch", "on_gather_ns", "on_journal"]
