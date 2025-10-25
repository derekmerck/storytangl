

from enum import IntEnum
import functools

import attr

clamp = lambda x, min_n, max_n: min( max( min_n, x), max_n )


class QualityTier(IntEnum):
    NONE = 0
    VERY_LOW = 1
    LOW = 2
    MID = 3
    HIGH = 4
    VERY_HIGH = 5
    MAX = 6

    def up(self):
        return self.__class__(clamp(self.value+1, 0, 6))

    def down(self):
        return self.__class__(clamp(self.value-1, 0, 6))

    @classmethod
    def from_float(cls, value: float):
        value = clamp( value, 0.0, 1.0)
        match value:
            case 0.0:
                value_ = 0
            case _:
                value_ = 1 + int( value * 5 )
        return cls(value_)

    @classmethod
    def to_float(cls, member: 'QualityTier') -> float:
        return member.value / float(cls.MAX.value)

    def __float__(self) -> float:
        return self.to_float(self)

    @classmethod
    def rank_incr(cls, n=1/8):
        if isinstance(n, QualityTier):
            n = QualityTier.tier_to_rank_incr(n)
        return n/float(cls.MAX.value)

    @classmethod
    def tier_to_rank_incr(cls, member: 'QualityTier'):
        # MAX -> 1/1, full tier
        # MID -> 1/8, about 10/tier
        # VERY_LOW -> 1/32, about 30/tier
        return 1.0 / 2.0 ** (cls.MAX.value - member.value)


# @functools.total_ordering doesn't work for complex inequality func
class Quality:

    def __init__(self, f):
        if isinstance(f, str):
            f = QualityTier(f)
        if isinstance(f, QualityTier):
            f = float(f)
        if not isinstance(f, float):
            raise TypeError
        f = clamp( f, 0.0, 1.0 )
        self.val = f
        super().__init__()

    @property
    def quality(self):
        return QualityTier.from_float(self.val)

    q = quality  # alias

    def incr(self, n=1/8):
        #: increment val in ranks, default = 1/8 a tier,
        self.val += Q.rank_incr(n)
        self.val = clamp( self.val, 0, 1.0 )

    def decr(self, n=1/8):
        #: decrement val in ranks, default = 1/8 a tier
        self.val -= Q.rank_incr(n)
        self.val = clamp( self.val, 0, 1.0 )

    def __eq__(self, other) -> bool:
        # eq is _by tier_
        if isinstance(other, float):
            other = Q.from_float(other)
        elif isinstance(other, Quality):
            other = other.q
        return self.q is other

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other) -> bool:
        # ineq is _by val_
        return self.val < float(other)

    def __le__(self, other) -> bool:
        return self == other or self < other

    def __gt__(self, other) -> bool:
        return self.val > float(other)

    def __ge__(self, other) -> bool:
        return self == other or self > other

    def __repr__(self) -> str:
        return f"{self.val}/{self.quality.name}"

    def __float__(self) -> float:
        return self.val

    def __add__(self, other):
        return self.__class__( self.val.__add__(float(other)) )

    def __sub__(self, other):
        return self.__class__( self.val.__sub__(float(other)) )

    def __mul__(self, other):
        return self.__class__( self.val.__mul__(float(other)) )

    def __truediv__(self, other):
        return self.__class__( self.val.__truediv__(float(other)) )


Q = QualityTier
Qu = Quality
