"""Sprite sheets: frames, clips and timing for an animated alternative to a still.

A sprite sheet is an optional second representation of a staged image. The still
stays the floor every client can draw; a client that understands sheets may play
named clips from the sheet instead. Nothing here decides *which* clip plays or
*whether* it loops -- that is per-use staging (``StagingHints.media_clip`` and
``media_timing``). This module describes only what the bytes are.

The format is Aseprite's
------------------------
Sprite sheets are a mature, non-core problem with a format artists already export,
so the manifest is a typed **subset of Aseprite's JSON sprite-sheet export** rather
than anything bespoke: TexturePacker-style frame records plus ``meta.frameTags``.
Field names and shapes follow Aseprite's own exporter (``doc_exporter.cpp``),
including two details that are easy to get wrong:

- a tag's ``repeat`` is written as a *quoted string*, and only when it is finite;
- there is no way to write "loop forever". Absent ``repeat`` means play once (the
  export semantics), and looping is therefore a per-use hint, never a sheet fact.

Accepted: frame rects and durations, trimming (``spriteSourceSize`` within
``sourceSize``), tags with ``direction`` and ``repeat``, and slice pivots. Rotated
frames are refused, since Aseprite never writes them. Layers, colours, user data
and app metadata are ignored.

Shorthands compile to the same manifest
---------------------------------------
Two lighter ways to describe a sheet exist, and both expand into
:class:`SpriteSheetManifest` so there is one validated shape and one reader:

- a **filename** such as ``master_sprite-idle-4x1-1600ms`` (see :class:`SheetName`);
- a **compact form** (:class:`CompactSheet`) whose per-cell fields each take one
  value or one value per cell -- a single value repeats, like array broadcasting.

The filename and compact forms carry uniform or simple timing. Anything more
particular is an Aseprite export.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

Direction = Literal["forward", "reverse", "pingpong", "pingpong_reverse"]

DEFAULT_FRAME_MS = 100
"""Aseprite's default frame duration, used when a shorthand states no timing."""

PIVOT_SLICE = "pivot"
"""Name of the slice whose key pivot anchors the sheet.

Aseprite carries pivots on slices rather than on frames or the sheet. Reading the
slice with this name is the one convention layered on top of the format.
"""


