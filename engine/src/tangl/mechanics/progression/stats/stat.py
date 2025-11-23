from __future__ import annotations

from typing import ClassVar, Union

from pydantic import BaseModel, ConfigDict

from ..handlers.base import StatHandler
from ..handlers.probit import ProbitStatHandler
from ..measures import Quality


ValueLike = Union[float, int, str, Quality]


class Stat(BaseModel):
    """
    A measured value with dual representation:

        - fv: continuous float (e.g., 1–20)
        - qv: discrete tier [1–5], derived via handler

    Construction accepts:
        - float → interpreted as fv directly
        - int in [1, 5] → qv
        - Quality → qv
        - str → Quality name/alias (e.g., "mid", "good")
    """

    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    fv: float

    # Default handler; callers/worlds can subclass Stat and override this.
    handler: ClassVar[type[StatHandler]] = ProbitStatHandler

    def __init__(self, value: ValueLike = 10.0, **data):
        fv = self._normalize_value(value)
        super().__init__(fv=fv, **data)

    @classmethod
    def _normalize_value(cls, value: ValueLike) -> float:
        if isinstance(value, Quality):
            return cls.handler.fv_from_qv(value.value)

        if isinstance(value, str):
            quality = Quality.from_name(value)
            return cls.handler.fv_from_qv(quality.value)

        if isinstance(value, int) and 1 <= value <= 5:
            return cls.handler.fv_from_qv(value)

        # Otherwise treat as fv
        return float(value)

    # Derived representations -------------------------------------------------

    @property
    def qv(self) -> int:
        """Quantized tier (1–5)."""
        return self.handler.qv_from_fv(self.fv)

    @property
    def quality(self) -> Quality:
        """Quality enum representation."""
        return Quality(self.qv)

    # Arithmetic --------------------------------------------------------------

    def __float__(self) -> float:  # type: ignore[override]
        return self.fv

    def __add__(self, other: Union["Stat", float, int]) -> "Stat":
        other_fv = other.fv if isinstance(other, Stat) else float(other)
        return Stat(self.fv + other_fv)

    def __sub__(self, other: Union["Stat", float, int]) -> "Stat":
        other_fv = other.fv if isinstance(other, Stat) else float(other)
        return Stat(self.fv - other_fv)

    # Comparisons -------------------------------------------------------------

    def __eq__(self, other: object) -> bool:  # type: ignore[override]
        """
        Equality is tier-based against other Stats and numeric/Quality types.

        - Stat == Stat → compare qv
        - Stat == Quality / int → compare qv
        - Stat == "name" → compare to Quality.from_name(name)
        """
        if isinstance(other, Stat):
            return self.qv == other.qv
        if isinstance(other, Quality):
            return self.qv == other.value
        if isinstance(other, int):
            return self.qv == other
        if isinstance(other, str):
            try:
                q = Quality.from_name(other).value
            except KeyError:
                return False
            return self.qv == q
        return False

    def __lt__(self, other: Union["Stat", float, int]) -> bool:
        other_fv = other.fv if isinstance(other, Stat) else float(other)
        return self.fv < other_fv

    # Convenience methods -----------------------------------------------------

    def delta(self, other: "Stat") -> float:
        """Return fv difference self - other."""
        return self.fv - other.fv

    def with_handler(self, handler: type[StatHandler]) -> "Stat":
        """
        Return a new Stat with the same fv but a different handler class.

        Useful for “what if this stat lived under a different progression model?”
        """
        cls = type(self)
        new_cls = type(
            f"{cls.__name__}WithHandler",
            (cls,),
            {"handler": handler, "__module__": cls.__module__},
        )
        return new_cls(self.fv)

    def __repr__(self) -> str:
        return f"Stat(fv={self.fv:.2f}, qv={self.qv})"
