"""Read an Aseprite JSON sprite-sheet export into the client-facing manifest.

Sprite sheets are a mature, non-core problem with a format artists already
export, so a sheet's sidecar is an Aseprite export rather than anything bespoke.
It is read here, as a typed subset, and converted into
:class:`~tangl.presentation.sprite_sheet.SpriteSheetManifest`; no client ever sees
the export itself.

Shapes and meanings follow Aseprite's exporter (``src/app/doc_exporter.cpp``) and
file spec (``docs/ase-file-specs.md``), including the details that are easy to
get wrong:

- ``frames`` is a hash keyed by filename in timeline order (the default), or an array;
- a tag's ``repeat`` is written as a quoted string, and only when it is set;
- a slice key holds from its ``frame`` until the next key;
- a key's ``pivot`` is relative to that key's ``bounds`` origin, not to the canvas;
- a key with no width or height hides the slice from its frame onward.

What the subset accepts, it honours; what it cannot honour, it refuses at load,
because a manifest that is quietly misrendered is worse than one that fails:

- a trimmed frame becomes an offset on its canvas (``spriteSourceSize`` within
  ``sourceSize``), and a frame that does not fill its canvas must state both, since
  either one alone leaves its position on the canvas unstated;
- the slice named ``pivot`` becomes a pivot on each frame it covers;
- rotated frames are refused -- Aseprite never writes them;
- frames drawn from canvases of different sizes are refused: one sheet is one sprite;
- a second slice named ``pivot`` is refused, since either could be meant.

Layers, colours, user data and app metadata are ignored.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tangl.presentation.sprite_sheet import (
    Direction,
    SheetClip,
    SheetFrame,
    SheetPoint,
    SheetRect,
    SheetSize,
    SpriteSheetManifest,
)

PIVOT_SLICE = "pivot"
"""The slice whose keys anchor the sheet's frames.

