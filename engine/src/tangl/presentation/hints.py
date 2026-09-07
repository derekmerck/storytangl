"""Advisory rendering and media-staging vocabulary."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tangl.type_hints import StyleClass, StyleDict, StyleId


class PresentationHints(BaseModel, extra="allow"):
    """Advisory styling metadata for text and projected-state payloads."""

    model_config = ConfigDict(frozen=True)

    style_name: StyleId | None = None
    style_tags: list[StyleClass] = Field(default_factory=list)
    style_dict: StyleDict = Field(default_factory=dict)
    icon: str | None = None

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


ShapeName = Literal["landscape", "portrait", "square", "avatar", "banner", "bg"]
PositionName = Literal["top", "bottom", "left", "right", "cover", "inline"]
SizeName = Literal["small", "medium", "large"]
TransitionName = Literal[
    "fade_in", "fade_out", "remove", "from_right", "from_left", "from_top",
    "from_bottom", "to_right", "to_left", "to_top", "to_bottom", "update", "scale",
    "rotate",
]
DurationName = Literal["short", "medium", "long"]
TimingName = Literal["start", "stop", "pause", "restart", "loop"]

# Coarse staging grid, named from the viewer's side of the screen. Deliberately
# not theatrical: "stage left" is the performer's left and therefore the
# audience's right, which reads backwards here and is rejected outright rather
# than silently accepted (see StagingHints._normalize_axis).
#
# Subdivisions are the planned extension, keeping these three as the cardinals:
# left_left, left, left_right, mid_left, mid, mid_right, right_left, right,
# right_right — for staging crowds by nudging off a cardinal rather than by
# hardcoded pixel offsets.
MediaXName = Literal["left", "mid", "right"]
MediaYName = Literal["top", "mid", "bottom"]

_AXIS_ALIASES = {
    "screen_left": "left", "screen_right": "right", "center": "mid", "centre": "mid",
    "middle": "mid",
}
_AXIS_REJECTED = {"stage_left", "stage_right"}


class StagingHints(BaseModel, extra="allow"):
    """Client-facing media staging hints."""

    media_shape: ShapeName | float | None = None
    media_size: SizeName | tuple[int, int] | tuple[float, float] | float | None = None
    media_position: PositionName | tuple[int, int] | tuple[float, float] | None = None
    media_transition: TransitionName | None = None
    media_duration: DurationName | float | None = None
    media_timing: TimingName | None = None

    @field_validator("media_x", "media_y", mode="before")
    @classmethod
    def _normalize_axis(cls, value: Any) -> Any:
        """Accept screen-relative aliases; refuse theatrical ones outright."""

        if not isinstance(value, str):
            return value
        name = value.strip().lower()
        if name in _AXIS_REJECTED:
            raise ValueError(
                f"{value!r} is not a staging position. Theatrical 'stage left' is "
                "the performer's left and the viewer's right, which inverts this "
                "vocabulary. Use 'left' or 'right', named from the viewer's side."
            )
        return _AXIS_ALIASES.get(name, name)

    media_x: MediaXName | None = None
    """Horizontal staging slot, named from the viewer's side of the screen."""

    media_y: MediaYName | None = None
    """Vertical staging level."""

    media_flip_h: bool | None = None
    """Mirror the asset horizontally when staged.

    Orthogonal to :attr:`media_position` (where it sits) and
    :attr:`media_transition` (how it arrives, including ``from_left`` and
    ``from_right``). Sprite art has a fixed facing, so a sprite reused on the
    other side of a stage needs mirroring independently of either. Ports honour
    the hints they understand and ignore the rest.
    """


__all__ = [
    "DurationName",
    "MediaXName",
    "MediaYName",
    "PositionName",
    "PresentationHints",
    "ShapeName",
    "SizeName",
    "StagingHints",
    "TimingName",
    "TransitionName",
]
