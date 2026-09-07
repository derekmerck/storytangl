"""Story-info channels publishing a block's surface geometry.

Surface geometry rides story-info rather than the journal for the same reason
map plate geometry does: it is *reference state*, not turn content. It changes
when the furniture changes, not when the player acts, so a client fetches it once
by name and a client that cannot draw surfaces never pays for it at all.

Registered against :class:`~tangl.mechanics.surface.HasSurface` rather than
against any mechanic, so a block publishes these channels by owning a surface and
nothing else. Importing this module registers the handlers; the credentials
worlds pull it in the way the adventure sandbox pulls in its map channel.
"""

from __future__ import annotations

from tangl.service.dispatch import on_advertise_info_channels, on_get_story_info
from tangl.service.response import (
    InfoAffordance,
    KvListValue,
    KvRow,
    ProjectedSection,
    StoryInfoRequest,
    TableValue,
)
from tangl.vm.runtime.frame import PhaseCtx

from .surface import HasSurface, Surface

SURFACE_PLATE_KIND = "surface_plate"
SURFACE_SLOTS_KIND = "surface_slots"
SURFACE_KINDS = frozenset({SURFACE_PLATE_KIND, SURFACE_SLOTS_KIND})

SURFACE_PLATE_SECTION = "surface_plate"
SURFACE_SLOTS_SECTION = "surface_slots"


def _surface(caller: HasSurface) -> Surface | None:
    """Return the caller's surface when it has one.

    Handlers register for every ``HasSurface`` caller, and the mixin's default is
    ``None``: owning the capability is not the same as declaring the furniture.
    """

    surface = getattr(caller, "surface", None)
    return surface if isinstance(surface, Surface) else None


@on_advertise_info_channels(wants_caller_kind=HasSurface, wants_exact_kind=False)
def advertise_surface_info_channels(
    *,
    caller: HasSurface,
    ctx: PhaseCtx,
    **_kw: object,
) -> list[InfoAffordance]:
    """Advertise the surface channels, and only where a surface is declared."""

    surface = _surface(caller)
    if surface is None:
        return []
    # No shortcuts, matching the map plate: this is geometry a renderer asks for
    # by name, not a drawer a reader opens. An affordance with a key on it would
    # offer the player a table of coordinates.
    return [
        InfoAffordance(
            kind=SURFACE_PLATE_KIND,
            label="Surface",
            query={"kinds": [SURFACE_PLATE_KIND, SURFACE_SLOTS_KIND]},
        )
    ]


@on_get_story_info(wants_caller_kind=HasSurface, wants_exact_kind=False)
def project_surface_info(
    *,
    caller: HasSurface,
    ctx: PhaseCtx,
    request: StoryInfoRequest,
    **_kw: object,
) -> list[ProjectedSection] | None:
    """Project the requested surface channels, when asked for by name."""

    surface = _surface(caller)
    if surface is None:
        return None
    kinds = request.requested_kinds()
    if SURFACE_KINDS.isdisjoint(kinds):
        return None

    sections: list[ProjectedSection] = []
    if SURFACE_PLATE_KIND in kinds:
        sections.append(_plate_section(surface))
    if SURFACE_SLOTS_KIND in kinds:
        sections.append(_slots_section(surface))
    return sections or None


def _plate_section(surface: Surface) -> ProjectedSection:
    """Name, optional art, and the surface's own extent.

    The band travels as four numbered rows rather than one formatted string so
    the client reads coordinates it was given instead of parsing coordinates back
    out of prose.
    """

    rows = [
        KvRow(key="Name", value=surface.name),
        KvRow(key="Image", value=surface.plate or ""),
        KvRow(key="Slots", value=len(surface.slots)),
    ]
    if surface.band is not None:
        rows.extend(
            [
                KvRow(key="Band x", value=surface.band.x),
                KvRow(key="Band y", value=surface.band.y),
                KvRow(key="Band w", value=surface.band.w),
                KvRow(key="Band h", value=surface.band.h),
            ]
        )
    return ProjectedSection(
        section_id=SURFACE_PLATE_SECTION,
        title="Surface",
        kind=SURFACE_PLATE_KIND,
        value=KvListValue(items=rows),
    )


def _slots_section(surface: Surface) -> ProjectedSection:
    """Every slot, with the piece kind it holds, in a stable order.

    Sorted by name so a surface with two slots for the same kind fills them the
    same way every time. Nothing else decides the order: the client pairs live
    pieces against these rows as they arrive.
    """

    return ProjectedSection(
        section_id=SURFACE_SLOTS_SECTION,
        title="Surface Slots",
        kind=SURFACE_SLOTS_KIND,
        value=TableValue(
            columns=["Slot", "Holds", "x", "y", "w", "h"],
            rows=[
                [name, slot.holds, slot.x, slot.y, slot.w, slot.h]
                for name, slot in sorted(surface.slots.items())
            ],
        ),
    )


__all__ = [
    "SURFACE_PLATE_KIND",
    "SURFACE_SLOTS_KIND",
    "advertise_surface_info_channels",
    "project_surface_info",
]
