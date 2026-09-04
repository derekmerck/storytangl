"""Map-view rendering and the Input Parity floor it has to honour.

The claim under test is the one the whole map design rests on: a hotspot is a
presentation of a choice, never a second way to act. Clicking a region must
commit exactly what selecting its numbered entry commits.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from tangl.pygame_client.models import (  # noqa: E402
    Commit,
    Choice,
    Line,
    MapPlate,
    MapRegion,
    StageImage,
    Turn,
)
from tangl.pygame_client.stage import LOGICAL_SIZE, SCALE, Stage  # noqa: E402

PLATE = MapPlate(
    name="quay",
    image="quay_map.png",
    regions=(
        MapRegion(name="quayside", x=0.03, y=0.13, w=0.25, h=0.30),
        MapRegion(name="salon", x=0.75, y=0.43, w=0.21, h=0.28),
        MapRegion(name="lighthouse", x=0.60, y=0.05, w=0.10, h=0.10),
    ),
)


def _plate_file(tmp_path):
    """A stand-in plate. The renderer only needs something it can load."""

    path = tmp_path / "quay_map.png"
    pygame.image.save(pygame.Surface(LOGICAL_SIZE), str(path))
    return path


@pytest.fixture
def stage(tmp_path):
    _plate_file(tmp_path)
    made = Stage(asset_dir=tmp_path, title="map test")
    yield made
    pygame.quit()


@pytest.fixture
def frame() -> Turn:
    """A map turn: two claimed regions, one of them guarded, one region loose."""

    return Turn(
        step=1,
        images=[StageImage(role="map_im", source="quay_map.png")],
        lines=[Line(text="The district runs from the water to the salon steps.")],
        choices=[
            Choice(
                edge_id=uuid4(),
                text="Go to The Quayside",
                payload={"move": "quayside"},
                tags=frozenset({"ui:plate:quay:quayside"}),
            ),
            Choice(
                edge_id=uuid4(),
                text="Go to The Salon",
                available=False,
                unavailable_reason="guard_failed_or_unavailable",
                tags=frozenset({"ui:plate:quay:salon"}),
            ),
        ],
        plate=PLATE,
    )


def _centre(region: MapRegion) -> tuple[int, int]:
    """Window coordinates at the middle of a region."""

    x = (region.x + region.w / 2) * LOGICAL_SIZE[0]
    y = (region.y + region.h / 2) * LOGICAL_SIZE[1]
    return (round(x) * SCALE, round(y) * SCALE)


def test_a_region_click_commits_what_its_numbered_entry_commits(stage, frame) -> None:
    stage.draw(frame)
    quayside = next(r for r in PLATE.regions if r.name == "quayside")
    choice = frame.choices[0]

    # The authored activation payload rides along; a hotspot commits exactly
    # what the numbered row commits, payload included.
    assert stage.hit(_centre(quayside)) == Commit(
        edge_id=choice.edge_id, payload={"move": "quayside"}
    )


def test_a_guarded_region_is_drawn_but_refuses_the_click(stage, frame) -> None:
    """Dimmed and present, not absent — and still not actionable."""

    stage.draw(frame)
    salon = next(r for r in PLATE.regions if r.name == "salon")

    assert stage.hit(_centre(salon)) is None


def test_a_region_no_choice_claims_is_inert(stage, frame) -> None:
    """The plate names a lighthouse; nothing offers travel there."""

    stage.draw(frame)
    lighthouse = next(r for r in PLATE.regions if r.name == "lighthouse")

    assert stage.hit(_centre(lighthouse)) is None


def test_every_choice_stays_reachable_off_the_plate(stage, frame) -> None:
    """The legend is the floor: available choices are clickable there too."""

    stage.draw(frame)
    reachable = {action.edge_id for _rect, action in stage.hitboxes}

    assert frame.choices[0].edge_id in reachable
    assert frame.choices[1].edge_id not in reachable
    # One box on the plate and one legend row, both committing the same edge.
    bound = [h for h in stage.hitboxes if h[1].edge_id == frame.choices[0].edge_id]
    assert len(bound) == 2
    assert all(action == bound[0][1] for _rect, action in bound)


def test_a_turn_without_a_plate_falls_back_to_the_ordinary_layout(stage, frame) -> None:
    """No plate, no map: the client renders the world it is given."""

    frame.plate = None
    stage.draw(frame)
    quayside = next(r for r in PLATE.regions if r.name == "quayside")

    assert stage.hit(_centre(quayside)) is None
    assert {a.edge_id for _rect, a in stage.hitboxes} == {frame.choices[0].edge_id}


def test_the_plate_named_by_geometry_wins_over_a_stale_one(stage, frame, tmp_path):
    """A batch crossing two maps must not pair one picture with the other's rects."""

    stale = pygame.Surface(LOGICAL_SIZE)
    stale.fill((255, 0, 0))
    pygame.image.save(stale, str(tmp_path / "old_map.png"))
    frame.images.insert(0, StageImage(role="map_im", source="old_map.png"))

    stage.draw(frame)
    drawn = stage.surface.get_at((2, 2))[:3]

    # The stale plate is solid red; the named one is not.
    assert drawn != (255, 0, 0)


