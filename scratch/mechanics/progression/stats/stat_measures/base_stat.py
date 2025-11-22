from typing import ClassVar
import functools

from ..type_hints import *
from ..measures import Quality, measure_of

class StatHandler:
    # Stats have 20 incremental values (float, fv) and a 5-level "measure" (int, qv)

    @classmethod
    def qv_from_fv(cls, fv: FloatValue, measure: Type[Measure] = None) -> QuantizedValue | IntEnum:
        """
        Quality val from float val with standard linear sort into 5 bins
        """
        qv = int(((fv - 1) // 4 ) + 1)
        if measure:
            return measure(qv)
        return qv

    @classmethod
    def fv_from_qv(cls, qv: QuantizedValue, **kwargs) -> FloatValue:
        """
        Standard linear expansion of 5 bins to the midpoint value of each bin
        """
        return (qv - 1. ) * 4. + 2.

    @classmethod
    def delta(cls, value0: Statlike, value1: Statlike) -> FloatValue:
        """
        delta represents "expense" of getting from v0 to v1

        Default linear difference v1-v0 normalized to a relative
        distance StatValue (0-20)

        The float value range of delta is (-19, 19)
        - very low (1) vs very high (20) = 20 - 1 =  19
        - very high (20) vs very low (1) = 1 - 20 = -19
        - same level vs same level = x - x = 0
        So add 20, divide by 2 to normalize to a stat value
        """
        value0 = cls.normalize_value(value0)
        value1 = cls.normalize_value(value1)
        diff = value1 - value0
        normalized_diff = (diff + 20.0) / 2.0
        return normalized_diff

    @classmethod
    def likelihood(cls, value: Statlike) -> float:
        """
        Likelihood x < value

        Default uniform probability.
        """
        value = cls.normalize_value(value)
        return value / 20.0

    @classmethod
    def relative_likelihood(cls, value0: Statlike, value1: Statlike) -> float:
        # returns a probability 0-1
        dist = cls.delta(value0, value1)
        likelihood = cls.likelihood(dist)
        return likelihood

    @classmethod
    def normalize_value(cls, value: Statlike, measure: Measure = None) -> float:
        # todo: check that an incoming IntEnum quality has the right number of
        #       increments instead of just assuming that it is from this quality-range
        if isinstance(value, Stat):
            # If it's a _different_ stat type should it be cast by level into this type?
            return value.fv
        elif isinstance(value, int):
            # It's a level
            qv = value
            return cls.fv_from_qv(qv)
        elif isinstance(value, str):
            # It's a level _name_
            qv = measure_of(value)
            if not qv:
                raise ValueError(f"Bad value '{value}' for measure")
            # if not measure:
            #     raise ValueError("Named values require a Measure class")
            # qv = measure(value)
            return cls.fv_from_qv(qv)
        elif isinstance(value, float):
            # It's a value
            return value
        raise TypeError

    @classmethod
    def exp2(cls, value: Statlike):
        """
        - powers of 2 by qv or ev offset by -2
        - range is 0.125 -> 4
        - mid is 1

        LEVELS = {
            "none": 0.,
            "very small": 2**-2,  # 1/4
            "small": 2**-1,       # 1/2
            "medium": 2**0,       # 1
            "large": 2**1,        # 2
            "very large": 2**2 }  # 4
        """
        fv = cls.normalize_value(value)
        if hasattr(cls, "ev_from_fv"):
            v = cls.ev_from_fv(fv)
        else:
            v = cls.qv_from_fv(fv)
        return 2**(v-3)

from pydantic import BaseModel, field_validator

@functools.total_ordering
class Stat(BaseModel):
    """
    The class var 'measure' defines names for the five quality levels.
    The class var 'handler' determines how levels, distances, and probabilities
    are computed.
    """

    measure: ClassVar[Type[Measure]] = Quality
    handler: ClassVar[Type[StatHandler]] = StatHandler

    fv: float = 10.0  # range 1-20

    def __init__(self, value: Statlike):
        value = self.handler.normalize_value(value, self.measure)
        super().__init__(fv=value)

    @property
    def qv(self) -> Measure:
        # Quantized-value (1-5)
        return self.handler.qv_from_fv(self.fv, self.measure)

    def __int__(self) -> QuantizedValue:
        return int(self.qv)

    def __float__(self) -> FloatValue:
        return self.fv

    def __str__(self):
        return f"{self.qv!r}({self.fv:0.2f})"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.fv:0.2f})"

    # Ordering funcs

    def __eq__(self, other: Statlike) -> bool:
        if isinstance(other, (int, str)):
            # compare by level
            return int(self) == int(other)
        # compare by value
        return float(self) == float(other)

    def __gt__(self, other: Statlike) -> bool:
        if isinstance(other, (int, str)):
            # compare by level
            return int(self) > int(other)
        # compare by value
        return float(self) > float(other)

    # Numerical funcs

    def __add__(self, other: Statlike):
        other_value = self.handler.normalize_value(other)
        return self.__class__(self.fv + other_value)

    def __iadd__(self, other: Statlike):
        other_value = self.handler.normalize_value(other)
        self.fv += other_value

    def __sub__(self, other: Statlike):
        other_value = self.handler.normalize_value(other)
        return self.__class__(self.fv - other_value)

    def __isub__(self, other: Statlike):
        other_value = self.handler.normalize_value(other)
        self.fv -= other_value

    @property
    def exp2(self):
        return self.handler.exp2(self)