Aseprite carries pivots on slices rather than on frames or the sheet. Reading the
slice with this name is the one convention layered on top of the format.
"""


class _Export(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")


class _Rect(_Export):
    x: int
    y: int
    w: int = Field(ge=0)
    h: int = Field(ge=0)


class _Size(_Export):
    w: int
    h: int


class _Point(_Export):
    x: int
    y: int


class _Frame(_Export):
    filename: str | None = None
    frame: _Rect
    rotated: bool = False
    trimmed: bool = False
    sprite_source_size: _Rect | None = Field(default=None, alias="spriteSourceSize")
    source_size: _Size | None = Field(default=None, alias="sourceSize")
    duration: int = Field(gt=0)


class _Tag(_Export):
    name: str
    from_frame: int = Field(alias="from", ge=0)
    to_frame: int = Field(alias="to", ge=0)
    direction: Direction = "forward"
    repeat: int | None = Field(default=None, gt=0)

    @field_validator("repeat", mode="before")
    @classmethod
    def _repeat_from_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            if not value.isdigit():
                raise ValueError(f"repeat must be a positive integer, got {value!r}")
            return int(value)
        return value


class _SliceKey(_Export):
    frame: int = Field(ge=0)
    bounds: _Rect
    pivot: _Point | None = None


class _Slice(_Export):
    name: str
    keys: list[_SliceKey] = Field(default_factory=list)


class _Meta(_Export):
    image: str
    size: _Size
    frame_tags: list[_Tag] = Field(default_factory=list, alias="frameTags")
    slices: list[_Slice] = Field(default_factory=list)


class AsepriteExport(_Export):
    """The subset of an Aseprite JSON export this engine reads."""

    frames: list[_Frame]
    meta: _Meta

    @field_validator("frames", mode="before")
    @classmethod
    def _frames_from_hash(cls, value: Any) -> Any:
        if isinstance(value, dict):
            frames: list[dict[str, Any]] = []
            for name, record in value.items():
                if not isinstance(record, dict):
                    # Unpacking a non-record would raise TypeError, which escapes the
                    # loader's ValueError handling and loses the sidecar's name with it.
                    raise ValueError(f"frame {name!r} is {type(record).__name__}, not a frame record")
                frames.append({"filename": name, **record})
            return frames
        return value

    def to_manifest(self) -> SpriteSheetManifest:
        if not self.frames:
            raise ValueError("an export needs at least one frame")
        canvases: set[tuple[int, int]] = set()
        frames: list[SheetFrame] = []
        pivots = self._pivots()
        for index, record in enumerate(self.frames):
            if record.rotated:
                raise ValueError(
                    f"frame {index} is rotated: Aseprite never writes rotated frames, and a "
                    "packer that rotates would need every client to un-rotate"
                )
            rect = record.frame
            # Both fields are optional in the subset, because a frame that fills its
            # canvas needs neither. A frame that does not fill it needs both, and
            # defaulting either one would invent a canvas and a position on it.
            missing = [
                name
                for name, value in (("spriteSourceSize", record.sprite_source_size), ("sourceSize", record.source_size))
                if value is None
            ]
            if record.trimmed and missing:
                raise ValueError(
                    f"frame {index} says it is trimmed but omits {' and '.join(missing)}, "
                    "so where its pixels sit on the canvas is unstated"
                )
            placed = record.sprite_source_size or _Rect(x=0, y=0, w=rect.w, h=rect.h)
            if (placed.w, placed.h) != (rect.w, rect.h):
                raise ValueError(
                    f"frame {index} is {rect.w}x{rect.h} in the sheet but {placed.w}x{placed.h} "
                    "on its canvas; padded or extruded frames are not supported"
                )
            canvas = record.source_size or _Size(w=placed.x + rect.w, h=placed.y + rect.h)
            if record.sprite_source_size is None and (canvas.w, canvas.h) != (rect.w, rect.h):
                raise ValueError(
                    f"frame {index} is {rect.w}x{rect.h} on a {canvas.w}x{canvas.h} canvas, but no "
                    "spriteSourceSize says where it sits, whatever its trimmed flag claims"
                )
            canvases.add((canvas.w, canvas.h))
            frames.append(
                SheetFrame(
                    rect=SheetRect(x=rect.x, y=rect.y, w=rect.w, h=rect.h),
                    offset=SheetPoint(x=placed.x, y=placed.y),
                    duration_ms=record.duration,
                    pivot=pivots.get(index),
                )
            )
        if len(canvases) > 1:
            raise ValueError(
                f"frames are drawn on canvases of different sizes {sorted(canvases)}; "
                "a sheet must hold one sprite"
            )
        [(canvas_w, canvas_h)] = canvases
        return SpriteSheetManifest(
            image=self.meta.image,
            size=SheetSize(w=self.meta.size.w, h=self.meta.size.h),
            canvas=SheetSize(w=canvas_w, h=canvas_h),
            frames=frames,
            clips=[
                SheetClip(
                    name=tag.name,
                    first=tag.from_frame,
                    last=tag.to_frame,
                    direction=tag.direction,
                    repeat=tag.repeat,
                )
                for tag in self.meta.frame_tags
            ],
        )

    def _pivots(self) -> dict[int, SheetPoint]:
        """Each frame's pivot on its canvas, from the key in force at that frame."""

        slices = [s for s in self.meta.slices if s.name == PIVOT_SLICE]
        if len(slices) > 1:
            raise ValueError(f"{len(slices)} slices are named {PIVOT_SLICE!r}; a frame can have one anchor")
        if not slices:
            return {}
        keys = sorted(slices[0].keys, key=lambda key: key.frame)
        pivots: dict[int, SheetPoint] = {}
        for index in range(len(self.frames)):
            current = next((key for key in reversed(keys) if key.frame <= index), None)
            if current is None or current.pivot is None or not (current.bounds.w and current.bounds.h):
                continue
            pivots[index] = SheetPoint(
                x=current.bounds.x + current.pivot.x,
                y=current.bounds.y + current.pivot.y,
            )
        return pivots


def read_aseprite_export(data: str | bytes | dict[str, Any]) -> SpriteSheetManifest:
    """The client-facing manifest for one Aseprite export, or ``ValueError`` saying why not."""

    export = (
        AsepriteExport.model_validate(data)
        if isinstance(data, dict)
        else AsepriteExport.model_validate_json(data)
    )
    return export.to_manifest()


__all__ = ["PIVOT_SLICE", "AsepriteExport", "read_aseprite_export"]
