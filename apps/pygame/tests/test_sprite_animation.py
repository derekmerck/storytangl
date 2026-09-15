"""Playing sprite-sheet clips over a still, without moving the character.

The claims under test, in order of how badly they fail when wrong:

- frame 0 of a clip lands on exactly the still's pixels, flipped or not -- or
  every clip start would visibly jump the character;
- the frame shown, and whether the stage keeps ticking, are what the portable
  vectors say -- the same file the Python reference and any other client run;
- a trimmed frame, and a frame whose pivot moved, land where the manifest's
  placement puts them;
- frames are cut from the sheet before being mirrored, or a flipped sprite plays
  its clips backwards;
- a clip belongs to one staged occurrence, and ``media_timing`` is honoured as
  stated: restating carries on, switching or ``restart`` starts over, ``pause``
  and ``stop`` hold.

The sheet here is deliberately lopsided -- three columns of padding on one side,
one on the other, and a two-tone still -- because a symmetric test sheet would
pass a wrong mirror offset and a wrong crop order alike.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from PIL import Image  # noqa: E402

from tangl.presentation.sprite_sheet import SpriteSheetManifest  # noqa: E402
from tangl.pygame_client.models import SheetSource, StageImage, Turn  # noqa: E402
from tangl.pygame_client.stage import Stage  # noqa: E402

VECTORS = json.loads(
    (Path(__file__).parents[3] / "engine" / "contrib" / "conformance" / "sprite_sheets" / "playback.json").read_text()
)

STILL_W, STILL_H = 20, 112
PAD_L, PAD_R = 3, 1
CELL_W = PAD_L + STILL_W + PAD_R

LEFT, RIGHT = (200, 30, 30, 255), (90, 10, 10, 255)       # the still: two tones, so mirroring shows
BLINK_L, BLINK_R = (30, 30, 200, 255), (240, 240, 240, 255)
CALL_L, CALL_R = (30, 200, 30, 255), (10, 90, 10, 255)
HOLD_L, HOLD_R = (220, 220, 30, 255), (90, 90, 10, 255)


def _two_tone(image: Image.Image, x0: int, left, right) -> None:
    for x in range(STILL_W):
        for y in range(STILL_H):
            image.putpixel((x0 + x, y), left if x < STILL_W // 2 else right)


def _manifest(image: str, size: tuple[int, int], canvas: tuple[int, int], frames: list[dict], clips=()) -> SpriteSheetManifest:
    return SpriteSheetManifest.model_validate({
        "image": image, "size": {"w": size[0], "h": size[1]}, "canvas": {"w": canvas[0], "h": canvas[1]},
        "frames": frames, "clips": list(clips),
    })


@pytest.fixture
def art(tmp_path: Path):
    still = Image.new("RGBA", (STILL_W, STILL_H), (0, 0, 0, 0))
    _two_tone(still, 0, LEFT, RIGHT)
    still_path = tmp_path / "hero.png"
    still.save(still_path)

    sheet = Image.new("RGBA", (CELL_W * 4, STILL_H), (0, 0, 0, 0))
    for cell, (left, right) in enumerate([(LEFT, RIGHT), (BLINK_L, BLINK_R), (CALL_L, CALL_R), (HOLD_L, HOLD_R)]):
        _two_tone(sheet, cell * CELL_W + PAD_L, left, right)
    for x in range(PAD_L):                                  # the call reaches into the padding
        for y in range(STILL_H):
            sheet.putpixel((2 * CELL_W + x, y), CALL_L)
    sheet_path = tmp_path / "hero-4x1.png"
    sheet.save(sheet_path)

    pivot = {"x": PAD_L + STILL_W // 2, "y": STILL_H - 1}
    manifest = _manifest(
        "hero-4x1.png", (CELL_W * 4, STILL_H), (CELL_W, STILL_H),
        [{"rect": {"x": i * CELL_W, "y": 0, "w": CELL_W, "h": STILL_H}, "duration_ms": d, "pivot": pivot}
         for i, d in enumerate([1800, 200, 150, 150])],
        [{"name": "idle", "first": 0, "last": 1}, {"name": "call", "first": 2, "last": 3}],
    )
    return str(still_path), SheetSource(source=str(sheet_path), manifest=manifest)


class Clock:
    def __init__(self) -> None:
        self.ms = 0.0

    def __call__(self) -> float:
        return self.ms


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def stage(clock: Clock):
    made = Stage(clock=clock, title="sprite animation test")
    yield made
    pygame.quit()


def _image(still: str, sheet: SheetSource | None = None, **fields) -> StageImage:
    return StageImage(role="dialog_im", source=still, sheets=(sheet,) if sheet else (), **fields)


def _turn(still: str, sheet: SheetSource | None = None, **fields) -> Turn:
    return Turn(step=1, images=[_image(still, sheet, **fields)])


def _pixels(stage: Stage) -> bytes:
    return pygame.image.tobytes(stage.surface, "RGBA")


def _box(snapshot: bytes, stage: Stage, *, half: str | None = None) -> pygame.Rect:
    """Where a still was drawn, found by looking at a still-only draw, not by re-deriving layout."""

    surface = pygame.image.frombytes(snapshot, stage.surface.get_size(), "RGBA")
    background = surface.get_at((0, 0))
    width = surface.get_width()
    xs = range(width // 2) if half == "left" else range(width // 2, width) if half == "right" else range(width)
    points = [(x, y) for x in xs for y in range(0, surface.get_height(), 2) if surface.get_at((x, y)) != background]
    x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
    y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
    return pygame.Rect(x0, y0, x1 - x0 + 1, y1 - y0 + 1)


def _probe(stage: Stage, still_only: bytes, *, left: bool, half: str | None = None) -> tuple[int, int, int, int]:
    """Colour at the middle of the still's left or right half, located from a still-only draw."""

    box = _box(still_only, stage, half=half)
    x = box.x + box.w // 4 if left else box.right - 1 - box.w // 4
    return tuple(stage.surface.get_at((x, box.centery)))


