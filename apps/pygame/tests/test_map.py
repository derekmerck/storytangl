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

    assert stage.hit(_centre(quayside)) == (choice.edge_id, choice.payload)


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
    reachable = {edge_id for _rect, edge_id, _payload in stage.hitboxes}

    assert frame.choices[0].edge_id in reachable
    assert frame.choices[1].edge_id not in reachable
    # One box on the plate and one legend row, both committing the same edge.
    bound = [h for h in stage.hitboxes if h[1] == frame.choices[0].edge_id]
    assert len(bound) == 2
    assert all(payload == frame.choices[0].payload for _rect, _edge, payload in bound)


def test_a_turn_without_a_plate_falls_back_to_the_ordinary_layout(stage, frame) -> None:
    """No plate, no map: the client renders the world it is given."""

    frame.plate = None
    stage.draw(frame)
    quayside = next(r for r in PLATE.regions if r.name == "quayside")

    assert stage.hit(_centre(quayside)) is None
    assert {edge for _rect, edge, _payload in stage.hitboxes} == {frame.choices[0].edge_id}
