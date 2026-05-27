"""Service-side projected-state dispatch hooks."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Callable

from tangl.core import BehaviorRegistry, CallReceipt, DispatchLayer, Selector

from .response import InfoAffordance, ProjectedSection, ProjectedState, StoryInfoRequest


service_info_dispatch = BehaviorRegistry(
    label="service_info_dispatch",
    default_dispatch_layer=DispatchLayer.APPLICATION,
)


def _make_on_hook(task: str) -> Callable:
    """Create a registration decorator for a service-info task."""

    def on_hook(func=None, **kwargs):
        if func is None:
            return lambda f: service_info_dispatch.register(func=f, task=task, **kwargs)
        return service_info_dispatch.register(func=func, task=task, **kwargs)

    on_hook.__name__ = f"on_{task}"
    on_hook.__doc__ = f"Register a handler for the ``{task}`` task."
    return on_hook


on_advertise_info_channels = _make_on_hook("advertise_info_channels")
on_get_story_info = _make_on_hook("get_story_info")


def _execute(task: str, *, caller: object, ctx: object, **kwargs: object) -> list[object]:
    receipts = service_info_dispatch.execute_all(
        task=task,
        call_kwargs={"caller": caller, **kwargs},
        ctx=ctx,
        selector=Selector(caller_kind=type(caller)),
    )
    return CallReceipt.gather_results(*receipts)


def do_advertise_info_channels(caller: object, *, ctx: object) -> list[InfoAffordance]:
    """Gather queryable story-info channels for the current envelope."""
    affordances: list[InfoAffordance] = []
    for value in _execute("advertise_info_channels", caller=caller, ctx=ctx):
        affordances.extend(_coerce_affordances(value))
    return affordances


def do_get_story_info(
    caller: object,
    *,
    ctx: object,
    request: StoryInfoRequest,
) -> ProjectedState:
    """Gather projected-state sections for ``request``."""
    sections: list[ProjectedSection] = []
    for value in _execute("get_story_info", caller=caller, ctx=ctx, request=request):
        sections.extend(_coerce_sections(value))
    return ProjectedState(sections=sections)


def _coerce_affordances(value: object) -> list[InfoAffordance]:
    if value is None:
        return []
    if isinstance(value, InfoAffordance):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        affordances: list[InfoAffordance] = []
        for item in value:
            if not isinstance(item, InfoAffordance):
                raise TypeError(
                    "advertise_info_channels handlers must return "
                    "InfoAffordance values"
                )
            affordances.append(item)
        return affordances
    raise TypeError(
        "advertise_info_channels handlers must return "
        "InfoAffordance | Iterable[InfoAffordance] | None"
    )


def _coerce_sections(value: object) -> list[ProjectedSection]:
    if value is None:
        return []
    if isinstance(value, ProjectedState):
        return list(value.sections)
    if isinstance(value, ProjectedSection):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        sections: list[ProjectedSection] = []
        for item in value:
            if not isinstance(item, ProjectedSection):
                raise TypeError(
                    "get_story_info handlers must return ProjectedSection values"
                )
            sections.append(item)
        return sections
    raise TypeError(
        "get_story_info handlers must return "
        "ProjectedSection | ProjectedState | Iterable[ProjectedSection] | None"
    )


__all__ = [
    "do_advertise_info_channels",
    "do_get_story_info",
    "on_advertise_info_channels",
    "on_get_story_info",
    "service_info_dispatch",
]
