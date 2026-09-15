"""The client-facing sprite-sheet manifest: its shape, and the two laws it carries.

The claims under test are that a manifest a client cannot draw is refused, and that
the Python reference agrees with the language-neutral vectors every client runs --
when a frame shows, when a clip settles, and where a frame lands over its still.
Importing tool formats is media's business and is tested there.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tangl.presentation.hints import StagingHints
from tangl.presentation.sprite_sheet import SpriteSheetManifest

VECTORS = json.loads(
    (Path(__file__).parents[2] / "contrib" / "conformance" / "sprite_sheets" / "playback.json").read_text()
)
SHEETS = {name: SpriteSheetManifest.model_validate(sheet) for name, sheet in VECTORS["sheets"].items()}


def _sheet(**changes) -> dict:
    sheet = {
        "image": "hero-3x1.png",
        "size": {"w": 30, "h": 12},
        "canvas": {"w": 10, "h": 12},
        "frames": [{"rect": {"x": 10 * i, "y": 0, "w": 10, "h": 12}, "duration_ms": 100} for i in range(3)],
        "clips": [{"name": "walk", "first": 0, "last": 2}],
    }
    sheet.update(changes)
    return sheet


# ── the shape ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda s: s["frames"][2]["rect"].update(x=25), "outside the 30x12 sheet"),
        (lambda s: s["frames"][1].update(offset={"x": 1, "y": 0}), "does not fit the 10x12 canvas"),
        (lambda s: s["frames"][1].update(duration_ms=0), "greater than 0"),
        (lambda s: s["clips"].append({"name": "run", "first": 1, "last": 3}), "reaches frame 3"),
        (lambda s: s["clips"].append({"name": "walk", "first": 0, "last": 0}), "declared twice"),
        (lambda s: s["clips"][0].update(first=2, last=1), "ends before it starts"),
        (lambda s: s["clips"][0].update(repeat=0), "greater than 0"),
        (lambda s: s.update(frames=[]), "at least one frame"),
        (lambda s: s["clips"][0].update(frameTags=[]), "Extra inputs"),
    ],
)
def test_a_manifest_a_client_could_not_draw_is_refused(mutate, message: str) -> None:
    sheet = _sheet()
    mutate(sheet)

    with pytest.raises(ValidationError, match=message):
        SpriteSheetManifest.model_validate(sheet)


def test_the_manifest_survives_the_wire_as_json() -> None:
    sheet = SHEETS["trimmed"]

    assert SpriteSheetManifest.model_validate_json(json.dumps(sheet.model_dump())) == sheet


def test_a_sheet_without_clips_has_one_that_answers_to_any_name() -> None:
    untagged, tagged = SHEETS["untagged"], SHEETS["blink"]

    assert untagged.has_clip("anything") and untagged.clip("anything").last == 1
    assert tagged.has_clip("idle") and not tagged.has_clip("call")
    with pytest.raises(KeyError, match="no clip named 'call'"):
        tagged.clip("call")


# ── the laws, against the portable vectors ───────────────────────────────


def _timing_id(case: dict) -> str:
    return f"{case['sheet']}-{case['clip']}-{'loop' if case['loop'] else 'play'}"


@pytest.mark.parametrize("case", VECTORS["timing"], ids=_timing_id)
def test_the_reference_shows_the_frames_the_vectors_name(case: dict) -> None:
    sheet = SHEETS[case["sheet"]]

    shown = [[t, sheet.frame_index_at(case["clip"], t, loop=case["loop"])] for t, _ in case["frames"]]

    assert shown == case["frames"]


@pytest.mark.parametrize("case", VECTORS["timing"], ids=_timing_id)
def test_the_reference_settles_when_the_vectors_say(case: dict) -> None:
    sheet = SHEETS[case["sheet"]]
    settles = sheet.settles_at_ms(case["clip"], loop=case["loop"])

    assert settles == case["settles_at_ms"]
    if settles is not None:
        # Settled means settled: the frame at that moment is the frame forever after.
        final = sheet.frame_index_at(case["clip"], settles, loop=case["loop"])
        assert {sheet.frame_index_at(case["clip"], settles + t, loop=case["loop"]) for t in range(0, 2000, 7)} == {final}


@pytest.mark.parametrize(
    "case", VECTORS["placement"], ids=lambda c: f"{c['sheet']}-{c['frame']}-{'mirrored' if c['flip_h'] else 'facing'}"
)
def test_the_reference_places_frames_where_the_vectors_say(case: dict) -> None:
    at = SHEETS[case["sheet"]].placement(case["frame"], tuple(case["still"]), flip_h=case["flip_h"])

    assert [at.x, at.y] == case["at"]


def test_the_vectors_cover_every_direction_both_modes_and_trimming() -> None:
    """A vector file that quietly lost a family would still pass everything above."""

    directions = {
        clip.direction
        for case in VECTORS["timing"]
        for clip in [SHEETS[case["sheet"]].clip(case["clip"])]
    }
    assert directions == {"forward", "reverse", "pingpong", "pingpong_reverse"}
    assert {case["loop"] for case in VECTORS["timing"]} == {True, False}
    assert any(frame.offset.x or frame.offset.y for frame in SHEETS["trimmed"].frames)
    assert {case["flip_h"] for case in VECTORS["placement"]} == {True, False}


def test_ping_pong_repeat_counts_directions_not_round_trips() -> None:
    """Aseprite's rule, which is easy to get wrong: repeat 1 is one way, 2 is out and back."""

    strip = SHEETS["strip"]

    assert strip.play_order("glance") == [2, 1, 0]
    assert strip.play_order("bounce") == [0, 1, 2, 1, 0]
    assert strip.play_order("wave") == [0, 1, 2, 1, 0, 1, 2]


# ── the per-use hint ─────────────────────────────────────────────────────


def test_the_clip_is_selected_per_use_beside_its_timing() -> None:
    hints = StagingHints(media_x="right", media_clip="call", media_timing="loop")

    assert hints.model_dump(exclude_none=True) == {"media_x": "right", "media_timing": "loop", "media_clip": "call"}
