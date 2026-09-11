"""Service-side projected-state dispatch hooks."""

from __future__ import annotations

from collections.abc import Iterable

from tangl.core import BehaviorRegistry, CallReceipt, DispatchLayer, Selector
from tangl.presentation.dispatch import presentation_dispatch
from tangl.presentation.projection import (
    BrandingValue,
    InfoAffordance,
    ProjectionRequest,
    ProjectedSection,
    ProjectedState,
    TableValue,
)
from tangl.story import World

WORLD_STYLE_CHANNEL = "ui-style-hints-html"
WORLD_BRANDING_CHANNEL = "ui-branding"

service_dispatch = BehaviorRegistry(
    label="service_dispatch",
    default_dispatch_layer=DispatchLayer.SYSTEM,
)


def _execute(task: str, *, caller: object, ctx: object, **kwargs: object) -> list[object]:
    receipts = BehaviorRegistry.chain_execute_all(
        service_dispatch,
        presentation_dispatch,
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
    request: ProjectionRequest,
) -> ProjectedState:
    """Gather projected-state sections for ``request``."""
    sections: list[ProjectedSection] = []
    for value in _execute("get_story_info", caller=caller, ctx=ctx, request=request):
        sections.extend(_coerce_sections(value))
    return ProjectedState(sections=sections)


def do_get_world_info(
    caller: World,
    *,
    ctx: object,
    request: ProjectionRequest,
) -> ProjectedState:
    """Gather public world-static sections for ``request``."""

    sections: list[ProjectedSection] = []
    for value in _execute("get_world_info", caller=caller, ctx=ctx, request=request):
        sections.extend(_coerce_sections(value))
    return ProjectedState(sections=sections)


def advertise_world_info_channels(
    *, caller: World, **_kw: object
) -> list[InfoAffordance]:
    """Advertise the fixed public presentation channels shared by worlds."""

    return [
        InfoAffordance(channel_id=WORLD_STYLE_CHANNEL, label="HTML style hints"),
        InfoAffordance(channel_id=WORLD_BRANDING_CHANNEL, label="Branding"),
    ]


def project_world_info(
    *, caller: World, request: ProjectionRequest, **_kw: object
) -> list[ProjectedSection]:
    """Project cacheable advisory presentation metadata for one world."""

    channels = request.requested_channels()
    sections: list[ProjectedSection] = []
    if WORLD_STYLE_CHANNEL in channels:
        sections.append(
            ProjectedSection(
                section_id=WORLD_STYLE_CHANNEL,
                title="HTML style hints",
                kind="style_hints",
                value=TableValue(
                    columns=["class", "meaning"],
                    rows=[
                        ["st-emphasis", "emphasized content"],
                        ["st-emphasis--warn", "warning prominence"],
                        ["st-unavailable", "unavailable action"],
                    ],
                ),
            )
        )
    if WORLD_BRANDING_CHANNEL in channels:
        branding = {
            "name": str(caller.metadata.get("title", caller.label)),
            **dict(caller.metadata.get("branding") or {}),
        }
        sections.append(
            ProjectedSection(
                section_id=WORLD_BRANDING_CHANNEL,
                title="Branding",
                kind="branding",
                value=BrandingValue.model_validate(branding),
            )
        )
    return sections


service_dispatch.register(
    advertise_world_info_channels,
    task="advertise_info_channels",
    wants_caller_kind=World,
    wants_exact_kind=False,
)
service_dispatch.register(
    project_world_info,
    task="get_world_info",
    wants_caller_kind=World,
    wants_exact_kind=False,
)


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
    "do_get_world_info",
    "WORLD_BRANDING_CHANNEL",
    "WORLD_STYLE_CHANNEL",
    "service_dispatch",
]
