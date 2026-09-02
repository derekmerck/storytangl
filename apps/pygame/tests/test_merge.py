"""Merging a multi-step envelope into one actionable frame.

The bridge yields one turn per step, but the player acts on a single frame, so
repeated staging across steps must collapse without losing distinct sprites.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from tangl.pygame_client.__main__ import _merge  # noqa: E402
from tangl.pygame_client.models import Choice, Line, StageImage, Turn  # noqa: E402


def _bg(source: str) -> StageImage:
    return StageImage(role="narrative_im", source=source)


def _sprite(source: str, slot: str | None = None) -> StageImage:
    return StageImage(role="dialog_im", source=source, x_slot=slot)


def test_repeated_staging_across_steps_is_deduplicated() -> None:
    """Both resolution batches restage the same scene; the player sees one."""

    merged = _merge([
        Turn(step=1, images=[_bg("quay.png"), _sprite("master.png")]),
        Turn(step=2, images=[_bg("quay.png"), _sprite("master.png")],
             choices=[Choice(edge_id=uuid4(), text="go on")]),
    ])

    assert [image.source for image in merged.images] == ["quay.png", "master.png"]


def test_distinct_sprites_both_survive() -> None:
    merged = _merge([
        Turn(step=1, images=[_sprite("clerk.png", "left")]),
        Turn(step=2, images=[_sprite("master.png", "right")]),
    ])

    assert {image.source for image in merged.images} == {"clerk.png", "master.png"}


def test_the_same_sprite_in_two_slots_is_not_a_duplicate() -> None:
    """An explicit slot makes a repeat deliberate rather than incidental."""

    merged = _merge([
        Turn(step=1, images=[_sprite("guard.png", "left"), _sprite("guard.png", "right")]),
    ])

    assert [image.x_slot for image in merged.images] == ["left", "right"]


def test_the_last_background_wins_when_the_scene_changes() -> None:
    """Selecting the earliest background would strand a stale scene."""

    merged = _merge([
        Turn(step=1, images=[_bg("quay.png")]),
        Turn(step=2, images=[_bg("warehouse.png")],
             choices=[Choice(edge_id=uuid4(), text="go on")]),
    ])

    backgrounds = [i.source for i in merged.images if i.role == "narrative_im"]
    assert backgrounds == ["warehouse.png"]


def test_lines_accumulate_and_only_the_last_step_offers_choices() -> None:
    edge = uuid4()
    merged = _merge([
        Turn(step=1, lines=[Line(text="first")], choices=[Choice(edge_id=uuid4(), text="stale")]),
        Turn(step=2, lines=[Line(text="second")], choices=[Choice(edge_id=edge, text="live")]),
    ])

    assert [line.text for line in merged.lines] == ["first", "second"]
    assert [choice.edge_id for choice in merged.choices] == [edge]


def _plate(source: str) -> StageImage:
    return StageImage(role="map_im", source=source)


def test_crossing_between_two_maps_keeps_only_the_latest_plate() -> None:
    """A plate is stage state, not transcript.

    A batch that leaves one map and arrives at another would otherwise carry
    both, and the renderer would pair a picture with the wrong geometry.
    """

    merged = _merge([
        Turn(step=1, images=[_plate("quay_map.png")], lines=[Line(text="the quay")]),
        Turn(step=2, images=[_plate("uplands_map.png")], lines=[Line(text="the uplands")]),
    ])

    plates = [image for image in merged.images if image.role == "map_im"]
    assert [image.source for image in plates] == ["uplands_map.png"]


def test_a_plate_and_a_background_do_not_displace_each_other() -> None:
    """They share the frame; only same-kind restaging collapses."""

    merged = _merge([
        Turn(step=1, images=[_bg("quai_bg.png"), _plate("quay_map.png")]),
    ])

    assert {image.role for image in merged.images} == {"narrative_im", "map_im"}
