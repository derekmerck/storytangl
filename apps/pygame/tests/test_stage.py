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
    PendingSelection,
    Piece,
    Turn,
    Zone,
)
from tangl.presentation.intent import PiecesAccepts, TextAccepts  # noqa: E402
from tangl.pygame_client.models import PagePanel  # noqa: E402
from tangl.pygame_client.stage import (  # noqa: E402
    CHOICE_KEYS,
    STAGED_LIMIT,
    STAGED_ROLES,
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
        assert rect.bottom <= stage.logical_size[1]
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
    assert rect.right <= stage.logical_size[0]
    assert stage._clip(long_choice.text).endswith("…")


def test_every_available_choice_is_clickable(stage: Stage) -> None:
    stage.draw(_turn(12, choice_count=3))

    for rect, action in stage.hitboxes:
        centre = (
            rect.centerx * stage.display_scale,
            rect.centery * stage.display_scale,
        )
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

    band = pygame.Surface((stage.logical_size[0], 140))
    band.blit(
        stage.surface,
        (0, 0),
        pygame.Rect(0, stage.prose_top, stage.logical_size[0], 140),
    )
    colours = {
        band.get_at((x, y))[:3]
        for x in range(0, stage.logical_size[0], 4)
        for y in range(0, 140, 4)
    }
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
    wide = len(stage._rows(plain, [], columns=(stage.logical_size[0] - 12) // 4))

    panelled = _packet_turn(lines=[Line(text="word " * 60)])
    stage.draw(panelled)
    narrow = len(
        stage._rows(
            panelled,
            [],
            columns=(stage.logical_size[0] - stage.panel_width - 12) // 4,
        )
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
    columns = (stage.panel_width - 10) // 4
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
    rows = stage.panel_rows(crowded, columns=(stage.panel_width - 10) // 4)
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

    narrow = stage._frac_x(0.5, width=20)
    wide = stage._frac_x(0.5, width=80)

    assert narrow + 20 // 2 == stage.logical_size[0] // 2
    assert wide + 80 // 2 == stage.logical_size[0] // 2


def test_a_placement_may_sit_outside_the_frame(stage: Stage) -> None:
    """Off-stage is a position, not a mistake.

    An image sliding from -0.5 to 0.2 is an entrance from the left, and every
    frame of it before arrival is partly outside. Clamping would turn that
    into a figure stuck against the edge.
    """

    assert stage._frac_x(-0.5, width=60) < 0
    assert stage._frac_x(1.5, width=60) > stage.logical_size[0] - 60
    # and the ordinary case still lands where it says
    assert stage._frac_x(0.5, width=60) + 30 == stage.logical_size[0] // 2


def test_fractional_media_y_places_the_baseline_not_the_top(stage: Stage) -> None:
    """A staged figure stands on something; the fraction is where it stands."""

    top = stage._frac_y(0.5, height=40)

    assert top + 40 == stage.logical_size[1] // 2


def test_a_vertical_placement_may_sit_outside_the_frame(stage: Stage) -> None:
    assert stage._frac_y(-0.5, height=40) < 0
    assert stage._frac_y(1.5, height=40) > stage.logical_size[1] - 40
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
    assert _fraction(-0.1) == -0.1         # off-stage, not out of range
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
    assert stage._frac_x(first.x_frac, 40) == stage._frac_x(second.x_frac, 40)


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
def test_an_explicit_fraction_is_never_held_on_screen(stage: Stage) -> None:
    """A placement is a decision already made; adjusting it breaks entrances."""

    assert stage.keep_on_screen
    assert stage._frac_x(-0.5, width=60) < 0


def test_a_fraction_is_exact_whatever_keep_says(stage: Stage) -> None:
    """Clamping preserves a name's meaning and destroys a number's.

    "Right" pulled into the visible band is still over that way. 0.75 pulled
    in, for an image wider than half the stage, ends up near the middle --
    a different position wearing the same hint. A world that cannot honour a
    coordinate should say a name instead; that is what names are for.
    """

    from tangl.pygame_client.models import StageImage

    at = lambda keep: stage._place_x(
        StageImage(role="staged_im", source="a.png", x_frac=0.98, keep=keep), 120, "mid"
    )

    assert at(None) == at("none") == at("whole") == at("width")
    assert at("whole") > stage.logical_size[0] - 120  # genuinely off the edge


def test_a_station_is_this_port_s_reading_not_a_coordinate(stage: Stage) -> None:
    """Names are advisory and each client answers them its own way.

    This port tucks the outer two against the edge with a gutter. That is not
    a fraction, and must not become one: worlds already staged by name sit
    where this calculation puts them.
    """

    w = 60
    assert stage._slot_x("left", w) == stage.margin
    assert stage._slot_x("right", w) == stage.logical_size[0] - w - stage.margin
    assert stage._slot_x("mid", w) == (stage.logical_size[0] - w) // 2
    assert stage._slot_x("nonsense", w) == stage._slot_x("mid", w)


def test_a_vertical_station_is_honoured_rather_than_discarded(stage: Stage) -> None:
    """`media_y` used to be declared and then dropped for want of a slot path."""

    h, floor = 40, 150
    assert stage._slot_y("bottom", h, floor) == floor - h
    assert stage._slot_y("top", h, floor) == stage.margin
    assert stage._slot_y(None, h, floor) == floor - h     # the shared baseline
    assert stage.margin <= stage._slot_y("mid", h, floor) <= floor - h


def test_keeping_a_station_whole_only_bites_when_it_would_clip(stage: Stage) -> None:
    """Edge-and-gutter already sits inside, so the policy is mostly inert on x.

    It earns its keep vertically, where a tall figure on the shared baseline
    can be pushed off the top of the frame.
    """

    assert stage._slot_x("right", 60) == stage._slot_x("right", 60, keep="none")

    tall, floor = 190, 150
    assert stage._slot_y("bottom", tall, floor, keep="none") < 0
    assert stage._slot_y("bottom", tall, floor, keep="whole") == 0


# ── end to end: hints -> fragment -> bridge -> StageImage -> pixels ──────────
#
# The helpers above are each correct in isolation, which is how a producer that
# refused what the consumer accepted, and a mirror applied twice, both passed a
# full suite. These go through the real path instead.


def _staged_fragment(tmp_path, name: str, size=(10, 12), role: str = "staged_im", **hints):
    """A staged image as a world would actually emit one."""
    from PIL import Image as PILImage
    from tangl.journal.fragments import MediaFragment
    from tangl.media.media_resource.resource_manager import ResourceManager
    from tangl.presentation.hints import StagingHints

    images = tmp_path / "images"
    images.mkdir(exist_ok=True)
    # Asymmetric on purpose: a left half that differs from the right is the
    # only way to tell a mirror from a mirror applied twice.
    #
    # And distinct per name, because media is content-addressed: two images
    # with identical bytes index to one resource, and the second name then
    # resolves to nothing.
    tint = (sum(name.encode()) * 37) % 200 + 55
    im = PILImage.new("RGBA", size, (0, 0, tint, 255))
    for y in range(size[1]):
        for x in range(size[0] // 2):
            im.putpixel((x, y), (255, 0, tint, 255))
    im.save(images / name)
    manager = ResourceManager(tmp_path)
    manager.index_directory("images")
    return MediaFragment(
        content=manager.get_rit(name), content_format="rit",
        media_role=role, staging_hints=StagingHints(**hints),
    )


def _tint(name: str) -> int:
    """The blue channel `_staged_fragment` gives this name."""

    return (sum(name.encode()) * 37) % 200 + 55


def _found(stage: "Stage", name: str) -> tuple[int, int, int, int] | None:
    """Bounding box of `name`'s pixels on the drawn stage, or None if absent.

    Keys on green being zero, which every test image has and no palette colour
    does, so scenery can never be mistaken for a figure. Reads the stage's own
    surface rather than any intermediate, because that is the only place a
    draw-order or clamping mistake actually shows.
    """

    want = _tint(name)
    w, h = stage.surface.get_size()
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            r, g, b, _ = stage.surface.get_at((x, y))
            if g == 0 and b == want:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _drawn(turn, tmp_path) -> "Stage":
    """A stage with `turn` actually rendered onto it."""

    stage = Stage(asset_dir=tmp_path / "images")
    stage.draw(turn)
    return stage


def test_end_to_end_an_off_stage_fraction_is_drawn_off_stage(
    stage: Stage, tmp_path
) -> None:
    """`[-2, 3]` at the model and `[0, 1]` at the bridge silently lost entrances."""

    from tangl.pygame_client.bridge import PygameSessionBridge

    # Centre a third of the way off the left edge, so part of it still lands.
    frag = _staged_fragment(tmp_path, "a.png", size=(40, 40), media_x=-0.03125, media_y=0.9)
    [turn] = PygameSessionBridge().build_turns([frag])
    assert turn.images[0].x_frac == -0.03125

    try:
        box = _found(_drawn(turn, tmp_path), "a.png")
        assert box is not None, "the image did not reach the stage at all"
        left, _, right, _ = box
        # Clipped by the frame, not pulled back into it: it starts hard against
        # column zero and only a sliver of its 40px width survives.
        assert left == 0
        assert right - left + 1 < 40, "the whole image is showing, so it was clamped"
        assert right == stage._frac_x(-0.03125, 40) + 39
    finally:
        pygame.quit()


def test_end_to_end_a_named_vertical_level_reaches_the_pixels(
    stage: Stage, tmp_path
) -> None:
    """`media_y="bottom"` was accepted, carried, and then had nowhere to go."""

    from tangl.pygame_client.bridge import PygameSessionBridge

    def baseline_of(name: str, level: str) -> int:
        frag = _staged_fragment(tmp_path, name, size=(20, 30),
                                media_x="mid", media_y=level)
        [turn] = PygameSessionBridge().build_turns([frag])
        assert turn.images[0].y_slot == level and turn.images[0].y_frac is None
        box = _found(_drawn(turn, tmp_path), name)
        assert box is not None, f"{level!r} put the image nowhere"
        return box[3]

    try:
        high, low = baseline_of("hi.png", "top"), baseline_of("lo.png", "bottom")
        assert high < low, "a named level did not move the image"
        assert high == stage.margin + 29  # tucked under the top gutter
        assert low == stage.logical_size[1] - 1  # standing on the floor
    finally:
        pygame.quit()


def test_end_to_end_a_named_level_takes_its_turn_in_the_depth_sort(tmp_path) -> None:
    """Sorting on `y_frac` alone gave every station a depth of zero.

    A `top` image then painted over a `bottom` one purely by arriving later,
    which is the painter's rule exactly backwards. Two overlapping figures --
    one placed by fraction, one by name -- are the only way to see it: with one
    vocabulary in play the bug is invisible.
    """

    from tangl.pygame_client.bridge import PygameSessionBridge

    # far.png's baseline is 100; tall.png is stationed at `top` but is tall
    # enough that its feet land at 160, so it is the nearer of the two and
    # belongs in front. They overlap on rows 60..99.
    #
    # tall.png arrives *first*, so arrival order and depth order disagree.
    # That matters: sort is stable, so any key that does not distinguish these
    # two -- the old `y_frac or 0.0`, which read the station as zero, or a
    # constant -- leaves them in arrival order and paints the far one in front.
    frags = [
        _staged_fragment(tmp_path, "tall.png", size=(40, 150), media_x=0.5, media_y="top"),
        _staged_fragment(tmp_path, "far.png", size=(40, 40), media_x=0.5, media_y=0.5),
    ]
    [turn] = PygameSessionBridge().build_turns(frags)

    try:
        stage = _drawn(turn, tmp_path)
        r, g, b, _ = stage.surface.get_at((stage.logical_size[0] // 2, 80))
        assert (g, b) == (0, _tint("tall.png")), (
            "the far figure painted over the near one: the station did not "
            "take its turn in the depth sort"
        )
    finally:
        pygame.quit()


def test_end_to_end_a_mirrored_image_is_mirrored_once(tmp_path) -> None:
    """Mirroring twice is the identity, and an attribute check cannot see it."""

    from tangl.pygame_client.bridge import PygameSessionBridge

    frag = _staged_fragment(tmp_path, "c.png", media_x=0.5, media_y=0.9, media_flip_h=True)
    [turn] = PygameSessionBridge().build_turns([frag])
    stage = Stage(asset_dir=tmp_path / "images")
    try:
        stage.draw(turn)
        # Read what actually landed on the stage, not an intermediate surface:
        # a mirror applied twice is invisible anywhere earlier.
        x0, y0 = stage._frac_x(0.5, 10), stage._frac_y(0.9, 12)
        row = y0 + 6
        left = stage.surface.get_at((x0, row))
        right = stage.surface.get_at((x0 + 9, row))
        # Source is red down its left half; mirrored once, red is on the right.
        assert right.r > left.r, "not mirrored, or mirrored twice"
    finally:
        pygame.quit()


def test_end_to_end_capacity_drops_the_tail_not_the_nearest(tmp_path) -> None:
    """Sorting before the cap spent the budget on whatever stood furthest away.

    Arrivals run near-to-far, which is what makes the two orders separable. A
    far-to-near fixture cannot fail: sorting ascending by depth returns the
    arrival order unchanged, so cap-then-sort and sort-then-cap keep the same
    images and the test passes either way.
    """

    from tangl.pygame_client.bridge import PygameSessionBridge
    from tangl.pygame_client.stage import STAGED_LIMIT

    over = 4
    names = [f"d{i}.png" for i in range(STAGED_LIMIT + over)]
    assert len({_tint(n) for n in names}) == len(names), "tints collided"
    frags = [
        _staged_fragment(tmp_path, name, size=(8, 8), media_x=0.5,
                         media_y=round(0.95 - i * 0.05, 4))
        for i, name in enumerate(names)
    ]
    [turn] = PygameSessionBridge().build_turns(frags)
    assert len(turn.images) == STAGED_LIMIT + over

    try:
        stage = _drawn(turn, tmp_path)
        drawn = {name for name in names if _found(stage, name) is not None}
        # The budget goes to the first arrivals -- the nearest -- and the tail
        # is what falls off. Sorting first would have kept the last `over`
        # instead, which are the furthest away.
        assert drawn == set(names[:STAGED_LIMIT])
    finally:
        pygame.quit()


def test_density_two_stage_scales_layout_but_not_staged_art(tmp_path) -> None:
    """A 640x400 declaration doubles UI density while pack-sized art stays natural."""

    from tangl.pygame_client.bridge import PygameSessionBridge
    from tangl.pygame_client.models import Surface, SurfaceSlot

    fragment = _staged_fragment(
        tmp_path,
        "large-stage.png",
        size=(80, 120),
        media_x=0.5,
        media_y=1.0,
    )
    [turn] = PygameSessionBridge().build_turns([fragment])
    staged_only = Turn(step=turn.step, images=list(turn.images))
    turn.lines = [Line(text=f"Line {index} " * 12) for index in range(30)]
    turn.choices = [Choice(edge_id=uuid4(), text=f"Choice {index}") for index in range(4)]
    turn.pieces = [
        Piece(piece_id=f"piece-{index}", kind="document", text=f"Document {index}")
        for index in range(18)
    ]
    turn.findings = [Finding(key="status", value="review")]
    turn.surface = Surface(
        name="desk",
        band=(0.0, 0.7, 1.0, 0.3),
        slots=(
            SurfaceSlot(
                name="document",
                holds="document",
                x=0.05,
                y=0.72,
                w=0.2,
                h=0.2,
            ),
        ),
    )

    stage = Stage(
        asset_dir=tmp_path / "images",
        logical_size=(640, 400),
        display_scale=1,
    )
    try:
        stage.draw(staged_only)
        box = _found(stage, "large-stage.png")
        assert box is not None
        left, top, right, bottom = box
        assert (right - left + 1, bottom - top + 1) == (80, 120)

        stage.draw(turn)

        assert stage.surface.get_size() == (640, 400)
        assert stage.window.get_size() == (640, 400)
        assert stage.density == 2
        assert stage.row_height == 18
        assert stage.margin == 20
        assert stage.prose_top == 48
        assert stage.panel_width == 208
        assert stage.font.get_height() >= 14
        assert stage.max_scroll > 0
        assert stage.slot_boxes
        assert stage.panel_page(
            stage.panel_rows(turn, columns=20),
            capacity=8,
        )[1] > 1
        assert all(
            0 <= rect.left <= rect.right <= 640
            and 0 <= rect.top <= rect.bottom <= 400
            for rect, _action in stage.hitboxes
        )

        pending = PendingSelection(
            choice=Choice(
                edge_id=uuid4(),
                text="Select documents",
                accepts=PiecesAccepts(min=1, max=3),
            )
        )
        stage.draw(turn, pending)
        assert stage.selection_pages(turn, pending) > 1
        assert all(rect.bottom <= 400 for rect, _action in stage.hitboxes)
    finally:
        pygame.quit()


@pytest.mark.parametrize(
    ("logical_size", "display_scale"),
    [((320, 200), 3), ((640, 400), 1)],
)
def test_input_coordinates_use_each_stage_local_display_scale(
    logical_size: tuple[int, int],
    display_scale: int,
) -> None:
    choice = Choice(edge_id=uuid4(), text="Continue")
    stage = Stage(logical_size=logical_size, display_scale=display_scale)
    try:
        stage.draw(Turn(step=1, choices=[choice]))
        rect, action = stage.hitboxes[0]
        click = (
            rect.centerx * stage.display_scale,
            rect.centery * stage.display_scale,
        )

        assert stage.hit(click) == action
    finally:
        pygame.quit()


def test_stage_refuses_an_unsupported_logical_extent_before_drawing() -> None:
    with pytest.raises(ValueError, match="does not support logical size 800x600"):
        Stage(logical_size=(800, 600))


def test_end_to_end_a_portrait_stands_on_the_stage_not_on_the_choice_list(
    tmp_path,
) -> None:
    """A portrait's feet must not move because the turn offered one more option.

    Portraits used to be floored at the top of the choice list, which cost them
    exactly the height that list took: the same character stood higher *and*
    drew smaller on a turn with eight choices than on one with one. Staged
    ornaments were floored at the stage all along, so two figures sharing a room
    disagreed about where the ground was, and the disagreement moved every turn.

    Both numbers are checked, because flooring and sizing failed together and
    either alone would leave the other free to drift.
    """

    from tangl.pygame_client.bridge import PygameSessionBridge

    def drawn(choice_count: int) -> tuple[tuple[int, int, int, int], int]:
        # Stationed right, and the choices kept short, so the list is drawn
        # over empty stage rather than over the figure we are measuring.
        frag = _staged_fragment(
            tmp_path, "face.png", size=(10, 12), role="dialog_im", media_x="right"
        )
        [turn] = PygameSessionBridge().build_turns([frag])
        turn.choices = [
            Choice(edge_id=uuid4(), text=f"c{index}") for index in range(choice_count)
        ]
        stage = _drawn(turn, tmp_path)
        box = _found(stage, "face.png")
        assert box is not None, "the portrait did not reach the stage at all"
        return box, stage.logical_size[1]

    (sparse, height), (crowded, _) = drawn(1), drawn(8)

    assert sparse == crowded, (
        "the portrait moved or resized when the choice list grew: "
        f"{sparse} with one choice, {crowded} with eight"
    )
    # The stage's own last row, the same floor `_draw_staged` measures from.
    assert sparse[3] == height - 1, (
        f"the portrait's feet land at {sparse[3]}, not on the stage floor {height - 1}"
    )