# ── where frames land ────────────────────────────────────────────────────


@pytest.mark.parametrize("flip", [False, True], ids=["facing", "mirrored"])
def test_frame_zero_lands_on_exactly_the_stills_pixels(stage, art, flip) -> None:
    """Starting a clip must not move the character by a single pixel."""

    still, sheet = art
    stage.draw(_turn(still, flip_h=flip))
    still_only = _pixels(stage)

    stage.draw(_turn(still, sheet, flip_h=flip, clip="idle", timing="loop"))

    assert _pixels(stage) == still_only


@pytest.mark.parametrize("flip", [False, True], ids=["facing", "mirrored"])
def test_a_trimmed_frame_with_its_own_pivot_lands_where_the_manifest_places_it(stage, tmp_path, clock, flip) -> None:
    """Both halves of the placement law at once: the frame's offset, and a pivot that moved."""

    ink, patch = (200, 30, 30, 255), (30, 200, 200, 255)
    still_path = tmp_path / "hero.png"
    Image.new("RGBA", (24, STILL_H), ink).save(still_path)
    atlas = Image.new("RGBA", (32, STILL_H), (0, 0, 0, 0))
    atlas.paste(Image.new("RGBA", (24, STILL_H), ink), (0, 0))
    atlas.paste(Image.new("RGBA", (8, 50), patch), (24, 0))
    atlas_path = tmp_path / "hero-2x1.png"
    atlas.save(atlas_path)
    manifest = _manifest(
        "hero-2x1.png", (32, STILL_H), (24, STILL_H),
        [{"rect": {"x": 0, "y": 0, "w": 24, "h": STILL_H}, "duration_ms": 100, "pivot": {"x": 12, "y": 111}},
         {"rect": {"x": 24, "y": 0, "w": 8, "h": 50}, "offset": {"x": 3, "y": 40}, "duration_ms": 100,
          "pivot": {"x": 9, "y": 111}}],
    )
    sheet = SheetSource(source=str(atlas_path), manifest=manifest)
    stage.draw(_turn(str(still_path), flip_h=flip))
    box = _box(_pixels(stage), stage)

    turn = _turn(str(still_path), sheet, flip_h=flip, clip="pose")
    stage.draw(turn)
    clock.ms = 100
    stage.draw(turn)

    at = manifest.placement(1, (24, STILL_H), flip_h=flip)
    drawn = [(x, y) for x in range(stage.surface.get_width()) for y in range(stage.surface.get_height())
             if tuple(stage.surface.get_at((x, y))) == patch]
    assert (min(drawn), max(drawn)) == ((box.x + at.x, box.y + at.y), (box.x + at.x + 7, box.y + at.y + 49))


