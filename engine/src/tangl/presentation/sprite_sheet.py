"""Sprite sheets: what a client needs to play a clip in place of a still.

A sprite sheet is an optional second representation of a staged image. The still
stays the floor every client can draw; a client that understands sheets may play a
named clip from the sheet instead. Which clip, and whether it loops, is per-use
staging (``StagingHints.media_clip`` and ``media_timing``). This module says only
what the sheet's pixels are and how a clip unfolds.

Normalized, not a tool's format
-------------------------------
Authors produce sheets with tools -- an Aseprite JSON export, or a filename
shorthand -- and :mod:`tangl.media.sprite_sheets` imports each into this one shape.
Nothing here knows a tool's aliases, a hash-versus-array layout, a repeat count
written as a string, or slices. Each frame carries its own resolved anchor, a
trimmed frame carries its own offset, and the canvas every frame is drawn on is
stated once. A client reads fields; it never re-derives an import.

Two laws, and a reference implementation of each
------------------------------------------------
The Python here is the reference, not code any other client shares. The portable
contract is these two laws and the vectors in
``engine/contrib/conformance/sprite_sheets/``, which a client in any language can
run against its own implementation.

**When** (:meth:`SpriteSheetManifest.frame_index_at`). A clip is a frame range
played in *passes*. A pass runs the range once in its direction; ``reverse`` and
``pingpong_reverse`` start at the far end. Forward and reverse passes each restart
from the top. Ping-pong passes alternate direction, and every pass after the first
starts one frame in from the end it turned at, so an end frame never shows twice
in a row. A clip played, not looped, makes ``repeat`` passes -- by default one,
or two for ping-pong (out and back) -- then holds its final frame. A looped clip
makes passes forever. A frame shows for ``[start, start + duration)``; elapsed
time at or below zero shows the first frame. A one-frame clip shows its frame
once per pass. These are Aseprite's own playback rules.

**Where** (:meth:`SpriteSheetManifest.placement`). A frame is drawn over the still
it replaces so that the frame's anchor lands on the still's anchor. The still's
anchor is its bottom-centre pixel, ``(w // 2, h - 1)``; a frame's is its declared
pivot, else the canvas's bottom-centre. Mirroring flips each image about its own
width -- the still, the canvas, and the anchors with them -- after the frame has
been cut from the sheet.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Direction = Literal["forward", "reverse", "pingpong", "pingpong_reverse"]


class _SheetModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class SheetPoint(_SheetModel):
    x: int
    y: int


class SheetSize(_SheetModel):
    w: int = Field(gt=0)
    h: int = Field(gt=0)


class SheetRect(_SheetModel):
    """A pixel rectangle."""

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(gt=0)
    h: int = Field(gt=0)


class SheetFrame(_SheetModel):
    """One frame: its pixels in the sheet, where they sit on the canvas, and for how long."""

    rect: SheetRect
    """Where the frame's pixels are in the sheet image."""

    offset: SheetPoint = SheetPoint(x=0, y=0)
    """Where ``rect``'s top-left sits on the canvas. Nonzero for a trimmed frame."""

    duration_ms: int = Field(gt=0)

    pivot: SheetPoint | None = None
    """This frame's anchor on the canvas, when the sheet declares one."""


class SheetClip(_SheetModel):
    """A named clip: an inclusive frame range, a direction, and a pass count."""

    name: str
    first: int = Field(ge=0)
    last: int = Field(ge=0)
    direction: Direction = "forward"
    repeat: int | None = Field(default=None, gt=0)
    """Passes when played rather than looped. ``None``: one, or two for ping-pong."""

    @model_validator(mode="after")
    def _ordered(self) -> "SheetClip":
        if self.last < self.first:
            raise ValueError(f"clip {self.name!r} ends before it starts ({self.first}..{self.last})")
        return self

    @property
    def passes(self) -> int:
        return self.repeat or (2 if self.direction.startswith("pingpong") else 1)