class _SheetModel(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class SheetRect(_SheetModel):
    """A pixel rectangle in sheet coordinates."""

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(gt=0)
    h: int = Field(gt=0)


class SheetSize(_SheetModel):
    w: int = Field(gt=0)
    h: int = Field(gt=0)


class SheetPoint(_SheetModel):
    x: int
    y: int


class SheetFrame(_SheetModel):
    """One frame: where its pixels are, and how long it shows."""

    filename: str | None = None
    frame: SheetRect
    rotated: bool = False
    trimmed: bool = False
    sprite_source_size: SheetRect | None = Field(default=None, alias="spriteSourceSize")
    source_size: SheetSize | None = Field(default=None, alias="sourceSize")
    duration: int = Field(gt=0)

    @field_validator("rotated")
    @classmethod
    def _refuse_rotation(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "rotated frames are not supported: Aseprite never writes them, and a "
                "packer that rotates would need every client to un-rotate"
            )
        return value


class FrameTag(_SheetModel):
    """A named clip: an inclusive frame range, a play direction, and a repeat count."""

    name: str
    from_frame: int = Field(alias="from", ge=0)
    to_frame: int = Field(alias="to", ge=0)
    direction: Direction = "forward"
    repeat: int | None = Field(default=None, gt=0)
    """How many times the clip plays. ``None`` means once.

    Aseprite writes this as a quoted string and omits it when unset; it is read
    from either form and written back as a string so an export round-trips.
    """

    @field_validator("repeat", mode="before")
    @classmethod
    def _repeat_from_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            if not value.isdigit():
                raise ValueError(f"repeat must be a positive integer, got {value!r}")
            return int(value)
        return value

    @field_serializer("repeat")
    def _repeat_as_string(self, value: int | None) -> str | None:
        return None if value is None else str(value)

    @model_validator(mode="after")
    def _ordered(self) -> "FrameTag":
        if self.to_frame < self.from_frame:
            raise ValueError(f"tag {self.name!r} ends before it starts ({self.from_frame}..{self.to_frame})")
        return self


class SliceKey(_SheetModel):
    frame: int = Field(ge=0)
    bounds: SheetRect
    pivot: SheetPoint | None = None
    center: SheetRect | None = None


class SheetSlice(_SheetModel):
    name: str
    keys: list[SliceKey] = Field(default_factory=list)


class SheetMeta(_SheetModel):
    image: str
    size: SheetSize
    frame_tags: list[FrameTag] = Field(default_factory=list, alias="frameTags")
    slices: list[SheetSlice] = Field(default_factory=list)


class SpriteSheetManifest(_SheetModel):
    """A typed subset of Aseprite's JSON sprite-sheet export.

    Accepts both of Aseprite's layouts: the default hash, keyed by frame filename in
    timeline order, and the array. Either way ``frames`` is held in timeline order,
    which is the order tag ranges index.
    """

    frames: list[SheetFrame]
    meta: SheetMeta

    @field_validator("frames", mode="before")
    @classmethod
    def _frames_from_hash(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return [{"filename": name, **record} for name, record in value.items()]
        return value

    @model_validator(mode="after")
    def _consistent(self) -> "SpriteSheetManifest":
        if not self.frames:
            raise ValueError("a sprite sheet needs at least one frame")
        size = self.meta.size
        for index, frame in enumerate(self.frames):
            r = frame.frame
            if r.x + r.w > size.w or r.y + r.h > size.h:
                raise ValueError(
                    f"frame {index} rect ({r.x},{r.y},{r.w},{r.h}) lies outside the "
                    f"{size.w}x{size.h} sheet"
                )
        names: set[str] = set()
        for tag in self.meta.frame_tags:
            if tag.to_frame >= len(self.frames):
                raise ValueError(
                    f"tag {tag.name!r} reaches frame {tag.to_frame}, but the sheet has "
                    f"{len(self.frames)} frames"
                )
            if tag.name in names:
                raise ValueError(f"tag {tag.name!r} is declared twice")
            names.add(tag.name)
        return self

    # ── clips ────────────────────────────────────────────────────────────

    def clip_names(self) -> list[str]:
        return [tag.name for tag in self.meta.frame_tags]

    def tag(self, clip: str | None) -> FrameTag:
        """The tag for ``clip``; with no tags at all, one implicit clip over every frame.

        Asking an untagged sheet for a named clip is not an error here: it has exactly
        one clip, and refusing a name nobody could have satisfied would only push a
        guess onto every client. Asking a *tagged* sheet for a clip it lacks is.
        """

        if not self.meta.frame_tags:
            return FrameTag(name=clip or "", from_frame=0, to_frame=len(self.frames) - 1)
        if clip is None:
            return self.meta.frame_tags[0]
        for tag in self.meta.frame_tags:
            if tag.name == clip:
                return tag
        raise KeyError(f"no clip named {clip!r}; this sheet has {self.clip_names()}")

    def sequence(self, clip: str | None) -> list[int]:
        """Frame indices for one pass of a clip, honouring its direction.

        A ping-pong pass runs out and back without repeating either end, so
        ``0 1 2`` plays as ``0 1 2 1`` and the next pass starts cleanly on ``0``.
        """

        tag = self.tag(clip)
        forward = list(range(tag.from_frame, tag.to_frame + 1))
        if len(forward) == 1:
            return forward
        if tag.direction == "forward":
            return forward
        if tag.direction == "reverse":
            return forward[::-1]
        if tag.direction == "pingpong":
            return forward + forward[-2:0:-1]
        return forward[::-1] + forward[1:-1]

    def frame_index_at(self, clip: str | None, elapsed_ms: float, *, loop: bool = False) -> int:
        """Which frame of the sheet shows ``elapsed_ms`` into ``clip``.

        The one timing function: clients call it with their clock, tests call it
        with a number. A frame covers ``[start, start + duration)``. The clip plays
        its tag's ``repeat`` count -- once when unset -- and then holds its final
        frame, unless the use asks it to loop, which only staging can.
        """

        order = self.sequence(clip)
        durations = [self.frames[i].duration for i in order]
        cycle = sum(durations)
        if elapsed_ms <= 0:
            return order[0]
        if not loop:
            passes = self.tag(clip).repeat or 1
            if elapsed_ms >= cycle * passes:
                return order[-1]
        t = elapsed_ms % cycle
        for index, duration in zip(order, durations):
            if t < duration:
                return index
            t -= duration
        return order[-1]

    def pivot(self) -> SheetPoint | None:
        """The anchor point shared by every frame, if the sheet declares one."""

        for sl in self.meta.slices:
            if sl.name == PIVOT_SLICE and sl.keys and sl.keys[0].pivot is not None:
                return sl.keys[0].pivot
        return None

    def check_grid(self, cols: int, rows: int) -> None:
        """Refuse a manifest that disagrees with a grid stated elsewhere, e.g. a filename.

        When a sidecar and a filename both describe a sheet, the sidecar is
        authoritative -- but the two must still agree, or the same fact is declared
        twice and can silently differ.
        """

        if len(self.frames) != cols * rows:
            raise ValueError(f"sheet declares {len(self.frames)} frames but its name says {cols}x{rows}")
        if self.meta.size.w % cols or self.meta.size.h % rows:
            raise ValueError(
                f"a {self.meta.size.w}x{self.meta.size.h} sheet does not divide into {cols}x{rows} cells"
            )
        # Count and divisibility alone cannot tell 4x1 from 2x2: both have four cells,
        # and a 40x12 sheet divides either way. Only the rects say which it is.
        cw, ch = self.meta.size.w // cols, self.meta.size.h // rows
        for index, frame in enumerate(self.frames):
            cell = SheetRect(x=(index % cols) * cw, y=(index // cols) * ch, w=cw, h=ch)
            if frame.frame != cell:
                raise ValueError(
                    f"frame {index} sits at {frame.frame.model_dump()}, not in the {cols}x{rows} "
                    f"cell its name says {cell.model_dump()}"
                )


# ── authoring shorthands ─────────────────────────────────────────────────────


def _distribute(total: int, weights: list[float]) -> list[int]:
    """Integer milliseconds proportional to ``weights`` that sum to exactly ``total``."""

    if total < len(weights):
        raise ValueError(f"{total} ms cannot give each of {len(weights)} frames a positive duration")
    scale = sum(weights)
    raw = [total * w / scale for w in weights]
    whole = [max(1, int(value)) for value in raw]
    shortfall = total - sum(whole)
    by_remainder = sorted(range(len(raw)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    for i in by_remainder[: max(shortfall, 0)]:
        whole[i] += 1
    return whole


def _broadcast(value: Any, cells: int, field: str) -> list[Any]:
    if isinstance(value, list):
        if len(value) != cells:
            raise ValueError(f"{field} gives {len(value)} values for {cells} cells")
        return list(value)
    return [value] * cells


class CompactSheet(_SheetModel):
    """A sheet described by grid and per-cell values instead of per-frame records.

    Every per-cell field takes **one value or one value per cell**: a single value
    repeats across every cell. ``total`` is sheet-level and never broadcasts; when
    present, ``duration`` values are weights scaled to fill it.
    """

    sheet: str
    """Grid as ``<columns>x<rows>``, read row-major."""

    role: str | list[str] | None = None
    """Clip name per cell. Consecutive cells with one role become one tag."""

    duration: float | list[float] | None = None
    """Milliseconds per cell, or weights when ``total`` is set."""

    total: int | None = Field(default=None, gt=0)

    @field_validator("sheet")
    @classmethod
    def _grid(cls, value: str) -> str:
        if not re.fullmatch(r"[1-9]\d*x[1-9]\d*", value):
            raise ValueError(f"sheet must be <columns>x<rows> with at least one of each, got {value!r}")
        return value

    @property
    def grid(self) -> tuple[int, int]:
        cols, rows = (int(part) for part in self.sheet.split("x"))
        return cols, rows

    def durations(self) -> list[int]:
        cols, rows = self.grid
        cells = cols * rows
        if self.total is not None:
            weights = _broadcast(1.0 if self.duration is None else self.duration, cells, "duration")
            if any(w <= 0 for w in weights):
                raise ValueError("duration weights must be positive")
            return _distribute(self.total, [float(w) for w in weights])
        values = _broadcast(DEFAULT_FRAME_MS if self.duration is None else self.duration, cells, "duration")
        if any(v <= 0 for v in values):
            raise ValueError("durations must be positive")
        return [max(1, round(v)) for v in values]

    def tags(self) -> list[FrameTag]:
        if self.role is None:
            return []
        cols, rows = self.grid
        roles = _broadcast(self.role, cols * rows, "role")
        tags: list[FrameTag] = []
        start = 0
        for index in range(1, len(roles) + 1):
            if index == len(roles) or roles[index] != roles[start]:
                if any(tag.name == roles[start] for tag in tags):
                    raise ValueError(
                        f"role {roles[start]!r} appears in two separate runs; a clip is a "
                        "contiguous range and cannot be split"
                    )
                tags.append(FrameTag(name=roles[start], from_frame=start, to_frame=index - 1))
                start = index
        return tags

    def to_manifest(self, image: str, size: tuple[int, int]) -> SpriteSheetManifest:
        """Expand into the canonical manifest for an image of ``size`` pixels."""

        cols, rows = self.grid
        width, height = size
        if width % cols or height % rows:
            raise ValueError(f"a {width}x{height} image does not divide into {cols}x{rows} cells")
        cw, ch = width // cols, height // rows
        frames = [
            SheetFrame(
                filename=f"{image} {index}",
                frame=SheetRect(x=(index % cols) * cw, y=(index // cols) * ch, w=cw, h=ch),
                duration=duration,
            )
            for index, duration in enumerate(self.durations())
        ]
        return SpriteSheetManifest(
            frames=frames,
            meta=SheetMeta(image=image, size=SheetSize(w=width, h=height), frame_tags=self.tags()),
        )


_SHEET_NAME = re.compile(
    r"^(?P<root>[A-Za-z0-9_]+)"
    r"(?:-(?P<clip>[a-z][a-z0-9_]*))?"
    r"-(?P<cols>[1-9]\d*)x(?P<rows>[1-9]\d*)"
    r"(?:-(?P<amount>[1-9]\d*)(?P<unit>ms|s))?$"
)


class SheetName(_SheetModel):
    """What a sheet's filename says about it.

    ``<root>[-<clip>]-<columns>x<rows>[-<total>(ms|s)]``. Underscore binds the root
    and hyphen separates segments, so ``master_sprite-idle-4x1-1600ms`` is a
    four-cell ``idle`` clip for the still named ``master_sprite``, lasting 1600 ms.
    Without a clip segment the sheet's clips come from its sidecar export.

    The grid segment contains an ``x``, which keeps it disjoint from #418's loose
    frame suffix (``-01``), so both conventions can live in one pack.
    """

    root: str
    clip: str | None = None
    cols: int
    rows: int
    total_ms: int | None = None

    @classmethod
    def parse(cls, stem: str) -> "SheetName | None":
        match = _SHEET_NAME.match(stem)
        if match is None:
            return None
        amount, unit = match["amount"], match["unit"]
        total = None if amount is None else int(amount) * (1000 if unit == "s" else 1)
        return cls(root=match["root"], clip=match["clip"], cols=int(match["cols"]),
                   rows=int(match["rows"]), total_ms=total)

    def compact(self) -> CompactSheet:
        """The compact form this name is shorthand for."""

        return CompactSheet(sheet=f"{self.cols}x{self.rows}", role=self.clip, total=self.total_ms)


__all__ = [
    "DEFAULT_FRAME_MS",
    "CompactSheet",
    "FrameTag",
    "SheetFrame",
    "SheetMeta",
    "SheetName",
    "SheetRect",
    "SheetSize",
    "SliceKey",
    "SpriteSheetManifest",
]
