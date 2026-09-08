"""A surface: the geometry a block's pieces are drawn resting on.

A zone rendered as a list of rows says *what you hold*. A zone rendered as a
surface says *what you are looking at* — documents lying on a desk, where
picking one is picking the thing itself. The data for both is identical; only
the geometry is missing, and this is where a world declares it.

Scope
-----
A surface belongs to a **block**: the largest span over which its shape is
guaranteed not to change. The next shift may set up a different desk — another
office, a promotion, administrative caprice — and that is a different surface on
a different block. What a surface may never do is mutate mid-shift; a world that
wants to rearrange the desk under the player breaks the shift in two.

Why the surface owns occupancy
------------------------------
Each slot names the ``piece_kind`` it holds, so the surface carries *both* the
geometry and the mapping. That is deliberate, and it is the opposite of where
the sandbox map puts its claim.

A map's regions are places, and a location knows what it is, so the claim rides
the location (``SandboxLocation.plates``) and generated choices inherit it. A
desk is not like that. The same scene may be played on two different desks — the
oak one you were promoted to, with coordinates shifted to make room for a bust
of dear leader — over pieces that have not changed at all. Putting the claim on
the pieces would mean the credential catalog had to be edited to buy furniture.
So the desk says where an id card lies, the mechanic says which pieces are id
cards, and neither names the other.

Both directions degrade to nothing rather than to a guess: a slot no piece fills
draws nothing, and a piece no slot holds is simply not on the surface — it stays
in the numbered list, which the §5.3 input-parity floor keeps reachable anyway.

Not built: controls
-------------------
The same mechanism answers screen clutter, and it is worth writing down because
it is mechanical rather than novel. A credentials shift offers nine choices at
its peak — three dispositions, three interrogations, inspect, review, reissue —
and every one of them costs a row at the bottom of a 320x200 stage.

Replace the *choice* categories with hotspot categories exactly as the piece
categories were replaced: the surface declares controls with rects, and a choice
lands in one by name. Dispositions become two buttons off to the side;
interrogations become hotspots on the candidate's own rect — ask about the
appearance, ask about the contraband — so the cue sits on the thing being asked
about.

The one part that does not already exist is the join token. A piece arrives
carrying ``piece_kind``; a choice today arrives carrying only display text, and
geometry must not be keyed to prose. The mechanic does know: moves are
``CredentialsMove(kind, target)`` — ``decide``/``pass``, ``verify_id``,
``request_search``. Promoting that to a client-visible ``ui:`` tag where move
edges are built is the whole engine-side change, and it is what the namespace
already exists for (:func:`tangl.journal.fragments.client_visible_tags`: "an
author or mechanic that wants a tag to reach clients says so by naming it").

Deliberately not done here. It is the first mechanic change this design would
need, and the pieces layer earns its keep without it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .geometry import NormalizedRect


class SurfaceSlot(NormalizedRect):
    """One place on a surface, and the kind of piece that lies there.

    Shares :class:`~tangl.presentation.geometry.NormalizedRect` with the sandbox map's
    regions: same normalized coordinates, same refusal to sit outside its plate.
    """

    holds: str
    """The ``piece_kind`` this slot accepts.

    Mechanic vocabulary, not world vocabulary — ``candidate``, ``id_card``,
    ``permit`` — which is exactly what makes the join work without either side
    importing the other. A client reads it off the wire and matches it against
    the pieces already in hand.
    """


class Surface(BaseModel):
    """Named geometry for one block's pieces: an extent plus the slots on it.

    Declares geometry only, and may declare slots nothing ever fills. That is
    the same tolerance the map plate has, and it is what lets a desk be
    re-measured, re-dressed or replaced without touching a mechanic.
    """

    name: str

    band: NormalizedRect | None = None
    """The surface's own extent — the desk, not the room.

    Declared rather than derived from the union of the slots, because a desk has
    a shape whether or not anything is on it, and because adding a slot must not
    silently resize the furniture. A client with no ``plate`` draws this band
    directly: a filled rect with a contour along its top edge reads as a surface
    projecting away from the viewer, which is why the desk needs no art.
    """

    plate: str | None = None
    """Asset name of an optional surface image, staged separately as media.

    Optional on purpose. Nothing requires art here today, and a world that later
    wants a painted desk should not have to move the geometry to get one.
    """

    slots: dict[str, SurfaceSlot] = Field(default_factory=dict)


class HasSurface:
    """Mixin for a block that publishes a surface for its pieces.

    Deliberately a bare mixin rather than a field on ``Block``: most blocks have
    no surface, and a client asks for this geometry by name so it never pays for
    the ones that do not. Story-info registration keys off this type, so any
    block that mixes it in publishes the channels — nothing about it is specific
    to the mechanic whose pieces happen to be lying there.
    """

    surface: Surface | None = None


__all__ = ["HasSurface", "Surface", "SurfaceSlot"]
