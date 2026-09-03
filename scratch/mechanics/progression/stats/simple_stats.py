from __future__ import annotations
from typing import Self
import random
from statistics import NormalDist
from typing import Literal
from enum import IntEnum

from pydantic import BaseModel, Field, field_validator, ConfigDict

StatName = str

class Quality5(IntEnum):

    VERY_LOW = VERY_EASY = 1
    LOW = EASY = 2
    MID = 3
    HIGH = HARD = 4
    VERY_HIGH = VERY_HARD = 5

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, Stat5):
            return value.qv()
        elif isinstance(value, int):
            return Stat5.from_int5(value).qv()
        elif isinstance(value, float):
            return Stat5(fv=value).qv()
        return super()._missing_(value)


class Stat5(BaseModel):

    model_config = ConfigDict(validate_assignment=True)
    fv: float = 0

    @field_validator('fv', mode='after')
    def _clamp_01(self, value: float) -> float:
        return min(max(value, 0.), 1.)

    def qv(self) -> Quality5:
        return Quality5( self.as_int5() )
    
    @classmethod
    def from_qv(cls, value: Quality5) -> Self:
        return cls.from_int5(value)

    def __float__(self) -> float:
        return self.fv

    def __int__(self):
        """Returns on range (1, 20)"""
        return self.as_int5()

    @classmethod
    def __sub__(cls, self: Self, other: Self) -> Stat5:
        fv = self.fv - other.fv
        return cls(fv=fv)

    @classmethod
    def __truediv__(cls, self: Self, other: float) -> Stat5:
        fv = self.fv / other
        return cls(fv=fv)

    # Linear stat conversions

    def as_std(self):
        """Returns on range (-2.5, 2.5)"""
        return (self.fv - 0.5) * 5

    @classmethod
    def from_std(cls, value: float):
        if not -2.5 <= value <= 2.5:
            raise ValueError(f'value {value} is out of range')
        fv = ( value / 5.0 ) + 0.5
        return cls(fv=fv)

    def as_int5(self):
        """Returns on range (1, 5)"""
        value = 1 + int( self.fv * 5.0)
        return min(max(value, 1), 5)

    @classmethod
    def from_int5(cls, value: int):
        if not 1 <= value <= 5:
            raise ValueError(f'value {value} is out of range')
        fv = value / 5.0
        return cls(fv=fv)

    def as_int20(self):
        """Returns on range (1, 20)"""
        value = 1 + int( self.fv * 20)
        return min(max(value, 1), 20)

    @classmethod
    def from_int20(cls, value: int):
        if not 1 <= value <= 20:
            raise ValueError(f'value {value} is out of range')
        fv = value / 20.0
        return cls(fv=fv)


class SimpleStats(BaseModel):

    body: Stat5 = Quality5.MID
    mind: Stat5 = Quality5.MID


class StatTestOutcome(IntEnum):
    DISASTER = -1
    FAILURE = 0
    SUCCESS = 1
    MAJOR_SUCCESS = 2

    def __bool__(self) -> bool:
        return self.value > 0

SamplerName = Literal[
    'u20', 'd20',           # 20pt uniform
    'n20', '4d6-4',         # 20pt normal
    'n5',  '4dF',           # 5pt normal
]

