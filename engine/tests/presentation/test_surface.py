"""The surface contract, independent of any mechanic, world, or renderer.

A surface is geometry a client may arrange things on: an extent, and named slots
each naming the ``piece_kind`` that lies there. It is advisory. Nothing here
authorizes a selection -- a slot says where a piece would be drawn, and current
offered-choice state remains the only thing that decides what may be picked.

These tests import presentation and nothing else, which is the point: the
vocabulary has to stand up without a mechanic to give it meaning. Service
delivery lives in the loader tests and rendering lives with the client.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tangl.presentation.geometry import NormalizedRect
from tangl.presentation.surface import HasSurface, Surface, SurfaceSlot


def test_a_slot_may_not_escape_its_plate() -> None:
    """The bounds rule the surface shares with the sandbox map plate.

    A rectangle off the edge draws nothing while looking well-formed in a world
    file, so it is refused where it is written rather than where it is drawn.
    """

    with pytest.raises(ValidationError):
        SurfaceSlot(holds="id_card", x=0.9, y=0.1, w=0.2, h=0.2)

    with pytest.raises(ValidationError):
        SurfaceSlot(holds="id_card", x=0.1, y=0.1, w=0.0, h=0.2)


def test_a_rect_may_not_be_nan() -> None:
    """The bounds rule cannot catch NaN on its own.

    Every comparison with NaN is false, so ``w=nan`` slips past ``w <= 0`` and
    then past ``x + w > 1.0`` as well, and reaches a renderer that turns it into
    a pixel rect. ``x=nan`` happens to be caught by the origin check and
    infinities by the extent check, which is what made the hole easy to miss --
    so the width and height cases are the ones asserted here.
    """

    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValidationError):
            NormalizedRect(x=0.1, y=0.1, w=bad, h=0.2)
        with pytest.raises(ValidationError):
            NormalizedRect(x=0.1, y=0.1, w=0.2, h=bad)


def test_a_surface_may_declare_slots_nothing_ever_fills() -> None:
    """Geometry outlives whatever happens to be on the desk this turn.

    The same tolerance the map plate has: a plate may name regions no location
    claims. It is what lets a desk be re-measured, re-dressed or replaced
    without a mechanic noticing.
    """

    surface = Surface(
        name="desk",
        slots={
            "bust_of_dear_leader": SurfaceSlot(holds="ornament", x=0.8, y=0.1, w=0.1, h=0.1)
        },
    )

    assert surface.slots["bust_of_dear_leader"].holds == "ornament"


def test_slots_keep_the_order_they_were_declared_in() -> None:
    """Authored order, not lexical.

    Where a surface declares two slots for one kind, this order is what decides
    which piece lands in which. The names here sort the opposite way from their
    declaration so the two cannot be confused for each other.
    """

    surface = Surface(
        name="desk",
        slots={
            "zulu": SurfaceSlot(holds="id_card", x=0.1, y=0.6, w=0.2, h=0.2),
            "alpha": SurfaceSlot(holds="id_card", x=0.4, y=0.6, w=0.2, h=0.2),
        },
    )

    assert list(surface.slots) == ["zulu", "alpha"]


def test_owning_the_capability_is_not_declaring_the_furniture() -> None:
    """``HasSurface`` defaults to none, so adopting it costs a world nothing."""

    class Counter(HasSurface):
        pass

    assert Counter().surface is None
