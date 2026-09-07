"""Normalized presentation geometry shared by the surfaces clients draw on.

A rectangle here is a fraction of whatever plate contains it, with the origin at
the plate's top-left corner, so it survives any rendered size. That is the only
form of geometry that crosses the contract: the engine never learns a client's
pixel dimensions, and a client never learns a world's.

Lives beside :class:`~tangl.journal.fragments.StagingHints` because it is the
same kind of thing — client-facing presentation vocabulary carried alongside the
journal rather than mechanics owned by any one of them. Both the sandbox map
plate and a game block's surface measure themselves this way, and the bounds
rule below is the reason they share a base rather than each keeping a copy: a
rectangle that escapes its plate is silently unclickable rather than visibly
wrong, so it has to be refused in one place.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class NormalizedRect(BaseModel):
    """One rectangle in normalized plate coordinates.

    Carries no notion of what it contains. Binding is by name, decided by
    whichever model subclasses this and by the client that joins it against
    live state.
    """

    model_config = ConfigDict(allow_inf_nan=False)
    """Refuse NaN and infinity before the bounds rule runs.

    The bounds rule cannot catch NaN on its own: every comparison with NaN is
    false, so ``w=nan`` passes ``w <= 0`` and then passes ``x + w > 1.0`` as
    well, and arrives intact at a renderer that turns it into a pixel rect.
    (``x=nan`` happens to be caught by the origin check and infinities by the
    extent check, which is precisely why this was easy to miss.)
    """

    x: float
    y: float
    w: float
    h: float

    @model_validator(mode="after")
    def _validate_bounds(self) -> "NormalizedRect":
        """Refuse a rectangle its plate cannot contain.

        Caught here rather than in a renderer because every client would have
        to rediscover it, and a rectangle off the edge of the plate draws
        nothing while looking perfectly well-formed in the world file.
        """

        if self.w <= 0 or self.h <= 0:
            raise ValueError(
                f"rect must have positive extent, got w={self.w}, h={self.h}"
            )
        if not (0.0 <= self.x and 0.0 <= self.y):
            raise ValueError(
                f"rect origin must be inside the plate, got x={self.x}, y={self.y}"
            )
        if self.x + self.w > 1.0 or self.y + self.h > 1.0:
            raise ValueError(
                "rect must lie wholly inside the plate: "
                f"x+w={self.x + self.w}, y+h={self.y + self.h} exceed 1.0"
            )
        return self

    def as_row(self, name: str) -> list[str | float]:
        """Return the disclosure row for this rectangle, keyed by ``name``."""

        return [name, self.x, self.y, self.w, self.h]


__all__ = ["NormalizedRect"]