def test_no_clip_means_the_still_even_when_a_sheet_is_there(stage, art) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)

    stage.draw(_turn(still, sheet))

    assert _pixels(stage) == still_only
    assert stage.animating is False


# ── which frame, and for how long ────────────────────────────────────────


@pytest.fixture(scope="module")
def vector_art(tmp_path_factory) -> dict[str, tuple[str, SheetSource, dict[tuple, int]]]:
    """Each timing sheet from the vector file, with every frame a colour of its own."""

    root = tmp_path_factory.mktemp("vectors")
    made = {}
    for name in {case["sheet"] for case in VECTORS["timing"]}:
        manifest = SpriteSheetManifest.model_validate(VECTORS["sheets"][name])
        atlas = Image.new("RGBA", (manifest.size.w, manifest.size.h), (0, 0, 0, 0))
        colours = {}
        for index, frame in enumerate(manifest.frames):
            colour = (40 + 50 * index, 220 - 40 * index, 120, 255)
            colours[colour] = index
            atlas.paste(Image.new("RGBA", (frame.rect.w, frame.rect.h), colour), (frame.rect.x, frame.rect.y))
        atlas.save(root / manifest.image)
        still = root / f"{name}.png"
        Image.new("RGBA", (manifest.canvas.w, manifest.canvas.h), (250, 0, 250, 255)).save(still)
        made[name] = (str(still), SheetSource(source=str(root / manifest.image), manifest=manifest), colours)
    return made


@pytest.mark.parametrize(
    "case", VECTORS["timing"], ids=lambda c: f"{c['sheet']}-{c['clip']}-{'loop' if c['loop'] else 'play'}"
)
def test_the_stage_shows_the_frames_the_portable_vectors_name(stage, clock, vector_art, case) -> None:
    still, sheet, colours = vector_art[case["sheet"]]
    stage.draw(_turn(still))
    centre = _box(_pixels(stage), stage).center
    turn = _turn(still, sheet, clip=case["clip"], timing="loop" if case["loop"] else None)
    stage.draw(turn)                                    # the clip starts when first staged

    shown, ticking = [], []
    for elapsed, _frame in case["frames"]:
        clock.ms = elapsed
        stage.draw(turn)
        shown.append([elapsed, colours[tuple(stage.surface.get_at(centre))]])
        ticking.append(stage.animating)

    assert shown == case["frames"]
    settles = case["settles_at_ms"]
    assert ticking == [settles is None or elapsed < settles for elapsed, _ in case["frames"]]


def test_the_clock_picks_the_frame_the_manifest_names(stage, art, clock) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)
    turn = _turn(still, sheet, clip="idle", timing="loop")

    seen = []
    for ms in (0, 1799, 1800, 1999, 2000):
        clock.ms = ms
        stage.draw(turn)
        seen.append(_probe(stage, still_only, left=True))

    assert seen == [LEFT, LEFT, BLINK_L, BLINK_L, LEFT]
    assert stage.animating is True


