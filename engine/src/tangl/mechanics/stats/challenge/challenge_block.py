from enum import Enum
from typing import Any

from tangl.business.story.structure import Block
from tangl.business.mechanics.stats.quantized_value import QuantizedValue, EnumeratedValue as EV

class StatChallenge:
    cost: Any = None  # cost vector
    stat_domain: Enum = None
    difficulty: QuantizedValue = EV.AVERAGE
    reward: QuantizedValue = EV.AVERAGE



class ChallengeBlock(StatChallenge, Block):
    ...
