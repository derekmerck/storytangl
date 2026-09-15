"""Sprite-sheet manifests: Aseprite's shape, clip timing, and the shorthands.

The claims under test are that a real Aseprite export reads and writes back in its
own shape; that one timing function answers "which frame now" for every client; and
that the filename and compact forms are only ways of writing the same manifest.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tangl.presentation.hints import StagingHints
from tangl.presentation.sprite_sheet import (
    DEFAULT_FRAME_MS,
    CompactSheet,
    SheetName,
    SpriteSheetManifest,
)


def _frame(x: int, duration: int, *, w: int = 10, h: int = 12, name: str | None = None) -> dict:
    record = {
        "frame": {"x": x, "y": 0, "w": w, "h": h},
        "rotated": False,
        "trimmed": False,
        "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h},
        "sourceSize": {"w": w, "h": h},
        "duration": duration,
    }
    if name is not None:
        record["filename"] = name
    return record


def _export(tags: list[dict], durations: list[int] = (100, 100, 100)) -> dict:
    """An export in Aseprite's default hash layout, fields as its exporter writes them."""

    return {
        "frames": {f"hero {i}.aseprite": _frame(i * 10, d) for i, d in enumerate(durations)},
        "meta": {
            "app": "https://www.aseprite.org/",
            "version": "1.3",
            "image": "hero-3x1.png",
            "format": "RGBA8888",
            "size": {"w": 10 * len(durations), "h": 12},
            "scale": "1",
            "frameTags": tags,
            "layers": [{"name": "Layer 1", "opacity": 255, "blendMode": "normal"}],
            "slices": [],
        },
    }


# ── the format ───────────────────────────────────────────────────────────


def test_an_aseprite_hash_export_reads_in_timeline_order() -> None:
    sheet = SpriteSheetManifest.model_validate(
        _export([{"name": "walk", "from": 0, "to": 2, "direction": "forward", "color": "#000000ff"}])
    )

    assert [f.filename for f in sheet.frames] == ["hero 0.aseprite", "hero 1.aseprite", "hero 2.aseprite"]
    assert sheet.clip_names() == ["walk"]


def test_the_array_layout_is_the_same_sheet() -> None:
    hashed = _export([{"name": "walk", "from": 0, "to": 2}])
    arrayed = {**hashed, "frames": [{"filename": k, **v} for k, v in hashed["frames"].items()]}

    assert SpriteSheetManifest.model_validate(arrayed) == SpriteSheetManifest.model_validate(hashed)


def test_repeat_reads_from_a_quoted_string_and_writes_back_as_one() -> None:
    """Aseprite writes ``"repeat": "3"``; an export must survive a round trip."""

    sheet = SpriteSheetManifest.model_validate(_export([{"name": "walk", "from": 0, "to": 2, "repeat": "3"}]))
    dumped = sheet.model_dump()

    assert sheet.meta.frame_tags[0].repeat == 3
    assert dumped["meta"]["frameTags"][0]["repeat"] == "3"
    assert "spriteSourceSize" in dumped["frames"][0] and "frameTags" in dumped["meta"]
    assert SpriteSheetManifest.model_validate(dumped) == sheet


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda e: e["frames"]["hero 0.aseprite"].update(rotated=True), "rotated"),
        (lambda e: e["frames"]["hero 2.aseprite"]["frame"].update(x=25), "outside"),
        (lambda e: e["meta"]["frameTags"].append({"name": "run", "from": 1, "to": 3}), "reaches frame 3"),
        (lambda e: e["meta"]["frameTags"].append({"name": "walk", "from": 0, "to": 0}), "declared twice"),
        (lambda e: e["meta"]["frameTags"][0].update(repeat="twice"), "positive integer"),
        (lambda e: e["meta"]["frameTags"][0].update({"from": 2, "to": 1}), "ends before it starts"),
        (lambda e: e["frames"]["hero 1.aseprite"].update(duration=0), "greater than 0"),
    ],
)
def test_a_sheet_that_cannot_be_played_is_refused(mutate, message: str) -> None:
    export = _export([{"name": "walk", "from": 0, "to": 2}])
    mutate(export)

    with pytest.raises(ValidationError, match=message):
        SpriteSheetManifest.model_validate(export)


# ── clips and timing ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("direction", "expected"),
    [
        ("forward", [0, 1, 2]),
        ("reverse", [2, 1, 0]),
        # Out and back without repeating either end, so the next pass starts cleanly.
        ("pingpong", [0, 1, 2, 1]),
        ("pingpong_reverse", [2, 1, 0, 1]),
    ],
)
def test_direction_orders_one_pass(direction: str, expected: list[int]) -> None:
    sheet = SpriteSheetManifest.model_validate(_export([{"name": "c", "from": 0, "to": 2, "direction": direction}]))

    assert sheet.sequence("c") == expected


def test_a_frame_covers_its_start_but_not_its_end() -> None:
    sheet = SpriteSheetManifest.model_validate(_export([{"name": "idle", "from": 0, "to": 1}], durations=[1800, 200]))

    at = [sheet.frame_index_at("idle", t, loop=True) for t in (-5, 0, 1799, 1800, 1999, 2000, 3800)]

    assert at == [0, 0, 0, 1, 1, 0, 1]


def test_an_unrepeated_clip_plays_once_and_holds_its_last_frame() -> None:
    """Absent ``repeat`` is Aseprite's "once on export"; looping is a per-use hint."""

    sheet = SpriteSheetManifest.model_validate(_export([{"name": "call", "from": 0, "to": 2}]))

    assert sheet.frame_index_at("call", 299) == 2
    assert sheet.frame_index_at("call", 300) == 2
    assert sheet.frame_index_at("call", 10_000) == 2
    assert sheet.frame_index_at("call", 10_000, loop=True) == 1