def test_a_play_once_clip_holds_its_last_frame_and_stops_asking_for_ticks(stage, art, clock) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)
    turn = _turn(still, sheet, clip="call")

    stage.draw(turn)
    assert stage.animating is True

    clock.ms = 10_000
    stage.draw(turn)

    assert _probe(stage, still_only, left=True) == HOLD_L
    assert stage.animating is False


def test_frames_are_cut_from_the_sheet_before_they_are_mirrored(stage, art, clock) -> None:
    """Mirror the whole sheet first and cell 1 becomes the mirror of cell 2."""

    still, sheet = art
    stage.draw(_turn(still, flip_h=True))
    still_only = _pixels(stage)
    turn = _turn(still, sheet, flip_h=True, clip="idle", timing="loop")
    stage.draw(turn)                                    # the clip starts when first staged
    clock.ms = 1800                                     # ...so this is its second frame
    stage.draw(turn)

    assert _probe(stage, still_only, left=True) == BLINK_R
    assert _probe(stage, still_only, left=False) == BLINK_L


def test_reduced_motion_holds_the_clips_first_frame_not_the_still(art, clock) -> None:
    """Motion is optional; the pose is story state and still shows."""

    still, sheet = art
    calm = Stage(clock=clock, animate=False, title="reduced motion")
    calm.draw(_turn(still))
    still_only = _pixels(calm)
    turn = _turn(still, sheet, clip="call")

    calm.draw(turn)
    # Long past the point an animated stage would have reached the clip's final
    # frame -- which is why this is advanced after staging, not before: a clip
    # starts when first staged, so a clock set beforehand proves nothing.
    clock.ms = 5_000
    calm.draw(turn)

    assert _probe(calm, still_only, left=True) == CALL_L
    assert calm.animating is False
    pygame.quit()


# ── clip state ───────────────────────────────────────────────────────────


def test_restating_a_clip_carries_on_but_switching_restarts_it(stage, art, clock) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)

    stage.draw(_turn(still, sheet, clip="idle", timing="loop"))
    clock.ms = 1850
    stage.draw(_turn(still, sheet, clip="idle", timing="loop"))    # a new turn restating the same clip
    assert _probe(stage, still_only, left=True) == BLINK_L

    stage.draw(_turn(still, sheet, clip="call"))                   # switching starts the new clip at its top
    assert _probe(stage, still_only, left=True) == CALL_L


def test_the_same_sprite_staged_twice_keeps_two_clocks(stage, art, clock) -> None:
    """Default slots come from arrival order, so one role and source is not one identity."""

    still, sheet = art
    stage.draw(Turn(step=1, images=[_image(still), _image(still)]))
    still_only = _pixels(stage)
    turn = Turn(step=1, images=[_image(still, sheet, clip="idle", timing="loop"), _image(still, sheet, clip="call")])

    stage.draw(turn)
    clock.ms = 1850
    stage.draw(turn)

    assert _probe(stage, still_only, left=True, half="left") == BLINK_L
    assert _probe(stage, still_only, left=True, half="right") == HOLD_L


def test_restart_starts_over_on_each_new_turn_but_not_on_a_redraw(stage, art, clock) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)
    turn = _turn(still, sheet, clip="idle", timing="loop")
    stage.draw(turn)
    clock.ms = 1850

    redraw = _turn(still, sheet, clip="idle", timing="restart")
    stage.draw(redraw)
    assert _probe(stage, still_only, left=True) == LEFT            # a new turn said restart

    clock.ms = 1850 + 1800
    stage.draw(redraw)                                              # the same turn, drawn again: carries on
    assert _probe(stage, still_only, left=True) == BLINK_L


def test_pause_holds_the_frame_and_the_next_play_resumes_from_it(stage, art, clock) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)
    stage.draw(_turn(still, sheet, clip="idle", timing="loop"))
    clock.ms = 1850

    paused = _turn(still, sheet, clip="idle", timing="pause")
    stage.draw(paused)
    clock.ms = 5_000
    stage.draw(paused)
    assert _probe(stage, still_only, left=True) == BLINK_L
    assert stage.animating is False

    resumed = _turn(still, sheet, clip="idle", timing="loop")
    stage.draw(resumed)                                             # elapsed picks up at 1850
    assert _probe(stage, still_only, left=True) == BLINK_L
    clock.ms = 5_150                                                # 2000 into the loop: its top again
    stage.draw(resumed)
    assert _probe(stage, still_only, left=True) == LEFT


