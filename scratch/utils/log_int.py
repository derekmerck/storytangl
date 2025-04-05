from __future__ import annotations
import functools
from typing import Type
import math
from typing import ClassVar
from enum import IntEnum


class LogIntMeta(type):
    """
    Dynamically creates an IntEnum class for a given range of qualifiers/number of increments
    and exponential-growth base ('b')
    """

    @staticmethod
    def create_quality_enum(qualifiers: list[str] | int = 5) -> IntEnum:
        """
        Dynamically creates an IntEnum based on a list of qualifiers or count of quality levels.
        """
        qualifier_sets = {
            3: ["low", "mid", "high"],
            5: ["very_Low", "low", "mid", "high", "very_high"],
            7: ["vv_low", "very_low", "low", "mid", "high", "very_high", "vv_high"],
        }
        if isinstance(qualifiers, int):
            qualifiers = qualifier_sets.get(qualifiers, qualifier_sets[5])  # default to 5
        return IntEnum('Quality', {qual.upper(): i + 1 for i, qual in enumerate(qualifiers)})

    def __new__(cls, name, bases, dct, b: int = 2,
                increments: int = 5,
                qualifiers: list[str] = None,
                **kwargs):
        dct['b'] = b  # set 'b' as a class attributes
        dct['increments'] = increments
        dct['Quality'] = cls.create_quality_enum(qualifiers=qualifiers or increments)
        return super().__new__(cls, name, bases, dct)


@functools.total_ordering
class LogInt(metaclass=LogIntMeta):

    a: ClassVar[float] = 0.    # amplitude speed of growth
    b: ClassVar[float] = 2.    # base, units per unit increase
    c: ClassVar[float] = 0.    # offset, shift curve up or down

    increments: ClassVar[int] = 5  # steps in scale

    Quality: Type[IntEnum]

    @classmethod
    def _get_exp_value(cls, linear_value: float):
        # cast linear value into exponential space, find exponent
        # f(x) = a * log_b( x ) + c - 1
        return (1 + cls.a) * math.log(linear_value, cls.b) + cls.c

    @classmethod
    def _get_linear_value(cls, exp_value: float):
        # cast an exponential space value into linear space
        # g(x) = c * b^( x + a - 1 )
        return (cls.c + 1) * cls.b ** (exp_value + cls.a)

    @classmethod
    def _normalize_to_linear(cls, value: LogIntLike) -> float:
        # _could_ check that an incoming IntEnum quality has the right number of increments
        # instead of just assuming that it is from this quality-range
        if isinstance(value, LogInt):
            # incoming log ints are cast into _this_ class's linear space
            return cls._get_linear_value( value.ev )
        elif isinstance(value, IntEnum) and len(cls.Quality) != len(value.__class__):
            raise TypeError("Don't know how to expand this kind of quality!")
        elif isinstance(value, str):
            qv = cls.Quality[value.upper()]
            return cls._get_linear_value(qv.value)
        elif isinstance(value, int) and 0 < value < cls.increments:
            # ints are assumed to be in exponential space and must be linearized
            return cls._get_linear_value(value)
        elif isinstance(value, float):
            return value
        raise TypeError

    def __init__(self, value: LogIntLike):
        # value internally is stored in linear range
        value = self._normalize_to_linear(value)
        self.lv: float = value

    @property
    def ev(self):
        return self._get_exp_value(self.lv)

    @property
    def qv(self):
        # quantized value
        value = round( self.ev )
        assert 1 <= value <= self.increments
        return int(value)

    @property
    def exp_range(self):
        return 1, self.increments

    @property
    def linear_range(self):
        return 0, self._get_exp_value(self.increments)

    def __add__(self, value: LogIntLike):
        value = self._normalize_to_linear(value)
        return self.__class__(self.lv + value)

    def __iadd__(self, value: LogIntLike):
        value = self._normalize_to_linear(value)
        self.lv += value

    def __sub__(self, value: LogIntLike):
        value = self._normalize_to_linear(value)
        return self.__class__(self.lv - value)

    def __isub__(self, value: LogIntLike):
        value = self._normalize_to_linear(value)
        self.lv = self.lv - value

    def __eq__(self, value: LogIntLike):
        value = self.__class__( value )
        return self.qv == value.qv

    def __gt__(self, value: LogIntLike):
        value = self.__class__( value )
        return self.qv > value.qv

    def __repr__(self):
        return f"{self.__class__.__name__}({self.lv})"

    def __str__(self):
        return str(int(self.ev))

    @property
    def quality(self):
        return self.Quality(self.qv)

# IntEnum's are automatically coerced into ints
LogIntLike = float | int | LogInt | str
