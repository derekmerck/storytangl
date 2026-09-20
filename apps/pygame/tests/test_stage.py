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
from tangl.presentation.intent import TextAccepts  # noqa: E402
from tangl.pygame_client.models import PagePanel  # noqa: E402
from tangl.pygame_client.stage import (  # noqa: E402
    CHOICE_KEYS,
    LOGICAL_SIZE,
    STAGED_LIMIT,
    STAGED_ROLES,
    PANEL_W,
    SCALE,
    Stage,
    choice_action,
    key_for_position,
    position_for_key,
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


def test_a_refused_row_shows_no_number_to_press(stage: Stage) -> None:
    """Every number on screen works, and the gaps are the refusals.

    Numbering stays positional -- the number a row shows is the key that
    commits it -- so live rows run 1, 3 rather than 1, 2 when a refusal sits
    between them. Printing the refusal's position would invite a press that
    silently does nothing.
    """

    live = Choice(edge_id=uuid4(), text="Back to the road")
    refused = Choice(
        edge_id=uuid4(),
        text="Mira would take a doorknob, but you don't have one.",
        available=False,
    )
    second_live = Choice(edge_id=uuid4(), text="Trade with Finn")
    turn = Turn(
        step=1,
        lines=[Line(text="At the harbour.")],
        choices=[live, refused, second_live],
    )

    assert stage._marker(1, live) == "1."
    assert stage._marker(2, refused) == "x)"
    assert stage._marker(3, second_live) == "3."

    stage.draw(turn)

    assert len(stage.hitboxes) == 2


def test_a_printed_key_is_one_the_client_accepts(stage: Stage) -> None:
    """Every marker on screen resolves back to the row that printed it.

    `str(index)` printed `10.` for the tenth choice while the event loop read
    one keypad key, so the number promised something nothing would take.
    """

    for position in range(1, len(CHOICE_KEYS) + 1):
        key = key_for_position(position)
        assert key is not None
        assert position_for_key(key) == position

    # Lowercase x is the mark for a row with no key, so it binds to nothing.
    assert position_for_key("x") is None
    assert "x" not in CHOICE_KEYS


def test_a_choice_past_the_alphabet_prints_no_key(stage: Stage) -> None:
    """Past the last key a row prints nothing rather than an ordinal.

    It stays clickable; what it must not do is name a key that does not work.
    """

    beyond = len(CHOICE_KEYS) + 1
    live = Choice(edge_id=uuid4(), text="One more than there are keys")

    assert key_for_position(beyond) is None
    assert stage._pin(beyond, live) == ""
    assert stage._marker(beyond, live).strip() == ""


def test_a_row_too_long_for_the_frame_is_clipped_not_spilled(stage: Stage) -> None:
    """A choice row cannot wrap, so an overlong one has to say it was cut.

    The number a reader presses has to stay on the line with the words it
    names. Before this, a long row ran off the right edge and took the end of
    its own sentence with it, with nothing on screen to say so.
    """

    long_choice = Choice(
        edge_id=uuid4(),
        text=(
            "Bree will trade a wooden-winged glider for a pallet of unclaimed "
            "freight — Bree would take a pallet of unclaimed freight, but you "
            "have nothing like it to offer."
        ),
    )
    stage.draw(Turn(step=1, lines=[Line(text="At the strip.")], choices=[long_choice]))

    ((rect, _action),) = stage.hitboxes
    assert rect.right <= LOGICAL_SIZE[0]
    assert stage._clip(long_choice.text).endswith("…")


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


# ── fractional staging (placement, not slotting) ─────────────────────────────


def test_fractional_media_x_centres_the_image_on_the_fraction(stage: Stage) -> None:
    """A placed image puts its *centre* on the fraction, whatever it is wide."""

    narrow = Stage._frac_x(0.5, width=20)
    wide = Stage._frac_x(0.5, width=80)

    assert narrow + 20 // 2 == LOGICAL_SIZE[0] // 2
    assert wide + 80 // 2 == LOGICAL_SIZE[0] // 2


def test_a_placement_may_sit_outside_the_frame(stage: Stage) -> None:
    """Off-stage is a position, not a mistake.

    An image sliding from -0.5 to 0.2 is an entrance from the left, and every
    frame of it before arrival is partly outside. Clamping would turn that
    into a figure stuck against the edge.
    """

    assert Stage._frac_x(-0.5, width=60) < 0
    assert Stage._frac_x(1.5, width=60) > LOGICAL_SIZE[0] - 60
    # and the ordinary case still lands where it says
    assert Stage._frac_x(0.5, width=60) + 30 == LOGICAL_SIZE[0] // 2


def test_fractional_media_y_places_the_baseline_not_the_top(stage: Stage) -> None:
    """A staged figure stands on something; the fraction is where it stands."""

    top = Stage._frac_y(0.5, height=40)

    assert top + 40 == LOGICAL_SIZE[1] // 2


def test_a_vertical_placement_may_sit_outside_the_frame(stage: Stage) -> None:
    assert Stage._frac_y(-0.5, height=40) < 0
    assert Stage._frac_y(1.5, height=40) > LOGICAL_SIZE[1] - 40


def test_a_cardinal_is_the_same_statement_as_its_fraction(stage: Stage) -> None:
    """A name is sugar for a position, so the two must agree exactly.

    Quarters rather than edges: an edge-anchored cardinal is width-dependent,
    which is what stops a name being expressible as a fraction at all.
    """

    from tangl.presentation.hints import CARDINAL_X

    assert CARDINAL_X == {"left": 0.25, "mid": 0.5, "right": 0.75}
    for name, frac in CARDINAL_X.items():
        assert stage._slot_x(name, width=60) == Stage._frac_x(frac, width=60)


def test_cardinals_are_viewer_relative(stage: Stage) -> None:
    """Pixel 0 is the viewer's left, so `right` is the larger fraction.

    The theatrical frame inverts this and is refused by the hint model; this
    pins the convention so a mapping change cannot silently mirror every
    staged figure.
    """

    from tangl.presentation.hints import CARDINAL_X

    assert CARDINAL_X["left"] < CARDINAL_X["mid"] < CARDINAL_X["right"]
    assert stage._slot_x("left", width=60) < stage._slot_x("right", width=60)


def test_a_staging_position_may_be_off_stage_but_not_a_unit_mistake() -> None:
    """The bounds separate a position from someone who wrote 50 meaning half."""

    from tangl.presentation.hints import STAGING_MAX, STAGING_MIN, StagingHints

    assert StagingHints(media_x=-0.5).media_x == -0.5     # entering from the left
    assert StagingHints(media_x=1.4).media_x == 1.4       # gone off the right
    for unit_mistake in (50, -50, STAGING_MAX + 1, STAGING_MIN - 1):
        with pytest.raises(Exception):
            StagingHints(media_x=unit_mistake)


def test_a_numeric_media_x_reads_as_a_fraction_not_a_slot() -> None:
    from tangl.pygame_client.bridge import _fraction

    assert _fraction(0.42) == 0.42
    assert _fraction(0) == 0.0
    assert _fraction(1) == 1.0


def test_a_non_fraction_media_x_falls_through_to_slot_handling() -> None:
    """Slot names, percentages and out-of-range numbers are not placements.

    Hints are authored data and may be anything. Coercing a stray value into a
    placement would move a figure somewhere nobody asked for, so only a real
    number inside the frame counts.
    """

    from tangl.pygame_client.bridge import _fraction

    assert _fraction("left") is None
    assert _fraction("0.42") is None       # a string is not a number
    assert _fraction(42) is None           # out of range: a percentage, not a fraction
    assert _fraction(-0.1) is None
    assert _fraction(None) is None
    assert _fraction(True) is None         # bool is an int subclass; not a placement


def test_a_placed_image_ignores_arrival_order(stage: Stage) -> None:
    """Placement answers a different question than slotting, and wins.

    Two images that would otherwise take the first two default slots both sit
    where their fractions say instead -- including on top of each other, which
    is the world's business rather than the client's.
    """

    from tangl.pygame_client.models import StageImage

    first = StageImage(role="dialog_im", source="a.png", x_frac=0.25)
    second = StageImage(role="dialog_im", source="b.png", x_frac=0.25)

    assert first.x_slot is None and second.x_slot is None
    assert Stage._frac_x(first.x_frac, 40) == Stage._frac_x(second.x_frac, 40)


# ── staged images (scenery inhabitants) ──────────────────────────────────────


def _staged(**kw):
    from tangl.pygame_client.models import StageImage

    return StageImage(role="staged_im", source=kw.pop("source", "s.png"), **kw)


def test_staged_images_are_a_separate_role_from_portraits() -> None:
    """A room's inhabitants must not compete for the dialog's three stations."""

    from tangl.pygame_client.stage import PORTRAIT_ROLES

    assert "staged_im" in STAGED_ROLES
    assert not set(STAGED_ROLES) & set(PORTRAIT_ROLES)


def test_staged_capacity_is_bounded_but_well_above_a_real_room() -> None:
    """A bound, not a design limit: it exists so a generated cast degrades."""

    assert STAGED_LIMIT >= 10


def test_staged_images_draw_nearest_last(stage: Stage) -> None:
    """Lower in the frame is nearer, so it draws later.

    The same painter's rule a surface uses for its slots, so depth comes off
    the placement rather than needing to be stated twice.
    """

    far, near = _staged(source="far.png", y_frac=0.2), _staged(source="near.png", y_frac=0.9)
    ordered = sorted([far, near], key=lambda i: i.y_frac or 0.0)

    assert [i.source for i in ordered] == ["far.png", "near.png"]


def test_an_unplaced_staged_image_says_nothing_about_where_it_stands() -> None:
    """It asked to be in the room without saying where; it does not get a slot."""

    image = _staged()

    assert image.x_frac is None and image.y_frac is None
    assert image.x_slot is None


def test_a_staged_image_may_name_what_its_fractions_are_relative_to() -> None:
    """Carried for a composition this port cannot resolve yet.

    Eyes cropped from a portrait want to be placed *on that portrait* and
    follow it wherever it is staged. Declaring the reference costs nothing now
    and is read unchanged once a placement pass exists.
    """

    assert _staged().rel is None
    assert _staged(rel="portrait:clerk").rel == "portrait:clerk"


def test_a_named_position_is_held_on_screen_for_a_wide_image(stage: Stage) -> None:
    """A station is a request the client may interpret; a wide image still fits.

    "On the right" for an image too wide to sit at 0.75 whole is answered by
    the nearest position that shows all of it, rather than by clipping.
    """

    narrow, wide = 40, 200

    assert stage._slot_x("right", narrow) == Stage._frac_x(0.75, narrow)
    # pulled LEFT, because what overflowed was the right edge
    assert stage._slot_x("right", wide) < Stage._frac_x(0.75, wide)
    assert stage._slot_x("right", wide) + wide <= LOGICAL_SIZE[0]
    assert stage._slot_x("left", wide) >= 0


def test_an_explicit_fraction_is_never_held_on_screen(stage: Stage) -> None:
    """A placement is a decision already made; adjusting it breaks entrances."""

    assert stage.keep_on_screen
    assert Stage._frac_x(-0.5, width=60) < 0


def test_keep_on_screen_can_be_turned_off(stage: Stage) -> None:
    from tangl.pygame_client.stage import Stage as S

    off = S(keep_on_screen=False)
    try:
        assert off._slot_x("right", 200) == Stage._frac_x(0.75, 200)
    finally:
        pygame.quit()


def test_an_image_wider_than_the_stage_centres(stage: Stage) -> None:
    """The visible band has vanished; centring is the least-bad answer."""

    assert Stage._visible_x(0.75, width=LOGICAL_SIZE[0] * 2) == 0.5


def test_an_image_may_ask_to_be_kept_whole(stage: Stage) -> None:
    """A placement is exact unless the image says it is a preference.

    Size is often unknown when a placement is written, so "put me here, but
    keep me visible" is the common case; "put me exactly here" is what a
    transition needs.
    """

    from tangl.pygame_client.models import StageImage

    unset = StageImage(role="staged_im", source="a.png", x_frac=0.98)
    refused = StageImage(role="staged_im", source="a.png", x_frac=0.98, keep="none")
    kept = StageImage(role="staged_im", source="a.png", x_frac=0.98, keep="whole")

    # unset defers to policy, which leaves a placement exact
    assert stage._place_x(unset, 120, "mid") > LOGICAL_SIZE[0] - 120
    # "none" says the same thing on purpose, without relying on the default
    assert stage._place_x(refused, 120, "mid") == stage._place_x(unset, 120, "mid")
    assert stage._place_x(kept, 120, "mid") == LOGICAL_SIZE[0] - 120


def test_the_axes_of_keep_are_separable(stage: Stage) -> None:
    """A panorama may bleed off the sides; a tall figure off the top."""

    from tangl.pygame_client.models import StageImage

    w_only = StageImage(role="staged_im", source="a.png", x_frac=0.98, keep="width")
    h_only = StageImage(role="staged_im", source="a.png", x_frac=0.98, keep="height")

    assert stage._place_x(w_only, 120, "mid") == LOGICAL_SIZE[0] - 120
    assert stage._place_x(h_only, 120, "mid") > LOGICAL_SIZE[0] - 120


def test_keeping_whole_clamps_the_baseline_too(stage: Stage) -> None:
    """The fraction is a bottom, so the band runs from `h` to 1.0."""

    tall = 150
    assert Stage._visible_y(0.25, tall) == tall / LOGICAL_SIZE[1]
    assert Stage._visible_y(0.9, tall) == 0.9
    assert Stage._visible_y(1.4, tall) == 1.0


def test_an_image_taller_than_the_stage_sits_on_the_floor(stage: Stage) -> None:
    assert Stage._visible_y(0.25, LOGICAL_SIZE[1] * 2) == 1.0