def test_an_unnamed_plate_image_refuses_to_guess(stage, frame, tmp_path):
    """Two staged maps and no name is ambiguous, so nothing is drawn."""

    pygame.image.save(pygame.Surface(LOGICAL_SIZE), str(tmp_path / "old_map.png"))
    frame.images.insert(0, StageImage(role="map_im", source="old_map.png"))
    frame.plate = MapPlate(name="quay", image=None, regions=PLATE.regions)

    stage.draw(frame)
    quayside = next(r for r in PLATE.regions if r.name == "quayside")

    assert stage.hit(_centre(quayside)) is None


def test_a_legend_row_wins_the_click_over_the_region_beneath_it(stage, frame):
    """The footer is drawn over the plate, so it must own the pixels it covers."""

    wide = MapRegion(name="quayside", x=0.0, y=0.0, w=1.0, h=1.0)
    frame.plate = MapPlate(name="quay", image="quay_map.png", regions=(wide,))
    stage.draw(frame)

    legend = next(
        rect for rect, action in stage.hitboxes
        if action.edge_id == frame.choices[0].edge_id and rect.h == 9 and rect.x == 4
    )
    click = ((legend.x + 1) * SCALE, (legend.y + 1) * SCALE)

    # Both the region and the legend row cover this pixel; the legend is on top.
    assert wide.x == 0.0 and wide.y == 0.0  # the region really does cover it
    assert stage.hit(click) == Commit(
        edge_id=frame.choices[0].edge_id, payload=frame.choices[0].payload
    )


def test_a_long_footer_pages_instead_of_covering_the_map(stage, frame):
    """Narration plus a long choice list must not grow over the whole plate."""

    frame.lines = [Line(text="A very long stretch of narration. " * 12)]
    frame.choices = [
        Choice(edge_id=uuid4(), text=f"Choice {n}", tags=frozenset())
        for n in range(12)
    ]
    stage.draw(frame)

    from tangl.pygame_client.stage import MAP_FOOTER_ROWS, ROW_H

    assert stage.max_scroll > 0
    footer_top = LOGICAL_SIZE[1] - MAP_FOOTER_ROWS * ROW_H - 2
    assert footer_top > LOGICAL_SIZE[1] // 2, "footer must not take half the plate"
    assert all(rect.y >= footer_top for rect, _action in stage.hitboxes)


def test_paging_a_long_footer_reaches_the_earlier_rows(stage, frame):
    """Scrolling exposes rows the first page could not fit."""

    frame.choices = [
        Choice(edge_id=uuid4(), text=f"Choice {n}") for n in range(12)
    ]
    stage.draw(frame)
    bottom = {a.edge_id for _r, a in stage.hitboxes}

    stage.scroll_by(-stage.max_scroll)
    stage.draw(frame)
    top = {a.edge_id for _r, a in stage.hitboxes}

    assert top != bottom
    assert frame.choices[0].edge_id in top


def test_an_attributed_line_keeps_its_speaker_in_the_footer(stage, frame):
    """The footer reuses ordinary row construction, so attribution survives."""

    frame.lines = [Line(text="You are late.", speaker="Master", manner="dryly")]
    stage.draw(frame)
    rows = stage._rows(frame, [])

    assert any(row.kind == "heading" and "Master" in row.text for row in rows)
    assert any(row.kind == "dialog" for row in rows)