class SimpleStatHandler:
    """
    In general, for a "normal" difficulty task with an equally weighted tester competency,
    success is about 50/50.

    Relative difficulty (RD) is `( difficulty - stat ) / 2`

    For 20pt-scale stats (1-20):
    - RD is a number -10 to 10
    - Goal is to beat `10 + RD` on 4d6-4/n20 or beat `( 3, 7, 14, 17 )[RD]` using d20/u20
    - Rolling at least 5 higher or lower than the target indicates a great success or disaster

    For 5pt-scale stats (-2,2):
    - RD is a number -2 to 2
    - Goal is to beat RD on 4dF/n5
    - Rolling at least 1 higher or lower than the target indicates a great success or disaster

    Situational effects from the tester or the test itself may provide additional bonuses or maluses.

    A natural min roll is always a disaster, a natural max roll is always a major success.
    - Using a normal sampler (4d6-4/n20, or 4dF/n5) makes major successes or disasters much less likely.
    """

    @classmethod
    def sample_d20(cls) -> int:
        """
        uniform distribution over ints 1 to 20
        """
        return random.randint(1, 20)

    @classmethod
    def sample_u20(cls) -> float:
        """
        uniform distribution over 1 to 20
        """
        return random.random()*20.

    # Normal 20, test against linear 20 RD
    @classmethod
    def sample_4d6_minus_4(cls) -> list[int]:
        """
        approximates a normal dist over 0 to 20
        """
        vals = [ random.randint(1, 6) for _ in range(4) ]
        return vals

    @classmethod
    def sample_n20(cls) -> float:
        """
        truncated normal dist over 1-20 w mu=10, sigma=2.5
        """
        val = NormalDist(10., 2.5).samples(1)[0]
        val = min(20., max(1., val))
        return val

    @classmethod
    def sample_4dF(cls) -> list[int]:
        """
        approximates a normal dist over -4 to 4
        """
        vals = [ random.randint(-1, 1) for _ in range(4) ]
        return vals

    @classmethod
    def sample_n5(cls):
        """
        truncated normal dist over -4 to 4, mu=0, sigma=1
        """
        val = NormalDist(0., 1.).samples(1)[0]
        val = min(4., max(-4., val))
        return val

    @classmethod
    def test_linear20(cls, value: float, rd: float) -> StatTestOutcome:
        """
        Use with 4d6-4/n20 value, rd in (-2,2)
        """
        if value < 0 or value > 20:
            raise ValueError(f"value {value} must be between 0 and 20")
        if value > 19.:
            # natural success
            return StatTestOutcome.MAJOR_SUCCESS
            # natural disaster
        elif value < 2.:
            return StatTestOutcome.DISASTER
        elif value >= 10.0 + ( 5. * (rd + 1) ):
            # would have succeeded even at 1 difficulty harder
            return StatTestOutcome.MAJOR_SUCCESS
        elif value >= 10.0 + ( 5. * rd ):
            return StatTestOutcome.SUCCESS
        elif value < 10.0 + ( 5. * (rd - 1) ):
            # would have failed even at 1 difficulty easier
            return StatTestOutcome.DISASTER
        return StatTestOutcome.FAILURE

    @classmethod
    def test_normal20(cls, value: float, rd: float):
        """Use w u20/d20 value, rd in (-2,2)"""
        ...

    @classmethod
    def test_rd(cls, value: float, rd: float):
        """Use w n5/4dF value, rd in (-2,2)"""
        if value < -4 or value > -4:
            raise ValueError(f"value {value} must be between -4 and 4")
        if value > 2:
            return StatTestOutcome.MAJOR_SUCCESS
        elif value < -2:
            return StatTestOutcome.DISASTER
        elif value >= rd + 1:
            return StatTestOutcome.MAJOR_SUCCESS
        elif value >= rd:
            return StatTestOutcome.SUCCESS
        elif value < rd - 1:
            return StatTestOutcome.DISASTER
        return StatTestOutcome.FAILURE

    @classmethod
    def test_difficulty(cls,
                        competence: Stat5 = Quality5.MID,
                        difficulty: Stat5 = Quality5.MID,
                        bonus: float = 0.,
                        malus: float = 0.,
                        sampler: SamplerName = "d20") -> StatTestOutcome:

        relative_difficulty = ( difficulty - competence ) / 2.
        # a number -4 to +4 / 2  -> a number between -2 and 2, higher means "harder"
        modified_difficulty = relative_difficulty + bonus - malus

        sampler = sampler.replace("-4", "_minus_4")  # function names can't have dashes
        sampling_func = getattr(cls, f"sampler_{sampler}")
        sampled_value = sampling_func()
        # might want to do something with multiple rolls, like reroll or print them here
        if isinstance(sampled_value, list):
            sampled_value = sum(sampled_value)
        # sampled value is a number between 1 and 20 or -4 and 4, higher means more effective

        if sampler in ['u20', 'd20']:
            outcome = cls.test_normal20(sampled_value, modified_difficulty)
        elif sampler in ['4d6-4', 'n20']:
            outcome = cls.test_linear20(sampled_value, modified_difficulty)
        elif sampler in ['4dF', 'n5']:
            outcome = cls.test_rd(sampled_value, modified_difficulty)

        return outcome

    @classmethod
    def stat_test(cls, test: HasDifficulty, tester: HasStats) -> StatTestOutcome:
        stat_value = getattr(tester, test.stat_name)
        difficulty = test.difficulty
        # todo: figure out bonuses and maluses based on tags or situational effects
        return cls.test_difficulty(stat_value, difficulty)


class HasDifficulty(BaseModel):

    stat_name: StatName
    difficulty: Quality5 = Quality5.MID

    @field_validator("difficulty", mode="after")
    @classmethod
    def _convert_to_qv(cls, data):
        data = Quality5(data)
        return data

    def stat_test(self, tester: HasStats) -> StatTestOutcome:
        return SimpleStatHandler.stat_test(self, tester)


class HasStats(BaseModel):

    stats: SimpleStats = Field(default_factory=SimpleStats)

    def __getattr__(self, name):
        # delegate to stats instance
        if hasattr(self.stats, name):
            return getattr(self.stats, name)
        return super().__getattr__(name)

    def stat_test(self, test: HasDifficulty) -> StatTestOutcome:
        return SimpleStatHandler.stat_test(test, self)

    # todo: how do we add StatNames from stats to the pyi for this type?
