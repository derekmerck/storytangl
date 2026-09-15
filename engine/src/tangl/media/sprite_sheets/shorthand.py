"""Authoring shorthands for sprite sheets: a filename, or a compact per-cell form.

Two lighter ways to describe a sheet than an Aseprite export, and both expand
into :class:`~tangl.presentation.sprite_sheet.SpriteSheetManifest`, so there is one
validated shape and one reader:

- a **filename** such as ``master_sprite-idle-4x1-1600ms`` (see :class:`SheetName`);
- a **compact form** (:class:`CompactSheet`) whose per-cell fields each take one
  value or one value per cell -- a single value repeats, like array broadcasting.

They carry uniform or simple timing on a regular grid. Anything more particular
is an Aseprite export.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tangl.presentation.sprite_sheet import (
    SheetClip,
    SheetFrame,
    SheetRect,
    SheetSize,
    SpriteSheetManifest,
)

DEFAULT_FRAME_MS = 100
"""Aseprite's default frame duration, used when a shorthand states no timing."""


def _distribute(total: int, weights: list[float]) -> list[int]:
    """Positive integer milliseconds, proportional to ``weights``, summing to exactly ``total``.

    Largest remainder first, so ordinary weights divide the way arithmetic says
    (0.9 and 0.1 of 2000 are 1800 and 200). A weight too small to earn a whole
    millisecond is then given one, taken from whichever frame has the most -- never
    added on top, which would overrun the total.
    """

    if total < len(weights):
        raise ValueError(f"{total} ms cannot give each of {len(weights)} frames a positive duration")
    scale = sum(weights)
    raw = [total * weight / scale for weight in weights]
    whole = [int(value) for value in raw]
    by_remainder = sorted(range(len(raw)), key=lambda i: raw[i] - whole[i], reverse=True)
    for i in by_remainder[: total - sum(whole)]:
        whole[i] += 1
    for i, ms in enumerate(whole):
        if ms == 0:
            donor = max(range(len(whole)), key=whole.__getitem__)
            whole[donor] -= 1
            whole[i] = 1
    return whole


def _broadcast(value: Any, cells: int, field: str) -> list[Any]:
    if isinstance(value, list):
        if len(value) != cells:
            raise ValueError(f"{field} gives {len(value)} values for {cells} cells")
        return list(value)
    return [value] * cells


def grid_rects(cols: int, rows: int, size: tuple[int, int]) -> list[SheetRect]:
    """The row-major cells of a ``cols`` by ``rows`` grid over an image of ``size`` pixels."""

    width, height = size
    if width % cols or height % rows:
        raise ValueError(f"a {width}x{height} image does not divide into {cols}x{rows} cells")
    cw, ch = width // cols, height // rows
    return [SheetRect(x=(i % cols) * cw, y=(i // cols) * ch, w=cw, h=ch) for i in range(cols * rows)]


class CompactSheet(BaseModel):
    """A sheet described by grid and per-cell values instead of per-frame records.

    Every per-cell field takes **one value or one value per cell**: a single value
    repeats across every cell. ``total`` is sheet-level and never broadcasts; when
    present, ``duration`` values are weights scaled to fill it.
    """

    model_config = ConfigDict(frozen=True)

    sheet: str
    """Grid as ``<columns>x<rows>``, read row-major."""

    role: str | list[str] | None = None
    """Clip name per cell. Consecutive cells with one role become one clip."""

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

    def clips(self) -> list[SheetClip]:
        if self.role is None:
            return []
        cols, rows = self.grid
        roles = _broadcast(self.role, cols * rows, "role")
        clips: list[SheetClip] = []
        start = 0
        for index in range(1, len(roles) + 1):
            if index == len(roles) or roles[index] != roles[start]:
                if any(clip.name == roles[start] for clip in clips):
                    raise ValueError(
                        f"role {roles[start]!r} appears in two separate runs; a clip is a "
                        "contiguous range and cannot be split"
                    )
                clips.append(SheetClip(name=roles[start], first=start, last=index - 1))
                start = index
        return clips

    def to_manifest(self, image: str, size: tuple[int, int]) -> SpriteSheetManifest:
        """Expand into the manifest for an image of ``size`` pixels."""

        rects = grid_rects(*self.grid, size)
        return SpriteSheetManifest(
            image=image,
            size=SheetSize(w=size[0], h=size[1]),
            canvas=SheetSize(w=rects[0].w, h=rects[0].h),
            frames=[SheetFrame(rect=rect, duration_ms=ms) for rect, ms in zip(rects, self.durations())],
            clips=self.clips(),
        )


_SHEET_NAME = re.compile(
    r"^(?P<root>[A-Za-z0-9_]+)"
    r"(?:-(?P<clip>[a-z][a-z0-9_]*))?"
    r"-(?P<cols>[1-9]\d*)x(?P<rows>[1-9]\d*)"
    r"(?:-(?P<amount>[1-9]\d*)(?P<unit>ms|s))?$"
)


class SheetName(BaseModel):
    """What a sheet's filename says about it.

    ``<root>[-<clip>]-<columns>x<rows>[-<total>(ms|s)]``. Underscore binds the root
    and hyphen separates segments, so ``master_sprite-idle-4x1-1600ms`` is a
    four-cell ``idle`` clip for the still named ``master_sprite``, lasting 1600 ms.
    Without a clip segment the sheet's clips come from its sidecar export.

    The grid segment contains an ``x``, which keeps it disjoint from #418's loose
    frame suffix (``-01``), so both conventions can live in one pack.
    """

    model_config = ConfigDict(frozen=True)

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

    def disagreements(self, manifest: SpriteSheetManifest) -> list[str]:
        """Everything this name states that ``manifest`` contradicts.

        When a sidecar and a filename both describe a sheet the sidecar is
        authoritative, but the two must still agree, or one fact is declared twice
        and can silently differ.
        """

        problems: list[str] = []
        size = (manifest.size.w, manifest.size.h)
        if len(manifest.frames) != self.cols * self.rows:
            problems.append(f"it declares {len(manifest.frames)} frames but its name says {self.cols}x{self.rows}")
        else:
            try:
                cells = grid_rects(self.cols, self.rows, size)
            except ValueError as exc:
                problems.append(str(exc))
            else:
                # Count and divisibility cannot tell 4x1 from 2x2: both have four
                # cells, and a 40x12 sheet divides either way. Only the rects can.
                # A trimmed frame may be smaller than its cell, but not outside it.
                for index, (frame, cell) in enumerate(zip(manifest.frames, cells)):
                    r = frame.rect
                    if r.x < cell.x or r.y < cell.y or r.x + r.w > cell.x + cell.w or r.y + r.h > cell.y + cell.h:
                        problems.append(
                            f"frame {index} sits at {r.model_dump()}, not in the {self.cols}x{self.rows} "
                            f"cell its name says {cell.model_dump()}"
                        )
                        break
        if self.clip is not None and self.clip not in manifest.clip_names():
            problems.append(f"the filename names clip {self.clip!r}, which the export does not tag")
        if self.total_ms is not None:
            actual = sum(frame.duration_ms for frame in manifest.frames)
            if actual != self.total_ms:
                problems.append(f"the filename says {self.total_ms} ms, the export's frames last {actual} ms")
        return problems


__all__ = ["DEFAULT_FRAME_MS", "CompactSheet", "SheetName", "grid_rects"]
