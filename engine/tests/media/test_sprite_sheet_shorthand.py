"""Filename and compact shorthands are only ways of writing a manifest.

The claims under test are that a name states root, clip, grid and total and nothing
else parses as one; that per-cell values broadcast; that a stated total is filled
exactly with positive durations however lopsided the weights; and that a name can
be checked against an export that claims to be the same sheet.
"""

from __future__ import annotations

import itertools

import pytest

from tangl.media.sprite_sheets.aseprite import read_aseprite_export
from tangl.media.sprite_sheets.shorthand import DEFAULT_FRAME_MS, CompactSheet, SheetName, _distribute


# ── filenames ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("master_sprite-4x1", ("master_sprite", None, 4, 1, None)),
        ("master_sprite-idle-4x1", ("master_sprite", "idle", 4, 1, None)),
        ("master_sprite-idle-4x2-1600ms", ("master_sprite", "idle", 4, 2, 1600)),
        ("master_sprite-blink-2x1-2s", ("master_sprite", "blink", 2, 1, 2000)),
    ],
)
def test_a_sheet_name_states_root_clip_grid_and_total(stem: str, expected: tuple) -> None:
    name = SheetName.parse(stem)

    assert (name.root, name.clip, name.cols, name.rows, name.total_ms) == expected


@pytest.mark.parametrize(
    "stem",
    [
        "master_sprite",            # the still itself
        "master_sprite-idle-01",    # #418's loose frame suffix: disjoint by construction
        "master_sprite-idle",
        "master_sprite-0x1",
        "master_sprite-idle-4x1-0ms",
        "master sprite-4x1",
    ],
)
def test_names_that_are_not_sheets_are_not_read_as_sheets(stem: str) -> None:
    assert SheetName.parse(stem) is None


# ── the compact form ─────────────────────────────────────────────────────


def test_a_single_value_repeats_across_every_cell() -> None:
    compact = CompactSheet(sheet="2x2", role="idle", duration=250)

    assert compact.durations() == [250, 250, 250, 250]
    assert [(c.name, c.first, c.last) for c in compact.clips()] == [("idle", 0, 3)]


def test_an_array_gives_one_value_per_cell_and_runs_become_clips() -> None:
    compact = CompactSheet(sheet="4x1", role=["idle", "idle", "call", "response"], duration=[1800, 200, 900, 900])

    assert compact.durations() == [1800, 200, 900, 900]
    assert [(c.name, c.first, c.last) for c in compact.clips()] == [("idle", 0, 1), ("call", 2, 2), ("response", 3, 3)]


def test_a_role_split_across_two_runs_is_refused() -> None:
    with pytest.raises(ValueError, match="two separate runs"):
        CompactSheet(sheet="3x1", role=["idle", "call", "idle"]).clips()


def test_an_array_of_the_wrong_length_is_refused() -> None:
    with pytest.raises(ValueError, match="gives 3 values for 4 cells"):
        CompactSheet(sheet="2x2", duration=[1, 2, 3]).durations()


def test_with_a_total_durations_are_weights_that_divide_it_the_way_arithmetic_says() -> None:
    assert CompactSheet(sheet="3x1", total=1000).durations() == [334, 333, 333]
    assert CompactSheet(sheet="2x1", duration=[0.9, 0.1], total=2000).durations() == [1800, 200]
    assert (CompactSheet(sheet="2x1", duration=[9, 1], total=2000).durations()
            == CompactSheet(sheet="2x1", duration=[0.9, 0.1], total=2000).durations())


@pytest.mark.parametrize(("total", "weights", "expected"), [(3, [1000, 1, 1], [1, 1, 1]), (10, [1000, 1, 1], [8, 1, 1])])
def test_a_weight_too_small_for_a_millisecond_takes_one_without_overrunning_the_total(total, weights, expected) -> None:
    assert _distribute(total, weights) == expected


def test_every_total_is_filled_exactly_with_positive_durations() -> None:
    """The contract, swept: the two examples above are where it used to break."""

    for total, weights in itertools.product(range(3, 40), itertools.product([0.001, 1, 7, 1000], repeat=3)):
        durations = _distribute(total, list(weights))
        assert sum(durations) == total and min(durations) >= 1, (total, weights, durations)


def test_a_total_too_small_to_give_every_frame_a_millisecond_is_refused() -> None:
    with pytest.raises(ValueError, match="cannot give each of 3 frames"):
        CompactSheet(sheet="3x1", total=2).durations()


def test_no_timing_at_all_means_aseprites_default() -> None:
    assert CompactSheet(sheet="3x1").durations() == [DEFAULT_FRAME_MS] * 3


def test_an_image_that_does_not_divide_into_the_grid_is_refused() -> None:
    with pytest.raises(ValueError, match="does not divide"):
        CompactSheet(sheet="3x1").to_manifest("hero-3x1.png", (31, 12))


# ── one manifest ─────────────────────────────────────────────────────────


def _export(image: str, cells: int, durations: list[int], tags: list[dict]) -> dict:
    return {
        "frames": [
            {"frame": {"x": 10 * i, "y": 0, "w": 10, "h": 12}, "sourceSize": {"w": 10, "h": 12}, "duration": d}
            for i, d in enumerate(durations)
        ],
        "meta": {"image": image, "size": {"w": 10 * cells, "h": 12}, "frameTags": tags},
    }


def test_a_filename_is_shorthand_for_exactly_the_manifest_an_export_would_give() -> None:
    from_name = SheetName.parse("hero-walk-3x1-600ms").compact().to_manifest("hero-walk-3x1-600ms.png", (30, 12))
    exported = read_aseprite_export(
        _export("hero-walk-3x1-600ms.png", 3, [200, 200, 200], [{"name": "walk", "from": 0, "to": 2}])
    )

    assert from_name == exported


def test_a_name_and_an_export_that_agree_have_nothing_to_report() -> None:
    exported = read_aseprite_export(_export("hero-idle-4x1.png", 4, [100] * 4, [{"name": "idle", "from": 0, "to": 3}]))

    assert SheetName.parse("hero-idle-4x1-400ms").disagreements(exported) == []


def test_a_name_catches_an_export_laid_out_on_another_grid() -> None:
    """Four frames and a divisible image cannot tell 4x1 from 2x2; only the rects can."""

    four_across = CompactSheet(sheet="4x1").to_manifest("hero-4x1.png", (40, 12))

    assert SheetName.parse("hero-4x1").disagreements(four_across) == []
    [problem] = SheetName.parse("hero-2x2").disagreements(four_across)
    assert "not in the 2x2 cell its name says" in problem
