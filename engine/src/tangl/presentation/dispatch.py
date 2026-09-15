"""Application-level contributors for portable presentation projections."""

from __future__ import annotations

from typing import Callable

from tangl.core import BehaviorRegistry, DispatchLayer


presentation_dispatch = BehaviorRegistry(
    label="presentation_dispatch",
    default_dispatch_layer=DispatchLayer.APPLICATION,
)


def _make_on_hook(task: str) -> Callable:
    """Create a presentation-contribution registration decorator."""

    def on_hook(func=None, **kwargs):
        if func is None:
            return lambda f: presentation_dispatch.register(func=f, task=task, **kwargs)
        return presentation_dispatch.register(func=func, task=task, **kwargs)

    on_hook.__name__ = f"on_{task}"
    on_hook.__doc__ = f"Register a presentation contributor for ``{task}``."
    return on_hook


on_advertise_story_info_channels = _make_on_hook("advertise_story_info_channels")
on_advertise_world_info_channels = _make_on_hook("advertise_world_info_channels")
on_get_story_info = _make_on_hook("get_story_info")

# The VM drives the ``compose_journal`` fold, and the story graph folds this
# registry into it. A mechanic that only adds staging -- which clip, which slot --
# registers here, contributing UI syntax without claiming a place in the lifecycle.
on_compose_journal = _make_on_hook("compose_journal")


__all__ = [
    "on_advertise_story_info_channels",
    "on_advertise_world_info_channels",
    "on_compose_journal",
    "on_get_story_info",
    "presentation_dispatch",
]
