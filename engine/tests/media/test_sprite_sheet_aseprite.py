"""Reading Aseprite's JSON export into the client-facing manifest.

The claims under test are that an export reads as Aseprite's exporter writes it,
and that everything the subset accepts is honoured rather than dropped: trimmed
frames keep their place on the canvas, a pivot follows its slice keys through time
and is measured from each key's bounds, and repeat reaches the clip. What cannot be
honoured is refused at load, not misrendered later.
"""

from __future__ import annotations

import json

import pytest

from tangl.media.sprite_sheets.aseprite import read_aseprite_export


def _frame(x: int, duration: int = 100, *, w: int = 10, h: int = 12) -> dict:
    return {
        "frame": {"x": x, "y": 0, "w": w, "h": h},
        "rotated": False,
        "trimmed": False,
        "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h},
        "sourceSize": {"w": w, "h": h},
        "duration": duration,
    }


def _export(tags: list[dict] = (), durations: list[int] = (100, 100, 100), slices: list[dict] = ()) -> dict:
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
            "frameTags": list(tags),
            "layers": [{"name": "Layer 1", "opacity": 255, "blendMode": "normal"}],
            "slices": list(slices),
        },
    }


def _key(frame: int, pivot: tuple[int, int] | None, *, bounds=(0, 0, 10, 12)) -> dict:
    x, y, w, h = bounds
    key = {"frame": frame, "bounds": {"x": x, "y": y, "w": w, "h": h}}
    if pivot is not None:
        key["pivot"] = {"x": pivot[0], "y": pivot[1]}
    return key


# ── reading ──────────────────────────────────────────────────────────────


def test_a_hash_export_reads_in_timeline_order() -> None:
    sheet = read_aseprite_export(_export([{"name": "walk", "from": 0, "to": 2, "color": "#000000ff"}], [10, 20, 30]))

    assert [f.duration_ms for f in sheet.frames] == [10, 20, 30]
    assert [f.rect.x for f in sheet.frames] == [0, 10, 20]
    assert (sheet.image, sheet.canvas.w, sheet.clip_names()) == ("hero-3x1.png", 10, ["walk"])


def test_the_array_layout_is_the_same_sheet() -> None:
    hashed = _export([{"name": "walk", "from": 0, "to": 2}])
    arrayed = {**hashed, "frames": [{"filename": k, **v} for k, v in hashed["frames"].items()]}

    assert read_aseprite_export(arrayed) == read_aseprite_export(hashed)


def test_an_export_reads_from_its_json_text() -> None:
    export = _export([{"name": "walk", "from": 0, "to": 2}])

    assert read_aseprite_export(json.dumps(export)) == read_aseprite_export(export)


def test_a_tags_direction_and_quoted_repeat_reach_the_clip() -> None:
    sheet = read_aseprite_export(_export([{"name": "wave", "from": 0, "to": 2, "direction": "pingpong", "repeat": "3"}]))

    [clip] = sheet.clips
    assert (clip.first, clip.last, clip.direction, clip.repeat) == (0, 2, "pingpong", 3)


# ── honoured ─────────────────────────────────────────────────────────────


def test_a_trimmed_frame_keeps_its_place_on_the_canvas() -> None:
    export = _export()
    export["frames"]["hero 1.aseprite"] = {
        "frame": {"x": 10, "y": 0, "w": 4, "h": 5},
        "rotated": False,
        "trimmed": True,
        "spriteSourceSize": {"x": 3, "y": 7, "w": 4, "h": 5},
        "sourceSize": {"w": 10, "h": 12},
        "duration": 100,
    }

    frame = read_aseprite_export(export).frames[1]

    assert (frame.rect.w, frame.rect.h, frame.offset.x, frame.offset.y) == (4, 5, 3, 7)


def test_each_frame_takes_the_pivot_of_the_slice_key_in_force() -> None:
    """A key holds from its frame until the next one; a frame before any key has none."""

    slices = [
        {"name": "hitbox", "keys": [_key(0, (1, 1))]},
        {"name": "pivot", "color": "#0000ffff", "keys": [_key(2, (6, 11)), _key(1, (5, 11))]},
    ]

    pivots = [f.pivot for f in read_aseprite_export(_export(slices=slices)).frames]

    assert [None if p is None else (p.x, p.y) for p in pivots] == [None, (5, 11), (6, 11)]


def test_a_pivot_is_measured_from_its_keys_bounds_not_the_canvas() -> None:
    slices = [{"name": "pivot", "keys": [_key(0, (2, 3), bounds=(4, 6, 5, 5))]}]

    pivot = read_aseprite_export(_export(slices=slices)).frames[0].pivot

    assert (pivot.x, pivot.y) == (6, 9)


def test_a_zero_sized_key_hides_the_pivot_from_its_frame_on() -> None:
    slices = [{"name": "pivot", "keys": [_key(0, (5, 11)), _key(2, (5, 11), bounds=(0, 0, 0, 0))]}]

    pivots = [f.pivot for f in read_aseprite_export(_export(slices=slices)).frames]

    assert [p is not None for p in pivots] == [True, True, False]


# ── refused ──────────────────────────────────────────────────────────────


def _trim_to_a_different_canvas(export: dict) -> None:
    export["frames"]["hero 2.aseprite"]["sourceSize"] = {"w": 11, "h": 12}


def test_a_frames_entry_that_is_not_a_record_is_a_value_error_like_the_rest() -> None:
    """``**record`` on a scalar would raise TypeError, which the loader does not catch."""

    export = _export()
    export["frames"]["hero 1.aseprite"] = None

    with pytest.raises(ValueError, match="is NoneType, not a frame record"):
        read_aseprite_export(export)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda e: e["frames"]["hero 0.aseprite"].update(rotated=True), "rotated"),
        (_trim_to_a_different_canvas, "canvases of different sizes"),
        (lambda e: e["frames"]["hero 1.aseprite"]["spriteSourceSize"].update(w=9), "padded or extruded"),
        (lambda e: e["meta"]["slices"].extend([{"name": "pivot", "keys": []}] * 2), "2 slices are named 'pivot'"),
        (lambda e: e["frames"]["hero 2.aseprite"]["frame"].update(x=25), "outside"),
        (lambda e: e["meta"]["frameTags"].append({"name": "run", "from": 1, "to": 3}), "reaches frame 3"),
        (lambda e: e["meta"]["frameTags"].append({"name": "walk", "from": 0, "to": 0}), "declared twice"),
        (lambda e: e["meta"]["frameTags"][0].update(repeat="twice"), "positive integer"),
        (lambda e: e["frames"]["hero 1.aseprite"].update(duration=0), "greater than 0"),
    ],
)
def test_what_cannot_be_honoured_is_refused(mutate, message: str) -> None:
    export = _export([{"name": "walk", "from": 0, "to": 2}])
    mutate(export)

    with pytest.raises(ValueError, match=message):
        read_aseprite_export(export)
