"""Story-info channels publishing a block's surface geometry.

Surface geometry rides story-info rather than the journal for the same reason
map plate geometry does: it is *reference state*, not turn content. It changes
when the furniture changes, not when the player acts, so a client fetches it once
by name and a client that cannot draw surfaces never pays for it at all.

Registered against :class:`~tangl.presentation.surface.HasSurface` rather than
against any mechanic, so a block publishes these channels by owning a surface and
nothing else. Importing this module registers the handlers; the credentials
worlds pull it in the way the adventure sandbox pulls in its map channel.

Why this lives in mechanics
---------------------------
Because mechanics sits at the intersection and may draw on either side. Knowing
what assets exist and how they are laid out is ordinary mechanics work -- a
checkpoint knows it has a counter with documents on it -- so the module belongs
here rather than being pushed up or down to satisfy a diagram.

What was wrong was not where the work happened but the vocabulary it reached for.
Describing a desk by importing Service made this module a party to the request:
it saw the projector seam, the response types, the shape of an answer being
prepared. None of that is its business. It needs to say *what is there and where*
in terms any client could read, and stop.

That the two got conflated is not surprising. Service was the first thing that
wanted to serve a projection, so serving and describing were folded together
while they had exactly one consumer between them -- the same accident that put
the rectangle in ``journal`` because a fragment carried it, and the surface types
beside a game block because a block declared one. Three instances of one mistake,
and #449 unpicks all three.

So the contribution goes on ``presentation_dispatch`` and this module imports no
Service. Service stays the outer operation: it fires the task, folds this
registry with the story and world authorities, and prepares the response.
Nothing here knows an envelope exists, or a client, or a DTO.
"""

from __future__ import annotations

from tangl.presentation.dispatch import on_advertise_info_channels, on_get_story_info
from tangl.presentation.projection import (
    InfoAffordance,
    KvListValue,
    ProjectedSection,
    ProjectionRequest,
    TableValue,
)
from tangl.presentation.surface import HasSurface, Surface
from tangl.presentation.values import KvRow
from tangl.vm.runtime.frame import PhaseCtx

SURFACE_PLATE_KIND = "surface_plate"
SURFACE_SLOTS_KIND = "surface_slots"
SURFACE_KINDS = frozenset({SURFACE_PLATE_KIND, SURFACE_SLOTS_KIND})

SURFACE_PLATE_SECTION = "surface_plate"
SURFACE_SLOTS_SECTION = "surface_slots"


def _surface(caller: HasSurface) -> Surface | None:
    """Return the caller's surface when it has one.

    Handlers register for every ``HasSurface`` caller, so the field is there by
    contract and is read as such -- a defensive ``getattr`` would turn a wrongly
    typed surface into a world that silently has no desk. The mixin's default is
    ``None``: owning the capability is not the same as declaring the furniture.
    """

    return caller.surface


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
    request: ProjectionRequest,
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
    """Every slot, with the piece kind it holds, in the order the world declared.

    Authored order, not lexical. Where a surface declares two slots for one kind,
    this order is what decides which piece lands in which -- so sorting here
    would quietly overrule the author, and would do it invisibly whenever the
    two orders happened to agree.

    This is the one place the surface deliberately parts company with the map
    plate, which does sort: a region is claimed by name and one at a time, so
    its order carries no meaning. A slot's order does.
    """

    return ProjectedSection(
        section_id=SURFACE_SLOTS_SECTION,
        title="Surface Slots",
        kind=SURFACE_SLOTS_KIND,
        value=TableValue(
            columns=["Slot", "Holds", "x", "y", "w", "h"],
            rows=[
                [name, slot.holds, slot.x, slot.y, slot.w, slot.h]
                for name, slot in surface.slots.items()
            ],
        ),
    )


__all__ = [
    "SURFACE_PLATE_KIND",
    "SURFACE_SLOTS_KIND",
    "advertise_surface_info_channels",
    "project_surface_info",
]
