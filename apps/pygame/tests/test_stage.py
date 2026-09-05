"""Renderer tests. Headless via the dummy SDL driver; no display required."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from tangl.pygame_client.models import (  # noqa: E402
    Choice,
    Finding,
    Line,
    Piece,
    Turn,
    Zone,
)
from tangl.journal.intent import TextAccepts  # noqa: E402
from tangl.pygame_client.models import PagePanel  # noqa: E402
from tangl.pygame_client.stage import (  # noqa: E402
    LOGICAL_SIZE,
    PANEL_W,
    SCALE,
    Stage,
    choice_action,
    unsupported_reason,
)


@pytest.fixture
def stage() -> Stage:
    made = Stage()
    yield made
    pygame.quit()


def _turn(line_count: int, choice_count: int) -> Turn:
    return Turn(
        step=1,
        lines=[
            Line(text=f"A line of narration number {index} " * 3, speaker="Dockhand", manner="calls")
            for index in range(line_count)
        ],
        choices=[
            Choice(edge_id=uuid4(), text=f"choice {index}") for index in range(choice_count)
        ],
    )


@pytest.mark.parametrize("line_count", [1, 5, 20])
def test_choices_stay_on_the_logical_surface(stage: Stage, line_count: int) -> None:
    """A long exchange must never push the only way to continue off-screen.

    The dockhand contest alone merges five lines with the aftermath content.
    """

    stage.draw(_turn(line_count, choice_count=3))

    assert len(stage.hitboxes) == 3
    for rect, _action in stage.hitboxes:
        assert rect.bottom <= LOGICAL_SIZE[1]
        assert rect.top >= 0


def test_every_available_choice_is_clickable(stage: Stage) -> None:
    stage.draw(_turn(12, choice_count=3))

    for rect, action in stage.hitboxes:
        centre = (rect.centerx * SCALE, rect.centery * SCALE)
        assert stage.hit(centre) is not None
        assert stage.hit(centre).edge_id == action.edge_id


def test_unavailable_choices_are_shown_but_not_clickable(stage: Stage) -> None:
    """Decision Legibility: dimmed with a reason, not hidden."""

    turn = Turn(
        step=1,
        choices=[
            Choice(
                edge_id=uuid4(),
                text="Challenge the salon master",
                available=False,
                unavailable_reason="You have no reply yet.",
            ),
            Choice(edge_id=uuid4(), text="Challenge the dockhand"),
        ],
    )
    stage.draw(turn)

    assert len(stage.hitboxes) == 1
    assert stage.hitboxes[0][1].edge_id == turn.choices[1].edge_id


def test_a_paragraph_longer_than_the_surface_still_renders(stage: Stage) -> None:
    """Paging works over rendered rows, so an oversized line is not dropped."""

    turn = Turn(
        step=1,
        lines=[Line(text="word " * 400)],
        choices=[Choice(edge_id=uuid4(), text="continue")],
    )
    stage.draw(turn)

    band = pygame.Surface((LOGICAL_SIZE[0], 140))
    band.blit(stage.surface, (0, 0), pygame.Rect(0, 24, LOGICAL_SIZE[0], 140))
    colours = {band.get_at((x, y))[:3] for x in range(0, LOGICAL_SIZE[0], 4) for y in range(0, 140, 4)}
    assert len(colours) > 1, "prose band is blank"
    assert stage.max_scroll > 0, "an oversized paragraph should be scrollable"


def test_every_row_is_reachable_by_scrolling(stage: Stage) -> None:
    turn = Turn(
        step=1,
        lines=[Line(text=f"line {index} of narration") for index in range(40)],
        choices=[Choice(edge_id=uuid4(), text="continue")],
    )
    stage.draw(turn)
    assert stage.max_scroll > 0

    stage.scroll_by(-stage.max_scroll)
    assert stage.scroll == 0, "should reach the first row"
    stage.scroll_by(999)
    assert stage.scroll == stage.max_scroll, "should clamp at the last row"


def test_unloadable_media_degrades_to_its_text_floor(stage: Stage) -> None:
    """A URL or missing file must not vanish; its description stays reachable."""

    from tangl.pygame_client.models import StageImage

    turn = Turn(
        step=1,
        images=[
            StageImage(
                role="dialog_im",
                source="https://example.invalid/portrait.png",
                alt_text="A woman with red hair.",
            )
        ],
        choices=[Choice(edge_id=uuid4(), text="continue")],
    )
    stage.draw(turn)

    rows = stage._rows(turn, [turn.images[0]])
    assert any("red hair" in row.text for row in rows)
    assert all(row.kind == "alt" for row in rows)


def test_unloadable_media_without_alt_text_names_its_role(stage: Stage) -> None:
    from tangl.pygame_client.models import StageImage

    image = StageImage(role="narrative_im", source="/absent/bg.png")
    rows = stage._rows(Turn(step=1), [image])

    assert any("narrative_im" in row.text for row in rows)


# ── state panel (§5.1 Decision Legibility) ───────────────────────────────────


ZONE = uuid4()


def _packet_turn(**overrides) -> Turn:
    defaults = dict(
        step=1,
        lines=[Line(text="Tomas Vey steps forward.")],
        choices=[Choice(edge_id=uuid4(), text="Inspect a document")],
        zones=[Zone(uid=ZONE, role="packet", label="Credentials packet")],
        pieces=[
            Piece(piece_id="c", kind="candidate", text="Tomas Vey", label="Tomas Vey"),
            Piece(piece_id="0:passport", kind="id_card", text="crisp",
                  label="passport", zone_ref=ZONE),
        ],
    )
    defaults.update(overrides)
    return Turn(**defaults)


def test_a_turn_with_state_narrows_the_prose_and_draws_a_panel(stage) -> None:
    """The panel takes its width from the prose rather than sharing it.

    A document that scrolled away is a document the player cannot evaluate, so
    the space is reserved rather than contended for.
    """

    plain = Turn(step=1, lines=[Line(text="word " * 60)])
    stage.draw(plain)
    wide = len(stage._rows(plain, [], columns=(LOGICAL_SIZE[0] - 12) // 4))

    panelled = _packet_turn(lines=[Line(text="word " * 60)])
    stage.draw(panelled)
    narrow = len(
        stage._rows(panelled, [], columns=(LOGICAL_SIZE[0] - PANEL_W - 12) // 4)
    )

    assert narrow > wide, "prose rewraps into the narrower column"


def test_a_turn_without_state_draws_no_panel(stage) -> None:
    assert stage._has_state(Turn(step=1, lines=[Line(text="just prose")])) is False
    assert stage._has_state(_packet_turn()) is True


def test_an_empty_zone_still_renders(stage) -> None:
    """A targetable container with nothing in it is information, not absence."""

    turn = _packet_turn(pieces=[])

    stage.draw(turn)  # must not raise; the zone header and "(empty)" are drawn

    assert stage._has_state(turn) is True


def _crowded_turn() -> Turn:
    return _packet_turn(
        choices=[Choice(edge_id=uuid4(), text=f"choice {n}") for n in range(9)],
        pieces=[
            Piece(piece_id=f"0:doc{n}", kind="id_card", text="x",
                  label=f"a fairly long document name {n}", zone_ref=ZONE)
            for n in range(8)
        ],
        findings=[
            Finding(key=f"finding {n}", value="a long explanation " * 3, emphasis="warn")
            for n in range(4)
        ],
    )


def test_overflowing_panel_state_stays_reachable_by_paging(stage) -> None:
    """Acknowledging missing state is not the same as showing it.

    An overflow notice told the player something was hidden and gave them no way
    to read it, which does not meet the §5.1 floor this panel exists for.

    Asserted against the *visible* slice: `panel_rows` returns everything the
    panel knows about regardless of the page, so checking it would pass whether
    or not paging worked.
    """

    crowded = _crowded_turn()
    columns = (PANEL_W - 10) // 4
    rows = stage.panel_rows(crowded, columns=columns)
    capacity = 8
    _page, pages, _visible = stage.panel_page(rows, capacity=capacity)
    assert pages > 1, "fixture must actually overflow"

    seen: set[str] = set()
    for _ in range(pages):
        _page, _pages, visible = stage.panel_page(rows, capacity=capacity)
        assert len(visible) < len(rows), "a page must be a slice, not everything"
        seen |= {text for text, _colour in visible}
        stage.panel_scroll += 1

    assert {text for text, _colour in rows} <= seen, "every row must reach a page"


def test_panel_paging_wraps_back_to_the_first_page(stage) -> None:
    crowded = _crowded_turn()
    rows = stage.panel_rows(crowded, columns=(PANEL_W - 10) // 4)
    first = stage.panel_page(rows, capacity=8)

    _page, pages, _visible = first
    stage.panel_scroll += pages

    assert stage.panel_page(rows, capacity=8) == first


def test_the_panel_pager_is_reachable_by_click(stage) -> None:
    stage.draw(_crowded_turn())

    assert any(
        isinstance(action, PagePanel) for _rect, action in stage.hitboxes
    ), "paging must be reachable by click, not only by key"


def test_a_panel_that_fits_offers_no_pager(stage) -> None:
    stage.draw(_packet_turn())

    assert not any(isinstance(action, PagePanel) for _rect, action in stage.hitboxes)


def test_an_unsupported_map_choice_is_dimmed_and_explains_itself(stage) -> None:
    """A live-looking hotspot over dead pixels is the failure the map avoids.

    The hitbox already disappeared; the colour and the legend row still implied
    the choice was on offer.
    """

    choice = Choice(edge_id=uuid4(), text="Say something", accepts=TextAccepts())

    assert choice_action(choice) is None
    assert unsupported_reason(choice) == "needs text input"
    assert "needs text input" in Stage._choice_label(1, choice)