class SpriteSheetManifest(_SheetModel):
    """One sheet image: its frames, the canvas they share, and its clips.

    A sheet with no clips has one implicit clip over every frame, which answers to
    any name. That is why indexing lets such a sheet be the only one for its still.
    """

    image: str
    """The sheet image's filename."""

    size: SheetSize
    """The sheet image's pixel size."""

    canvas: SheetSize
    """The size every frame is drawn on: the sprite's own size, before trimming."""

    frames: list[SheetFrame]
    clips: list[SheetClip] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> "SpriteSheetManifest":
        if not self.frames:
            raise ValueError("a sprite sheet needs at least one frame")
        for index, frame in enumerate(self.frames):
            r, o = frame.rect, frame.offset
            if r.x + r.w > self.size.w or r.y + r.h > self.size.h:
                raise ValueError(
                    f"frame {index} rect ({r.x},{r.y},{r.w},{r.h}) lies outside the "
                    f"{self.size.w}x{self.size.h} sheet"
                )
            if o.x < 0 or o.y < 0 or o.x + r.w > self.canvas.w or o.y + r.h > self.canvas.h:
                raise ValueError(
                    f"frame {index} placed at ({o.x},{o.y}) does not fit the "
                    f"{self.canvas.w}x{self.canvas.h} canvas"
                )
        names: set[str] = set()
        for clip in self.clips:
            if clip.last >= len(self.frames):
                raise ValueError(
                    f"clip {clip.name!r} reaches frame {clip.last}, but the sheet has {len(self.frames)} frames"
                )
            if clip.name in names:
                raise ValueError(f"clip {clip.name!r} is declared twice")
            names.add(clip.name)
        return self

    # ── clips ────────────────────────────────────────────────────────────

    def clip_names(self) -> list[str]:
        return [clip.name for clip in self.clips]

    def has_clip(self, name: str) -> bool:
        return not self.clips or name in self.clip_names()

    def clip(self, name: str) -> SheetClip:
        """The clip called ``name``; on a sheet with no clips, the implicit one."""

        if not self.clips:
            return SheetClip(name=name, first=0, last=len(self.frames) - 1)
        for clip in self.clips:
            if clip.name == name:
                return clip
        raise KeyError(f"no clip named {name!r}; this sheet has {self.clip_names()}")

    # ── when ─────────────────────────────────────────────────────────────

    def play_order(self, name: str, *, loop: bool = False) -> list[int]:
        """Frame indices in the order they show: one period when looping, else the whole play."""

        clip = self.clip(name)
        span = list(range(clip.first, clip.last + 1))
        if clip.direction in ("reverse", "pingpong_reverse"):
            span.reverse()
        pingpong = clip.direction.startswith("pingpong")
        if len(span) == 1:
            return span if loop else span * clip.passes
        if loop:
            return span + span[-2:0:-1] if pingpong else span
        order = list(span)
        for n in range(1, clip.passes):
            if pingpong:
                order += (span if n % 2 == 0 else span[::-1])[1:]
            else:
                order += span
        return order

    def frame_index_at(self, name: str, elapsed_ms: float, *, loop: bool = False) -> int:
        """Which frame of the sheet shows ``elapsed_ms`` into clip ``name``."""

        order = self.play_order(name, loop=loop)
        durations = [self.frames[i].duration_ms for i in order]
        total = sum(durations)
        if elapsed_ms <= 0:
            return order[0]
        if loop:
            t = elapsed_ms % total
        elif elapsed_ms >= total:
            return order[-1]
        else:
            t = elapsed_ms
        for index, duration in zip(order, durations):
            if t < duration:
                return index
            t -= duration
        return order[-1]

    def settles_at_ms(self, name: str, *, loop: bool = False) -> int | None:
        """From when the frame shown stops changing, or ``None`` if it never does.

        A client asks this to know when it can stop redrawing, so that answer comes
        from the same order the frames are chosen from.
        """

        order = self.play_order(name, loop=loop)
        if loop:
            return 0 if len(set(order)) == 1 else None
        start = len(order) - 1
        while start > 0 and order[start - 1] == order[-1]:
            start -= 1
        return sum(self.frames[i].duration_ms for i in order[:start])

    # ── where ────────────────────────────────────────────────────────────

    def anchor(self, index: int) -> SheetPoint:
        """Frame ``index``'s anchor on the canvas: its pivot, else the canvas's bottom-centre."""

        pivot = self.frames[index].pivot
        return pivot if pivot is not None else SheetPoint(x=self.canvas.w // 2, y=self.canvas.h - 1)

    def placement(self, index: int, still_size: tuple[int, int], *, flip_h: bool = False) -> SheetPoint:
        """Where frame ``index``'s pixels go, relative to the still's top-left, in sheet pixels.

        Drawn there, the frame's anchor covers the still's anchor, so starting,
        stopping or switching a clip never moves the character.
        """

        frame = self.frames[index]
        anchor = self.anchor(index)
        still_w, still_h = still_size
        still_x, anchor_x, offset_x = still_w // 2, anchor.x, frame.offset.x
        if flip_h:
            still_x = still_w - 1 - still_x
            anchor_x = self.canvas.w - 1 - anchor_x
            offset_x = self.canvas.w - offset_x - frame.rect.w
        return SheetPoint(
            x=still_x - anchor_x + offset_x,
            y=(still_h - 1) - anchor.y + frame.offset.y,
        )


__all__ = [
    "Direction",
    "SheetClip",
    "SheetFrame",
    "SheetPoint",
    "SheetRect",
    "SheetSize",
    "SpriteSheetManifest",
]
