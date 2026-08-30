from __future__ import annotations
import functools
import math
import random
from statistics import NormalDist
from enum import IntEnum
from typing import Type, ClassVar, Union, Self

FloatValue = float
ExpValue = float
QuantizedValue = int

def clamp(value: float, min_val: float, max_val: float) -> float:
    return min(max(value, min_val), max_val)


MVlike = Union['MeasuredValue', int, float]

class MeasuredValueHandler:
    """
    Basic MeasuredValueHandler using a linear tier progression.
    """

    @classmethod
    def normalize_to_fv(cls, value: MVlike) -> FloatValue:
        if isinstance(value, MeasuredValue):
            return value.fv
        elif isinstance(value, float):
            return value
        elif isinstance(value, int):  # int or Measure (IntEnum)
            return cls.fv_from_qv(value)
        raise ValueError(f"Unknown type {value.__class__} passed to stat handler")

    @classmethod
    def qv_from_fv(cls, fv: FloatValue, **kwargs) -> QuantizedValue:
        # linear conversion, 0-20 -> 1-5
        fv = clamp(fv, 0., 20.)
        qv = fv // 5 + 1  # range 1-5 for 0-20
        qv = clamp(qv, 1, 5)
        return int(qv)

    @classmethod
    def fv_from_qv(cls, qv: QuantizedValue, **kwargs) -> FloatValue:
        # linear conversion, 1-5 -> 0-20
        qv = clamp(qv, 1, 5)
        fv = 5.0 * (qv - 1)  # 0-4 * 5 -> 0-20
        fv = clamp(fv, 0., 20.)
        return fv

@functools.total_ordering
class MeasuredValue:
    def __init__(self,
                 value: MVlike,
                 handler: Type[MeasuredValueHandler] = None,
                 measure: Type[IntEnum] = None):
        if handler is None:
            handler = MeasuredValueHandler if not isinstance(value, MeasuredValue) else value.handler
        self.handler = handler

        self.fv = handler.normalize_to_fv(value)

        if measure is None and isinstance(value, MeasuredValue):
            measure = value.measure
        self.measure = measure

    @property
    def qv(self) -> QuantizedValue:
        _qv = self.handler.qv_from_fv(self.fv)
        if self.measure:
            return self.measure(_qv)
        return _qv

    def __iadd__(self, other: MVlike) -> Self:
        other_fv = self.handler.normalize_to_fv(other)
        self.fv += other_fv
        return self

    def __add__(self, other: MVlike) -> Self:
        other_fv = self.handler.normalize_to_fv(other)
        return self.__class__(self.fv + other_fv)

    def __isub__(self, other: MVlike) -> Self:
        other_fv = self.handler.normalize_to_fv(other)
        self.fv -= other_fv
        return self

    def __sub__(self, other: MVlike) -> Self:
        other_fv = self.handler.normalize_to_fv(other)
        return self.__class__(self.fv - other_fv)

    def __gt__(self, other: MVlike) -> bool:
        other_fv = self.handler.normalize_to_fv(other)
        return self.fv > other_fv

    def __eq__(self, other: MVlike) -> bool:
        other_fv = self.handler.normalize_to_fv(other)
        return self.fv == other_fv

    def __int__(self) -> QuantizedValue:
        return int(self.qv)

    def __float__(self) -> FloatValue:
        return self.fv

    def __str__(self) -> str:
        return f"{self.qv!r}({self.fv:0.2f})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.fv:0.2f})"


class LogarithmicMVHandler(MeasuredValueHandler):
    """
    MeasuredValueHandler with logarithmic tier progression.
    """

    a: ClassVar[float] = 0.0      # amplitude speed of growth
    b: ClassVar[float] = 2.115    # base, units per unit increase
    # 2.1115^0 = 1, 2.115^4 = 20
    c: ClassVar[float] = 1.0      # offset, shift curve up or down

    @classmethod
    def ev_from_fv(cls, fv: float) -> ExpValue:
        # cast linear value into exponential space, find exponent
        # f(x) = a * log_b( x ) + c - 1
        return (1 + cls.a) * math.log(fv, cls.b) + cls.c

    @classmethod
    def fv_from_ev(cls, ev: ExpValue) -> FloatValue:
        # cast an exponential space value into linear space
        # g(x) = c * b^( x + a - 1 )
        return cls.c * cls.b ** (ev + cls.a - 1)

    @classmethod
    def fv_from_qv(cls, qv: QuantizedValue, **kwargs) -> FloatValue:
        qv = clamp(qv, 1, 5)
        fv = cls.fv_from_ev(qv)
        fv = clamp(fv, 0., 20.)
        return fv

    @classmethod
    def qv_from_fv(cls, fv: FloatValue, **kwargs) -> QuantizedValue:
        ev = cls.ev_from_fv(fv)
        qv = round(ev - 0.1)      # this puts a very small bias to round _down_ the qv
        qv = clamp(qv, 1, 5)
        return int(qv)


class NormalMVHandler(MeasuredValueHandler):
    """
    MeasuredValueHandler with a normal tier distribution.
    """
    mu = 10
    sigma = 3

    @classmethod
    def qv_from_fv(cls, fv: FloatValue, **kwargs) -> QuantizedValue:
        """
        5 quality ranks:
        - very good (20, 1 step)
        - good      (15-19, 5 steps)
        - average   (7-14, 8 steps)
        - poor      (2-6, 5 steps)
        - very poor (1, 1 step)
        """
        if fv < cls.mu - 2.5*cls.sigma:     # fv < 2
            return 1
        elif fv < cls.mu - cls.sigma:       # fv < 6
            return 2
        elif fv < cls.mu + cls.sigma:       # fv < 13
            return 3
        elif fv <= cls.mu + 2.5*cls.sigma:  # fv < 18
            return 4
        else:
            return 5

    @classmethod
    def random_value_from_level(cls, level: QuantizedValue) -> FloatValue:
        ranges = [(1, 2), (3, 6), (7, 14), (15, 18), (19, 20)]
        return float(random.randint(*ranges[level-1]))

    @classmethod
    def average_value_from_level(cls, level: QuantizedValue) -> FloatValue:
        match level:
            case 1:
                return 1.0
            case 2:
                return 4.0
            case 3:
                return 10.0
            case 4:
                return 17.0
            case 5:
                return 20.0

    @classmethod
    def fv_from_qv(cls, qv: QuantizedValue, random_value: bool = False) -> FloatValue:
        if random_value:
            return cls.random_value_from_level(qv)
        return cls.average_value_from_level(qv)

    @classmethod
    def likelihood(cls, value: MVlike) -> float:
        # Probability that x < value given normal distribution (10, 3)
        value = cls.normalize_to_fv(value)
        dist = NormalDist(mu=cls.mu, sigma=cls.sigma)
        return dist.cdf(value)