def test_stop_holds_the_first_frame_and_the_next_play_starts_there(stage, art, clock) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)
    stage.draw(_turn(still, sheet, clip="idle", timing="loop"))
    clock.ms = 1850

    stopped = _turn(still, sheet, clip="idle", timing="stop")
    stage.draw(stopped)
    assert _probe(stage, still_only, left=True) == LEFT
    assert stage.animating is False

    clock.ms = 3_000
    played = _turn(still, sheet, clip="idle", timing="loop")
    stage.draw(played)
    clock.ms = 4_800
    stage.draw(played)
    assert _probe(stage, still_only, left=True) == BLINK_L


def test_a_sprite_that_leaves_the_stage_starts_afresh_when_it_returns(stage, art, clock) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)

    stage.draw(_turn(still, sheet, clip="idle", timing="loop"))
    stage.draw(Turn(step=2))                                        # off stage
    clock.ms = 1850
    stage.draw(_turn(still, sheet, clip="idle", timing="loop"))    # back

    assert _probe(stage, still_only, left=True) == LEFT


# ── the still is the floor ───────────────────────────────────────────────


def test_a_clip_no_sheet_has_falls_back_to_the_still(stage, art) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)

    stage.draw(_turn(still, sheet, clip="response"))

    assert _pixels(stage) == still_only


def test_a_sheet_whose_image_disagrees_with_its_manifest_falls_back_to_the_still(stage, art, tmp_path) -> None:
    still, sheet = art
    Image.new("RGBA", (10, 10)).save(sheet.source)                 # the bytes no longer match the manifest
    stage.draw(_turn(still))
    still_only = _pixels(stage)

    stage.draw(_turn(still, sheet, clip="idle", timing="loop"))

    assert _pixels(stage) == still_only


# ── the wire ─────────────────────────────────────────────────────────────


def test_the_bridge_takes_clip_timing_and_sheets_from_the_payload(tmp_path: Path) -> None:
    from tangl.journal.fragments import MediaFragment
    from tangl.media.media_resource.resource_manager import ResourceManager
    from tangl.presentation.hints import StagingHints
    from tangl.pygame_client.bridge import PygameSessionBridge

    (tmp_path / "images").mkdir()
    Image.new("RGBA", (10, 12), (1, 1, 1, 255)).save(tmp_path / "images" / "hero.png")
    Image.new("RGBA", (20, 12), (2, 2, 2, 255)).save(tmp_path / "images" / "hero-idle-2x1-400ms.png")
    manager = ResourceManager(tmp_path)
    manager.index_directory("images")
    fragment = MediaFragment(
        content=manager.get_rit("hero.png"), content_format="rit", media_role="dialog_im",
        staging_hints=StagingHints(media_x="right", media_flip_h=True, media_clip="idle", media_timing="restart"),
    )

    [turn] = PygameSessionBridge().build_turns([fragment])
    [image] = turn.images

    assert (image.x_slot, image.flip_h, image.clip, image.timing) == ("right", True, "idle", "restart")
    assert [Path(s.source).name for s in image.sheets] == ["hero-idle-2x1-400ms.png"]
    assert image.sheets[0].manifest.clip_names() == ["idle"]


def test_a_timing_this_port_does_not_know_is_dropped_rather_than_guessed(caplog) -> None:
    from tangl.pygame_client.bridge import _timing

    assert [_timing(value) for value in (None, "loop", "restart", "pause", "stop", "start")] == [
        None, "loop", "restart", "pause", "stop", "start"
    ]
    assert _timing("sometimes") is None
    assert "sometimes" in caplog.text
