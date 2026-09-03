from __future__ import annotations
from typing import Self
from enum import IntEnum

class EnumeratedValue(IntEnum):
    NONE                     = 0
    V_POOR  = V_EASY         = 1
    POOR    = EASY           = 2
    AVERAGE                  = 3
    GOOD    = HARD           = 4
    V_GOOD  = V_HARD = GREAT = 5

def clamp(value, minimum, maximum):
    return max(min(value, maximum), minimum)

class QuantizedValue:

    def __init__(self, value: int | float):
        self.fv = self._get_fv(value)

    @classmethod
    def _get_fv(cls, value: int | float) -> float:
        if isinstance(value, int):
            if not 0 < value < 5:
                raise ValueError(f"Value {value} is out of range")
            return value / 5.
        elif isinstance(value, float):
            if not 0. < value < 1.:
                raise ValueError(f"Value {value} is out of range")
            return value
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

    def __setattr__(self, key, value):
        if key == "fv":
            value = clamp(value, 0., 1.)
        return super().__setattr__(key, value)

    def __float__(self) -> float:
        return self.fv

    def __int__(self) -> int:
        return min(int(self.fv * 6), 5)

    def ev(self) -> EnumeratedValue:
        return EnumeratedValue(int(self))

    def __iadd__(self, other: int | float):
        self.fv += self._get_fv(other)

    def __add__(self, other: int | float):
        fv = self.fv + self._get_fv(other)
        fv = clamp(fv, 0., 1.)
        return self.__class__(fv)

    def __isub__(self, other: int | float):
        self.fv -= self._get_fv(other)

    def __sub__(self, other: int | float):
        fv = self.fv - self._get_fv(other)
        fv = clamp(fv, 0., 1.)
        return self.__class__(fv)

    def test(self, other: int | float) -> Self:
        """
        Randomly test a qv against another qv and return a result qv

        Consider a function of a competence qv and a difficulty qv as
        the likelihood distribution of success at some qv.

        Use a truncated normal distribution to model success.

        The mean of the distribution is float offset from 0 of the
        difference between quality levels.
        - At poor vs. easy or v_good vs. v_hard, it is 0.
        - At v_good vs. v_easy, it is 1, almost certain success
        - At v_poor vs. v_hard, it is -1, almost certain failure

        The std dev of the function can be adjusted to represent greater
        or lesser role for chance in the outcome.

        Let's consider the default distribution to be N(0,1).

        Now we can sample from the distribution and run the result back
        through a probint table to determine _how_ successful the outcome
        was relative to fv 0.5.  Scores more than 2 std dev greater than
        the expected map to 1.0/level 5.  Scores more than 2 std dev less
        than expected map to 0.0/level 0.
        """
