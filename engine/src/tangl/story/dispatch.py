from __future__ import annotations

from tangl.core import BehaviorRegistry, DispatchLayer

story_dispatch = BehaviorRegistry(
    label="story_dispatch",
    default_dispatch_layer=DispatchLayer.APPLICATION,
)


def _normalize_legacy_register_kwargs(kwargs):
    payload = dict(kwargs)
    if "caller" in payload and "wants_caller_kind" not in payload:
        payload["wants_caller_kind"] = payload.pop("caller")
        payload.setdefault("wants_exact_kind", False)
    if "is_instance" in payload and "wants_caller_kind" not in payload:
        payload["wants_caller_kind"] = payload.pop("is_instance")
        payload.setdefault("wants_exact_kind", False)
    if "handler_layer" in payload and "dispatch_layer" not in payload:
        payload["dispatch_layer"] = payload.pop("handler_layer")
    return payload


def on_journal(func=None, **kwargs):
    """Register a story-level JOURNAL handler."""
    kwargs = _normalize_legacy_register_kwargs(kwargs)
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="render_journal", **kwargs)
    return story_dispatch.register(func=func, task="render_journal", **kwargs)


def on_compose_journal(func=None, **kwargs):
    """Register a story-level post-merge JOURNAL composition handler."""
    kwargs = _normalize_legacy_register_kwargs(kwargs)
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="compose_journal", **kwargs)
    return story_dispatch.register(func=func, task="compose_journal", **kwargs)


def on_gather_ns(func=None, **kwargs):
    """Register a story-level namespace contributor."""
    kwargs = _normalize_legacy_register_kwargs(kwargs)
    if "has_kind" in kwargs:
        raise TypeError(
            "on_gather_ns no longer accepts 'has_kind'; use 'wants_caller_kind'",
        )
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="gather_ns", **kwargs)
    return story_dispatch.register(func=func, task="gather_ns", **kwargs)

# on_gather_content is the first sub-hook of a planned collect/enrich/compose
# journal decomposition.  on_post_process_content and on_get_choices were
# removed (zero consumers); restore them when the full pattern is needed.
# See scratch/legacy for the v37 three-stage journal pipeline.
def on_gather_content(func=None, **kwargs):
    """Legacy compatibility hook for gather-content author handlers."""
    kwargs = _normalize_legacy_register_kwargs(kwargs)
    if func is None:
        return lambda f: story_dispatch.register(func=f, task="gather_content", **kwargs)
    return story_dispatch.register(func=func, task="gather_content", **kwargs)


__all__ = [
    "on_compose_journal",
    "story_dispatch",
    "on_gather_content",
    "on_gather_ns",
    "on_journal",
]
