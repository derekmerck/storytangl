"""Surface geometry as reference state: who publishes it, and what it says.

The claim under test is that the furniture belongs to the world and the join
belongs to nobody. A block declares where an id card lies; the credentials
mechanic declares which pieces are id cards; neither names the other, and two
worlds running the same mechanic serve different geometry over identical pieces.

The other claim is that this costs nothing where it is not used. A block with no
surface must advertise no channel and project no section -- otherwise every
world pays for a desk it does not have.

Delivery only. The surface vocabulary itself is exercised in
``engine/tests/presentation/test_surface.py``, which imports no mechanic; what is
tested here is that a world's declaration reaches a client through the ordinary
Service operation, with generic contributions folded in.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.sandbox.location import SandboxMapRegion
from tangl.presentation.surface import HasSurface
from tangl.mechanics.surface_story_info import (
    advertise_surface_info_channels,
    project_surface_info,
)
from tangl.service.dispatch import do_advertise_info_channels, do_get_story_info
from tangl.presentation.projection import ProjectionRequest
from tangl.story import Action, InitMode
from tangl.vm import Ledger
from tangl.vm.runtime.frame import PhaseCtx

# Registers the surface channels on the service dispatch.
import tangl.mechanics.surface_story_info  # noqa: F401


def _worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _action(ledger: Ledger, text: str) -> Action:
    return next(
        edge
        for edge in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if edge.text == text
    )


def _at_the_shift(world_name: str, entry_text: str):
    """Walk one world to its checkpoint block and return (ledger, ctx)."""

    bundle = WorldBundle.load(_worlds_dir() / world_name)
    world = WorldCompiler().compile(bundle)
    result = world.create_story(f"{world_name}_surface_demo", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    ledger.resolve_choice(_action(ledger, entry_text).uid)
    return ledger, PhaseCtx(
        graph=result.graph, cursor_id=ledger.cursor.uid, step=ledger.step
    )


def _slots(ledger: Ledger, ctx: PhaseCtx) -> dict[str, list]:
    state = do_get_story_info(
        ledger.cursor,
        ctx=ctx,
        request=ProjectionRequest(kinds=["surface_plate", "surface_slots"]),
    )
    sections = {section.section_id: section for section in state.sections}
    table = sections["surface_slots"]
    assert table.value.columns == ["Slot", "Holds", "x", "y", "w", "h"]
    return {row[0]: row for row in table.value.rows}


def test_a_block_with_a_surface_advertises_and_serves_it() -> None:
    ledger, ctx = _at_the_shift("credential_gate", "Work the scheduled shift")

    advertised = {a.kind for a in do_advertise_info_channels(ledger.cursor, ctx=ctx)}
    assert "surface_plate" in advertised

    slots = _slots(ledger, ctx)
    assert slots["papers"][1] == "id_card"
    assert slots["papers"][2:] == [0.04, 0.66, 0.21, 0.26]


def test_the_band_travels_as_numbers_not_as_prose() -> None:
    """Four rows the client reads, rather than one string it would have to parse."""

    ledger, ctx = _at_the_shift("credential_gate", "Work the scheduled shift")
    state = do_get_story_info(
        ledger.cursor, ctx=ctx, request=ProjectionRequest(kinds=["surface_plate"])
    )
    rows = {row.key: row.value for row in state.sections[0].value.items}

    assert rows["Name"] == "checkpoint_counter"
    assert [rows[f"Band {axis}"] for axis in "xywh"] == [0.0, 0.62, 1.0, 0.38]


def test_slots_arrive_in_the_order_the_world_declared_them() -> None:
    """Authored order, not lexical.

    Where a surface declares two slots for one kind, this order decides which
    piece lands in which, so sorting the projection would overrule the author --
    and would do it invisibly whenever the two orders happened to agree.

    `credential_gate` is a real witness precisely because its declaration order
    and its alphabetical order differ.
    """

    ledger, ctx = _at_the_shift("credential_gate", "Work the scheduled shift")
    state = do_get_story_info(
        ledger.cursor, ctx=ctx, request=ProjectionRequest(kinds=["surface_slots"])
    )
    names = [row[0] for row in state.sections[0].value.rows]

    assert names == ["traveler", "papers", "permit", "ticket", "loose_page"]
    assert names != sorted(names), "world chosen as a witness no longer discriminates"


def test_two_worlds_running_one_mechanic_serve_their_own_furniture() -> None:
    """The point of declaring it per block: same pieces, different desk."""

    gate, gate_ctx = _at_the_shift("credential_gate", "Work the scheduled shift")
    hall, hall_ctx = _at_the_shift("hall_monitor", "Monitor the morning halls")

    gate_slots = _slots(gate, gate_ctx)
    hall_slots = _slots(hall, hall_ctx)

    # Both hold an id card; neither holds it in the same place.
    assert gate_slots["papers"][1] == hall_slots["pass_id"][1] == "id_card"
    assert gate_slots["papers"][2:] != hall_slots["pass_id"][2:]


def test_a_block_that_could_have_a_surface_but_declares_none_publishes_nothing() -> None:
    """Owning the capability is not the same as declaring the furniture.

    This is the case the guard exists for. A block that is not ``HasSurface`` at
    all never reaches the handler -- dispatch filters it -- so asserting against
    one proves only that dispatch works. What has to be pinned is a block that
    *does* mix the mixin in and leaves ``surface`` unset, which is every world
    that adopts the capability before it measures its desk.
    """

    class Counter(HasSurface):
        pass

    assert advertise_surface_info_channels(caller=Counter(), ctx=None) == []
    assert (
        project_surface_info(
            caller=Counter(),
            ctx=None,
            request=ProjectionRequest(kinds=["surface_plate", "surface_slots"]),
        )
        is None
    )


def test_a_block_with_no_surface_publishes_nothing() -> None:
    """And the same holds through the real dispatch path."""

    bundle = WorldBundle.load(_worlds_dir() / "credential_gate")
    world = WorldCompiler().compile(bundle)
    result = world.create_story("gate_no_surface", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    ctx = PhaseCtx(graph=result.graph, cursor_id=ledger.cursor.uid, step=ledger.step)

    advertised = {a.kind for a in do_advertise_info_channels(ledger.cursor, ctx=ctx)}
    assert "surface_plate" not in advertised

    state = do_get_story_info(
        ledger.cursor,
        ctx=ctx,
        request=ProjectionRequest(kinds=["surface_plate", "surface_slots"]),
    )
    assert [s for s in state.sections if s.kind.startswith("surface")] == []


def test_the_map_plate_still_enforces_the_rule_it_now_shares() -> None:
    """The regression guard for lifting the bounds check into a shared base.

    ``SandboxMapRegion`` had this rule and its own copy of it. Nothing asserted
    the rule, so rebasing it could have dropped it silently -- and a hitbox off
    the edge of a plate is unclickable rather than visibly wrong.
    """

    with pytest.raises(ValidationError):
        SandboxMapRegion(x=0.9, y=0.1, w=0.2, h=0.2)

    with pytest.raises(ValidationError):
        SandboxMapRegion(x=0.1, y=0.1, w=float("nan"), h=0.2)

    assert SandboxMapRegion(x=0.03, y=0.13, w=0.25, h=0.30).as_row("quayside") == [
        "quayside",
        0.03,
        0.13,
        0.25,
        0.30,
    ]


