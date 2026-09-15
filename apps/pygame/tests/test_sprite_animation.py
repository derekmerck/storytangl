"""Playing sprite-sheet clips over a still, without moving the character.

The claims under test, in order of how badly they fail when wrong:

- frame 0 of a clip lands on exactly the still's pixels, flipped or not -- or
  every clip start would visibly jump the character;
- the frame shown is the one the manifest's own timing names for the clock;
- frames are cut from the sheet before being mirrored, or a flipped sprite plays
  its clips backwards;
- a clip is per staged identity: switching clips restarts, restating does not.

The sheet here is deliberately lopsided -- three columns of padding on one side,
one on the other, and a two-tone still -- because a symmetric test sheet would
pass a wrong mirror offset and a wrong crop order alike.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from PIL import Image  # noqa: E402

from tangl.presentation.sprite_sheet import SpriteSheetManifest  # noqa: E402
from tangl.pygame_client.models import SheetSource, StageImage, Turn  # noqa: E402
from tangl.pygame_client.stage import Stage  # noqa: E402

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

    manifest = SpriteSheetManifest.model_validate({
        "frames": [{"frame": {"x": i * CELL_W, "y": 0, "w": CELL_W, "h": STILL_H}, "duration": d}
                   for i, d in enumerate([1800, 200, 150, 150])],
        "meta": {
            "image": "hero-4x1.png", "size": {"w": CELL_W * 4, "h": STILL_H},
            "frameTags": [{"name": "idle", "from": 0, "to": 1}, {"name": "call", "from": 2, "to": 3}],
            "slices": [{"name": "pivot", "keys": [{"frame": 0, "bounds": {"x": 0, "y": 0, "w": CELL_W, "h": STILL_H},
                                                   "pivot": {"x": PAD_L + STILL_W // 2, "y": STILL_H - 1}}]}],
        },
    })
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


def _turn(still: str, sheet: SheetSource | None = None, **fields) -> Turn:
    image = StageImage(role="dialog_im", source=still, sheets=(sheet,) if sheet else (), **fields)
    return Turn(step=1, images=[image])


def _pixels(stage: Stage) -> bytes:
    return pygame.image.tobytes(stage.surface, "RGBA")


def _box(stage: Stage) -> pygame.Rect:
    """Where the still is drawn: found by looking, not by re-deriving the layout."""

    rect = stage.surface.get_bounding_rect()
    return rect


def _probe(stage: Stage, still_only: bytes, *, left: bool) -> tuple[int, int, int, int]:
    """Colour at the middle of the still's left or right half, located from a still-only draw."""

    probe_surface = pygame.image.frombytes(still_only, stage.surface.get_size(), "RGBA")
    background = probe_surface.get_at((0, 0))
    xs = [x for x in range(probe_surface.get_width()) if probe_surface.get_at((x, 150)) != background]
    x0, x1 = min(xs), max(xs)
    x = x0 + (x1 - x0) // 4 if left else x1 - (x1 - x0) // 4
    return tuple(stage.surface.get_at((x, 150)))


# ── where frames land ────────────────────────────────────────────────────


@pytest.mark.parametrize("flip", [False, True], ids=["facing", "mirrored"])
def test_frame_zero_lands_on_exactly_the_stills_pixels(stage, art, flip) -> None:
    """Starting a clip must not move the character by a single pixel."""

    still, sheet = art
    stage.draw(_turn(still, flip_h=flip))
    still_only = _pixels(stage)

    stage.draw(_turn(still, sheet, flip_h=flip, clip="idle", loop=True))

    assert _pixels(stage) == still_only


def test_no_clip_means_the_still_even_when_a_sheet_is_there(stage, art) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)

    stage.draw(_turn(still, sheet))

    assert _pixels(stage) == still_only
    assert stage.animating is False


# ── which frame ──────────────────────────────────────────────────────────


def test_the_clock_picks_the_frame_the_manifest_names(stage, art, clock) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)
    turn = _turn(still, sheet, clip="idle", loop=True)

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
    turn = _turn(still, sheet, flip_h=True, clip="idle", loop=True)
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

    stage.draw(_turn(still, sheet, clip="idle", loop=True))
    clock.ms = 1850
    stage.draw(_turn(still, sheet, clip="idle", loop=True))       # a new turn restating the same clip
    assert _probe(stage, still_only, left=True) == BLINK_L

    stage.draw(_turn(still, sheet, clip="call"))                  # switching starts the new clip at its top
    assert _probe(stage, still_only, left=True) == CALL_L


def test_a_sprite_that_leaves_the_stage_starts_afresh_when_it_returns(stage, art, clock) -> None:
    still, sheet = art
    stage.draw(_turn(still))
    still_only = _pixels(stage)

    stage.draw(_turn(still, sheet, clip="idle", loop=True))
    stage.draw(Turn(step=2))                                      # off stage
    clock.ms = 1850
    stage.draw(_turn(still, sheet, clip="idle", loop=True))       # back

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

    stage.draw(_turn(still, sheet, clip="idle", loop=True))

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
        staging_hints=StagingHints(media_x="right", media_flip_h=True, media_clip="idle", media_timing="loop"),
    )

    [turn] = PygameSessionBridge().build_turns([fragment])
    [image] = turn.images

    assert (image.x_slot, image.flip_h, image.clip, image.loop) == ("right", True, "idle", True)
    assert [Path(s.source).name for s in image.sheets] == ["hero-idle-2x1-400ms.png"]
    assert image.sheets[0].manifest.clip_names() == ["idle"]
