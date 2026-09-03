"""
A stat using a power-of-two system on qv's to direct mathematical operations.

1. Growth and decay are _additions_ of measures, adding/removing a level to the same level results in the next level up or down

>>> M = LogIntStat
>>> M.SMALL - M.SMALL
very small
>>> M.SMALL + M.SMALL
medium
>>> M.MEDIUM - M.MEDIUM
small
>>> M.MEDIUM + M.MEDIUM
large

2. it follows that adding/removing 2 of the level below to a level results in the next level up or down

>>> M.SMALL - ( M.VERY_SMALL + M.VERY_SMALL)
very small
>>> M.MEDIUM + (M.SMALL + M.SMALL)
large

3. 'Weighted Measures' are _products_ of measures.  A very large weighting factor is equal to 1.0.

>>> M.MEDIUM * M.VERY_LARGE
medium
>>> M.MEDIUM * M.MEDIUM
very small
>>> M.MEDIUM * M.VERY_SMALL
none

4. Partial ordering, equal by level, inequality by value

>>> M.SMALL < M.MEDIUM < M.LARGE
True
>>> M.MEDIUM + M.VERY_SMALL == M.MEDIUM
True
>>> M.MEDIUM + M.VERY_SMALL > M.MEDIUM
True
>>> M.MEDIUM - M.VERY_SMALL == M.MEDIUM
True
>>> M.MEDIUM - M.VERY_SMALL < M.MEDIUM
True
>>> M(1.0) > M.MEDIUM
False

"""
from __future__ import annotations
import math
from typing import ClassVar

from .base_stat import StatHandler, Stat, Statlike
from ...type_hints import *

ExpValue = float  # range 1-5

class LogIntStatHandler(StatHandler):

    a: ClassVar[float] = 0.0      # amplitude speed of growth
    b: ClassVar[float] = 2.115    # base, units per unit increase
    # 2.1115^0 = 1, 2.115^4 = 20
    c: ClassVar[float] = 1.0      # offset, shift curve up or down

    @classmethod
    def ev_from_fv(cls, fv: FloatValue) -> ExpValue:
        # cast linear value into exponential space, find exponent
        # f(x) = a * log_b( x ) + c - 1
        return (1 + cls.a) * math.log(fv, cls.b) + cls.c

    @classmethod
    def fv_from_ev(cls, ev: ExpValue):
        # cast an exponential space value into linear space
        # g(x) = c * b^( x + a - 1 )
        return cls.c * cls.b ** (ev + cls.a - 1)

    # This is the non-generic mapping without a and c
    # @classmethod
    # def fv_from_ev(cls, ev: ExpValue) -> ExpValue:
    #     return cls.b**(ev - 1)

    # @classmethod
    # def ev_from_fv(cls, fv: FloatValue) -> FloatValue:
    #     return math.log(fv, cls.b) + 1

    @classmethod
    def fv_from_qv(cls, qv: QuantizedValue, **kwargs) -> FloatValue:
        return cls.fv_from_ev(qv)

    @classmethod
    def qv_from_fv(cls, fv: FloatValue, measure: Measure = None) -> QuantizedValue | IntEnum:
        ev = cls.ev_from_fv(fv)
        qv = int( round(ev - 0.1) )  # note, this puts a very small bias to round _down_ the qv
        if measure:
            qv = measure(qv)
        return qv

class LogIntStat(Stat):
    handler = LogIntStatHandler

    @property
    def ev(self) -> ExpValue:
        # exponential value, a _float_ on range 1-5
        return self.handler.ev_from_fv(self.fv)

    # def __add__(self, other: Statlike):
    #     other_value = self.handler.normalize_value(other)
    #     other_ev = LogIntStatHandler.ev_from_fv(other_value)
    #     new_ev = (self.ev + other_ev) * 0.5
    #     fv = LogIntStatHandler.fv_from_ev(new_ev)
    #     return self.__class__(fv)


# class LogIntMeta(type):
#     """
#     Dynamically creates an IntEnum class for a given range of qualifiers/number of increments
#     and exponential-growth base ('b')
#     """
#
#     @staticmethod
#     def create_quality_enum(qualifiers: list[str] | int = 5) -> IntEnum:
#         """
#         Dynamically creates an IntEnum based on a list of qualifiers or count of quality levels.
#         """
#         qualifier_sets = {
#             3: ["low", "mid", "high"],
#             5: ["very_Low", "low", "mid", "high", "very_high"],
#             7: ["vv_low", "very_low", "low", "mid", "high", "very_igh", "vv_High"],
#         }
#         if isinstance(qualifiers, int):
#             qualifiers = qualifier_sets.get(qualifiers, qualifier_sets[5])  # default to 5
#         return IntEnum('Quality', {qual.upper(): i + 1 for i, qual in enumerate(qualifiers)})
#
#     def __new__(cls, name, bases, dct, b: int = 2,
#                 increments: int = 5,
#                 qualifiers: list[str] = None,
#                 **kwargs):
#         dct['b'] = b  # set 'b' as a class attributes
#         dct['increments'] = increments
#         dct['Quality'] = cls.create_quality_enum(qualifiers=qualifiers or increments)
#         return super().__new__(cls, name, bases, dct)

# @functools.total_ordering
# class OldExpStat:
#
#     @staticmethod
#     def closest(num):
#         return min(Measure.LEVELS.values(), key=lambda x:abs(x - num))
#
#     @staticmethod
#     def clamp(value: float):
#         return max([min([value, 2 ** 2]), 0])
#
#     def __init__(self, value):
#         if isinstance(value, Measure):
#             value = value.value
#         elif isinstance(value, str):
#             try:
#                 value = self.LEVELS[value]
#             except KeyError:
#                 raise ValueError(f"{value} is not a valid level")
#         elif not isinstance(value, Number):
#             raise TypeError("value must be a Number, a level string, or a Measure object")
#         if not isinstance(value, float):
#             value = float(value)
#         self.value = self.clamp(value)
#
#     def __mul__(self, other):
#         other = Measure(other)
#         new_value = self.value * other.value * 2**-2
#         result = Measure(new_value)
#         return result
#
#     def __add__(self, other):
#         """Incr this level by doubling, adding the same level"""
#         other = Measure(other)
#         new_value = self.value + other.value
#         result = Measure(new_value)
#         return result
#
#     def __sub__(self, other):
#         """Decr this level by halving, decrementing half of the same level"""
#         other = Measure(other)
#         new_value = self.value - other.value * 0.5
#         result = Measure(new_value)
#         return result
#
# Interesting partial order, equality by level, inequality by value
#
#     def __eq__(self, other):
#         other = Measure(other)
#         return self.level == other.level
#
#     def __lt__(self, other):
#         other = Measure(other)
#         return self.value < other.value
#
#     def __gt__(self, other):
#         return self.value > other.value

