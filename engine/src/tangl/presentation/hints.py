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
# Names and fractions are one vocabulary, not two. A cardinal is sugar for a
# position — `mid` is 0.5 — and the planned subdivisions (left_left, mid_right
# and so on) are midpoints between cardinals, for staging a dialog crowd where
# three avatars argue with one. Nothing downstream stores a pixel called
# "mid"; a name resolves to a position like any other.
#
# A world may therefore say either, and should say whichever it means: a name
# when it wants a station ("on the left", wherever this client puts that), a
# fraction when it wants a placement (0.18, and the same 0.18 on any stage).
#
# Caveat worth knowing, because the pygame port does not implement the
# equivalence cleanly: `mid` centres, so it really is 0.5, but `left` and
# `right` anchor to an edge with a gutter, which is width-dependent and so is
# no fixed fraction at all. A 60px image at `left` centres on 0.125; a 100px
# one on 0.1875. Unifying those would move existing staged sprites, so it is
# left alone here and noted rather than quietly changed.
MediaKeepName = Literal["whole", "width", "height", "none"]
"""Which extent of an image a client should hold inside the frame.

The axes are separable: a panorama may bleed off the sides while its height
matters, a standing figure the reverse. ``"none"`` is a member rather than an
absence because the two say different things -- an unset hint defers to
whatever the client does, while ``"none"`` insists the placement is exact. An
image meant to leave the frame has to be able to say so without knowing what
the client would otherwise have done.

Closed and typed, like every other staging hint. An open tag set is for
vocabularies a world invents, such as plate regions; this one has four members
known in advance. `extra="allow"` remains the escape hatch for a
client-specific policy outside the vocabulary.
"""

MediaXName = Literal["left", "mid", "right"]
MediaYName = Literal["top", "mid", "bottom"]

CARDINAL_X: dict[str, float] = {"left": 0.25, "mid": 0.5, "right": 0.75}
CARDINAL_Y: dict[str, float] = {"top": 0.25, "mid": 0.5, "bottom": 0.75}
"""What each cardinal means as a fraction, so a name and a number are the same
statement and nothing has to reimplement the mapping.

Quarters rather than edges. An edge-anchored cardinal is width-dependent -- the
same name lands somewhere different for a wide image than a narrow one -- which
is exactly what stops a name being expressible as a fraction at all. A quarter
means the same place whatever is measured against it, which is also what lets a
placement compose when frames nest.

Viewer-relative throughout: 0.0 is the viewer's left, and `right` is 0.75. The
theatrical frame inverts this and is rejected outright; see _normalize_axis.

Subdivisions, when they arrive, are midpoints between neighbours -- mid_right
is (0.5 + 0.75) / 2 -- so they need no table of their own.
"""

STAGING_MIN, STAGING_MAX = -2.0, 3.0
"""How far outside the frame a placement may sit.

Not a clamp: off-stage is a real position. An image sliding from -0.5 to 0.2 is
an entrance from the left, and a placement parked outside the frame is an
ordinary frame of that animation. The bounds exist only to separate a position
from a unit mistake -- someone who wrote 50 meaning half way -- and are wide
enough to park a full image clear of either edge.
"""

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

        if isinstance(value, bool):
            raise ValueError("a staging position is a name or a 0..1 fraction, not a bool")
        if isinstance(value, (int, float)):
            if not STAGING_MIN <= float(value) <= STAGING_MAX:
                raise ValueError(
                    f"{value!r} is not a staging position. Positions are measured "
                    "0..1 across the frame -- so 50 is not half way, use 0.5 -- and "
                    f"may sit outside it, from {STAGING_MIN} to {STAGING_MAX}, for "
                    "an image entering or leaving."
                )
            return float(value)
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

    media_x: MediaXName | float | None = None
    """Where this image sits horizontally: a named station, or a fraction.

    A name is a station — "on the left" — and a client may honour it however
    its layout prefers. A ``0..1`` fraction is a placement: the image's
    horizontal *centre*, measured across whatever frame it is staged in.
    """

    media_y: MediaYName | float | None = None
    """Where this image sits vertically: a named level, or a fraction.

    A ``0..1`` fraction places the image's *bottom*, because a staged figure
    stands on something and its baseline is what a placement is about.
    """

    media_keep: MediaKeepName | None = None
    """Ask that a *named* position be held inside the frame, on the axes named.

    Applies to `media_x`/`media_y` given as names, never as fractions. Holding
    an image on screen preserves what a name means -- "right" pulled in is
    still over that way -- and destroys what a number means: 0.75, for an image
    wider than half the frame, lands near the middle, which is a different
    position wearing the same hint.

    So a fraction is always exact. A world that does not know the image's size
    should say a name; that is what names are for, and asking for best effort
    on a coordinate it could not honour is the error rather than the clamp's
    absence.

    ``"width"`` and ``"height"`` are separable on purpose. A wide backdrop may
    want its width held while it bleeds off the top; a tall figure the reverse.

    ``None`` -- the hint unset -- leaves it to client policy, which for a named
    station is normally to keep it visible. ``"none"`` is the opposite and says
    the placement is exact, which is what an image leaving the frame needs.
    """

    media_flip_h: bool | None = None
    """Mirror the asset horizontally when staged.

    Orthogonal to :attr:`media_position` (where it sits) and
    :attr:`media_transition` (how it arrives, including ``from_left`` and
    ``from_right``). Sprite art has a fixed facing, so a sprite reused on the
    other side of a stage needs mirroring independently of either. Ports honour
    the hints they understand and ignore the rest.
    """

    media_clip: str | None = None
    """Which named clip of the media's sprite sheet to play for this use.

    A clip name from the sheet's manifest -- ``idle``, ``call``, ``response``. It
    selects, it does not describe: frame timing belongs to the sheet, and whether
    the clip loops is :attr:`media_timing`, because a sheet cannot say "forever".
    A client without sheets ignores it and draws the still; one whose sheet lacks
    the clip should do the same rather than guess a neighbour.
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
