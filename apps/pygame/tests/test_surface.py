"""Rendering a zone as a surface, and the joins that decide what lands where.

The claim under test is the one the surface design rests on: a slot is a
presentation of a piece, never a second way to act. Clicking a document on the
desk must pick exactly what selecting its numbered entry picks.

The other claim is that the join is by name and nothing else. A slot holds a
``piece_kind``; a piece declares one; neither names the other. Both directions
have to degrade to *nothing* rather than to a guess, because a surface that
silently invents a placement is worse than one that draws no desk at all.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from tangl.journal.intent import PieceConstraints, PiecesAccepts  # noqa: E402
from tangl.pygame_client.__main__ import _keyed  # noqa: E402
from tangl.pygame_client.bridge import place_pieces  # noqa: E402
from tangl.pygame_client.models import (  # noqa: E402
    Choice,
    Line,
    PendingSelection,
    Piece,
    PickPiece,
    Surface,
    SurfaceSlot,
    Turn,
    Zone,
)
from tangl.pygame_client.stage import (  # noqa: E402
    CREAM,
    SELECTION_ROWS,
    LOGICAL_SIZE,
    PROSE_TOP,
    SCALE,
    Stage,
)

ZONE_UID = uuid4()

SURFACE = Surface(
    name="checkpoint_counter",
    band=(0.0, 0.62, 1.0, 0.38),
    slots=(
        SurfaceSlot(name="traveler", holds="candidate", x=0.34, y=0.50, w=0.32, h=0.10),
        SurfaceSlot(name="papers", holds="id_card", x=0.04, y=0.66, w=0.21, h=0.26),
        # Declared, and nothing in this packet fills it.
        SurfaceSlot(name="permit", holds="permit", x=0.28, y=0.66, w=0.21, h=0.26),
    ),
)


@pytest.fixture
def stage(tmp_path):
    made = Stage(asset_dir=tmp_path, title="surface test")
    yield made
    pygame.quit()


def _piece(piece_id: str, kind: str, *, label: str, zoned: bool = True) -> Piece:
    return Piece(
        piece_id=piece_id,
        kind=kind,
        text=f"{label} description",
        label=label,
        zone_ref=ZONE_UID if zoned else None,
    )


@pytest.fixture
def frame() -> Turn:
    """A checkpoint turn: a traveler, a passport, and one ticket with no slot."""

    return Turn(
        step=1,
        lines=[Line(text="Tomas Vey steps forward.")],
        pieces=[
            _piece("0:tomas", "candidate", label="Tomas Vey", zoned=False),
            _piece("0:passport", "id_card", label="passport"),
            _piece("0:ticket", "ticket", label="ferry ticket"),
        ],
        zones=[Zone(uid=ZONE_UID, role="packet", label="Credentials packet")],
        choices=[
            Choice(
                edge_id=uuid4(),
                text="Inspect a document",
                accepts=PiecesAccepts(
                    min=1, max=1, constraints=PieceConstraints(target_zone_ref=str(ZONE_UID))
                ),
            )
        ],
        surface=SURFACE,
    )


def _box(stage, slot_name: str):
    """The rect the renderer actually drew this slot in.

    Read back rather than recomputed. The stage rect narrows for the state panel
    and shrinks with the choice list, so a test that re-derives it agrees with
    the renderer only by luck -- which is how the first draft of this file
    passed while its arithmetic was wrong.
    """

    return next(box for slot, _piece, box in stage.slot_boxes if slot.name == slot_name)


def _centre(box) -> tuple[int, int]:
    return (box.centerx * SCALE, box.centery * SCALE)


# ── the join ─────────────────────────────────────────────────────────────


def test_a_slot_takes_the_piece_whose_kind_it_holds(frame) -> None:
    placed = dict((slot.name, piece.piece_id) for slot, piece in place_pieces(SURFACE, frame.pieces))

    assert placed == {"traveler": "0:tomas", "papers": "0:passport"}


def test_a_slot_no_piece_fills_is_simply_absent(frame) -> None:
    """An empty permit slot yields no placement, not an empty one."""

    placed = place_pieces(SURFACE, frame.pieces)

    assert "permit" not in {slot.name for slot, _ in placed}


def test_a_piece_no_slot_holds_is_absent_from_the_surface(frame) -> None:
    """The ferry ticket has no slot; it must not be forced into a spare one."""

    placed = place_pieces(SURFACE, frame.pieces)

    assert "0:ticket" not in {piece.piece_id for _, piece in placed}


def test_two_slots_of_one_kind_fill_in_declared_order() -> None:
    """Pieces in stream order against slots in *declared* order, every turn.

    The slot names here sort the opposite way from the order they are declared
    in, deliberately. An earlier version of this test used ``left``/``right``,
    which are alphabetical *and* declared in that order -- so it passed whether
    the pipeline preserved authored order or silently sorted, which is exactly
    what it was sorting.
    """

    surface = Surface(
        name="desk",
        slots=(
            SurfaceSlot(name="zulu", holds="id_card", x=0.1, y=0.6, w=0.2, h=0.2),
            SurfaceSlot(name="alpha", holds="id_card", x=0.4, y=0.6, w=0.2, h=0.2),
        ),
    )
    pieces = [
        _piece("first", "id_card", label="hers"),
        _piece("second", "id_card", label="his"),
    ]

    placed = [(slot.name, piece.piece_id) for slot, piece in place_pieces(surface, pieces)]

    assert placed == [("zulu", "first"), ("alpha", "second")]


# ── input parity ─────────────────────────────────────────────────────────


def test_a_desk_click_and_its_number_key_pick_the_same_piece(stage, frame) -> None:
    """The whole point: picking the thing you are looking at is the same act.

    §5.3 Input Parity wants every click reachable by keyboard, not a second list
    saying so. A card carrying its own number satisfies that outright, so the
    claim to test is that the card and the key agree -- not that the piece is
    listed twice.
    """

    pending = PendingSelection(choice=frame.choices[0])
    stage.draw(frame, pending)

    assert stage.hit(_centre(_box(stage, "papers"))) == PickPiece(piece_id="0:passport")

    number = stage.selection_numbers["0:passport"]
    assert _keyed(stage, frame, pending, number) == PickPiece(piece_id="0:passport")


def test_a_piece_on_the_desk_gives_its_row_back_to_the_desk(stage, frame) -> None:
    """It is drawn once, not once on the desk and again in the list.

    The saving is the point: on a 320x200 stage every row the list keeps is a
    row the desk does not get.
    """

    pending = PendingSelection(choice=frame.choices[0])
    stage.draw(frame, pending)
    actions = [action for _rect, action in stage.hitboxes]

    # On the desk, and only there.
    assert actions.count(PickPiece(piece_id="0:passport")) == 1
    # The ferry ticket has no slot, so it keeps its row -- and its own number.
    assert actions.count(PickPiece(piece_id="0:ticket")) == 1
    assert stage.selection_numbers.keys() == {"0:passport", "0:ticket"}


def test_the_number_on_a_card_survives_a_piece_leaving_the_selection(stage, frame) -> None:
    """Numbering comes from the page, not from a count kept beside it.

    Once a piece is picked it drops out of the offered set, and a card that had
    numbered itself by its own position would silently start disagreeing with
    the keyboard exactly when the player is mid-selection.
    """

    frame.choices[0].accepts.max = 2
    pending = PendingSelection(choice=frame.choices[0], picked=["0:ticket"])
    stage.draw(frame, pending)

    number = stage.selection_numbers["0:passport"]
    assert _keyed(stage, frame, pending, number) == PickPiece(piece_id="0:passport")


def test_a_piece_on_the_desk_is_inert_until_a_selection_wants_it(stage, frame) -> None:
    """Drawn always, clickable only while a choice is collecting pieces.

    Legibility and parity pull in different directions here: the packet must be
    visible whether or not anything is being picked, but a click outside a
    selection has no numbered row to be equivalent to.
    """

    stage.draw(frame)

    assert stage.hit(_centre(_box(stage, "papers"))) is None


def test_an_empty_slot_refuses_the_click_while_picking(stage, frame) -> None:
    pending = PendingSelection(choice=frame.choices[0])
    stage.draw(frame, pending)

    # Nothing filled it, so it was never drawn and there is nothing to click.
    assert "permit" not in {slot.name for slot, _piece, _box in stage.slot_boxes}


def test_a_card_is_clickable_exactly_when_it_carries_a_number(stage) -> None:
    """The pagination witness, and the invariant underneath it.

    With more candidates than a page holds, the surface can draw a card whose
    piece is on another page. Such a card has no number, so the keyboard cannot
    reach it -- and it must not be reachable by mouse either, or the two input
    routes disagree about what is on offer. Clickable iff numbered is the whole
    rule, and it is asserted as an equality so neither side can drift.
    """

    count = SELECTION_ROWS + 2
    surface = Surface(
        name="wide_desk",
        slots=tuple(
            SurfaceSlot(
                name=f"slot{i}",
                holds="id_card",
                x=0.02 + 0.32 * (i % 3),
                y=0.02 + 0.32 * (i // 3),
                w=0.28,
                h=0.28,
            )
            for i in range(count)
        ),
    )
    pieces = [_piece(f"doc{i}", "id_card", label=f"document {i}") for i in range(count)]
    turn = Turn(
        step=1,
        pieces=pieces,
        zones=[Zone(uid=ZONE_UID, role="packet", label="Credentials packet")],
        choices=[
            Choice(
                edge_id=uuid4(),
                text="Inspect a document",
                accepts=PiecesAccepts(
                    min=1, max=1, constraints=PieceConstraints(target_zone_ref=str(ZONE_UID))
                ),
            )
        ],
        surface=surface,
    )
    pending = PendingSelection(choice=turn.choices[0])
    stage.draw(turn, pending)

    drawn = {piece.piece_id for _slot, piece, _box in stage.slot_boxes}
    clickable = {
        action.piece_id for _rect, action in stage.hitboxes if isinstance(action, PickPiece)
    }

    # More cards are drawn than any one page can offer -- otherwise this proves
    # nothing about paging.
    assert len(drawn) > len(stage.selection_numbers)
    assert clickable == set(stage.selection_numbers)


# ── what the surface owes the rest of the frame ──────────────────────────


def test_the_panel_shows_only_what_the_surface_could_not_place(stage, frame) -> None:
    """The desk shows the passport; the column is left with the ticket."""

    placed = place_pieces(SURFACE, frame.pieces)
    rows = [text for text, _colour in stage.panel_rows(frame, columns=24, placed=placed)]

    assert any("ferry ticket" in row for row in rows)
    assert not any("passport" in row for row in rows)
    assert not any("Tomas Vey" in row for row in rows)


def test_the_panel_keeps_the_whole_packet_when_there_is_no_surface(stage, frame) -> None:
    """Sabotage check: with nothing placed, the column is exactly as it was."""

    rows = [text for text, _colour in stage.panel_rows(frame, columns=24)]

    assert any("passport" in row for row in rows)
    assert any("ferry ticket" in row for row in rows)


def test_prose_stops_above_everything_the_surface_draws(stage, frame) -> None:
    """Not merely above the band.

    The nameplate sits above the band, and taking the prose floor from the band
    alone painted text straight over it. This asserts the pixels where the
    renderer says it drew the nameplate: with enough prose to fill the stage, the
    card must still be there.
    """

    frame.lines = [Line(text="The queue shuffles forward again. " * 4)] * 8
    stage.draw(frame)
    box = _box(stage, "traveler")

    cream = sum(
        stage.surface.get_at((x, y))[:3] == CREAM
        for x in range(box.left + 1, box.right - 1)
        for y in range(box.top + 1, box.bottom - 1)
    )

    # Prose backs its rows with INK, so a nameplate drawn under the text would
    # be mostly dark rather than mostly card.
    assert cream > 0.5 * (box.w - 2) * (box.h - 2)


def test_the_prose_floor_clears_the_highest_placed_slot(stage, frame) -> None:
    """The same claim structurally, against the floor the layout was handed."""

    stage.draw(frame)

    assert stage.prose_floor <= min(box.top for _s, _p, box in stage.slot_boxes)


def test_a_slot_maps_into_the_rect_it_is_given(stage) -> None:
    """The one place the fractions become pixels, checked by hand.

    Everything else reads boxes back from the renderer, so this is what stops a
    consistent-but-wrong mapping from satisfying the whole file.
    """

    rect = pygame.Rect(20, 40, 200, 100)

    assert stage._rect_in(rect, 0.5, 0.25, 0.25, 0.5) == pygame.Rect(120, 65, 50, 50)
