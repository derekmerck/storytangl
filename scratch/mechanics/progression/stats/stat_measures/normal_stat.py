import random
from statistics import NormalDist

from .base_stat import StatHandler, Stat
from ...type_hints import *

class NormalStatHandler(StatHandler):
    # the mapping from value to tier and the probability function both approximate
    # a normal distribution with mu=10, std=3

    @classmethod
    def qv_from_fv(cls, fv: FloatValue, measure: Measure = None) -> QuantizedValue | IntEnum:
        """
        5 quality ranks:
        - very good (20, 1 step)
        - good      (15-19, 5 steps)
        - average   (7-14, 8 steps)
        - poor      (2-6, 5 steps)
        - very poor (1, 1 step)
        """
        if 19 < fv:
            level = 5
        elif 15 < fv <= 19:
            level = 4
        elif 6 < fv <= 15:
            level = 3
        elif 2 < fv <= 6:
            level = 2
        elif fv <= 2:
            level = 1
        else:
            raise ValueError

        if measure:
            level = measure(level)

        return level

    @classmethod
    def random_value_from_level(cls, level: QuantizedValue) -> FloatValue:
        ranges = [(1, 1), (2, 6), (7, 14), (15, 19), (20, 20)]
        return float( random.randint(*ranges[level-1]) )

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
    def likelihood(cls, value: Statlike) -> float:
        # Probability that x < value given normal distribution (10, 3)
        value = cls.normalize_value(value)
        dist = NormalDist(mu=10, sigma=3)
        return dist.cdf(value)


class NormalStat(Stat):
    handler = NormalStatHandler