def test_repeat_plays_that_many_passes_before_holding() -> None:
    sheet = SpriteSheetManifest.model_validate(
        _export([{"name": "c", "from": 0, "to": 2, "direction": "pingpong", "repeat": "2"}], durations=[10, 20, 30])
    )
    one_pass = 10 + 20 + 30 + 20

    assert sheet.frame_index_at("c", one_pass + 5) == 0          # second pass, first frame
    assert sheet.frame_index_at("c", one_pass * 2 - 1) == 1      # last frame of pass two
    assert sheet.frame_index_at("c", one_pass * 2) == 1          # held


def test_an_untagged_sheet_is_one_clip_and_a_tagged_one_names_its_clips() -> None:
    untagged = SpriteSheetManifest.model_validate(_export([]))
    tagged = SpriteSheetManifest.model_validate(_export([{"name": "idle", "from": 0, "to": 0}]))

    assert untagged.sequence(None) == untagged.sequence("anything") == [0, 1, 2]
    assert tagged.sequence(None) == [0]
    with pytest.raises(KeyError, match="no clip named 'call'"):
        tagged.sequence("call")


def test_the_pivot_comes_from_the_slice_named_pivot() -> None:
    export = _export([])
    export["meta"]["slices"] = [
        {"name": "hitbox", "keys": [{"frame": 0, "bounds": {"x": 0, "y": 0, "w": 10, "h": 12}, "pivot": {"x": 1, "y": 1}}]},
        {"name": "pivot", "color": "#0000ffff", "keys": [{"frame": 0, "bounds": {"x": 0, "y": 0, "w": 10, "h": 12}, "pivot": {"x": 5, "y": 11}}]},
    ]

    assert SpriteSheetManifest.model_validate(export).pivot().model_dump() == {"x": 5, "y": 11}


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
    assert [(t.name, t.from_frame, t.to_frame) for t in compact.tags()] == [("idle", 0, 3)]


def test_an_array_gives_one_value_per_cell_and_runs_become_tags() -> None:
    compact = CompactSheet(sheet="4x1", role=["idle", "idle", "call", "response"], duration=[1800, 200, 900, 900])

    assert compact.durations() == [1800, 200, 900, 900]
    assert [(t.name, t.from_frame, t.to_frame) for t in compact.tags()] == [
        ("idle", 0, 1), ("call", 2, 2), ("response", 3, 3)
    ]


def test_a_role_split_across_two_runs_is_refused() -> None:
    with pytest.raises(ValueError, match="two separate runs"):
        CompactSheet(sheet="3x1", role=["idle", "call", "idle"]).tags()


def test_an_array_of_the_wrong_length_is_refused() -> None:
    with pytest.raises(ValueError, match="gives 3 values for 4 cells"):
        CompactSheet(sheet="2x2", duration=[1, 2, 3]).durations()


def test_with_a_total_durations_are_weights_that_fill_it_exactly() -> None:
    """1000 ms over three equal frames cannot be three equal integers."""

    assert sum(CompactSheet(sheet="3x1", total=1000).durations()) == 1000
    assert CompactSheet(sheet="3x1", total=1000).durations() == [334, 333, 333]
    assert CompactSheet(sheet="2x1", duration=[0.9, 0.1], total=2000).durations() == [1800, 200]
    assert (CompactSheet(sheet="2x1", duration=[9, 1], total=2000).durations()
            == CompactSheet(sheet="2x1", duration=[0.9, 0.1], total=2000).durations())


def test_no_timing_at_all_means_aseprites_default() -> None:
    assert CompactSheet(sheet="3x1").durations() == [DEFAULT_FRAME_MS] * 3


def test_a_filename_is_shorthand_for_exactly_the_manifest_it_expands_to() -> None:
    """One reader: the name, the compact form and an explicit export agree."""

    from_name = SheetName.parse("hero-walk-3x1-600ms").compact().to_manifest("hero-walk-3x1-600ms.png", (30, 12))
    explicit = SpriteSheetManifest.model_validate(
        {
            "frames": [{"filename": f"hero-walk-3x1-600ms.png {i}", **_frame(i * 10, 200)} for i in range(3)],
            "meta": {"image": "hero-walk-3x1-600ms.png", "size": {"w": 30, "h": 12},
                     "frameTags": [{"name": "walk", "from": 0, "to": 2}]},
        }
    )

    assert from_name.frames == [f.model_copy(update={"sprite_source_size": None, "source_size": None}) for f in explicit.frames]
    assert from_name.meta.frame_tags == explicit.meta.frame_tags


def test_a_sidecar_must_agree_with_the_grid_its_filename_states() -> None:
    sheet = CompactSheet(sheet="4x1").to_manifest("hero-4x1.png", (40, 12))

    sheet.check_grid(4, 1)
    with pytest.raises(ValueError, match="cell its name says"):
        sheet.check_grid(2, 2)


def test_an_image_that_does_not_divide_into_the_grid_is_refused() -> None:
    with pytest.raises(ValueError, match="does not divide"):
        CompactSheet(sheet="3x1").to_manifest("hero-3x1.png", (31, 12))


# ── the per-use hint ─────────────────────────────────────────────────────


def test_the_clip_is_selected_per_use_beside_its_timing() -> None:
    hints = StagingHints(media_x="right", media_clip="call", media_timing="loop")

    assert hints.model_dump(exclude_none=True) == {"media_x": "right", "media_timing": "loop", "media_clip": "call"}
