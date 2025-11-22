import typing as typ
from enum import Enum, auto

from tangl.utils.enum_utils import EnumUtils


class PsychosomaticDomains( EnumUtils, Enum ):
    """Default domains for a simple bi-modal progression system"""

    BODY = auto()   # heath, strength
    MIND = auto()   # wit, spirit

    @classmethod
    def stat_currency(cls): return {
        cls.BODY:       "stamina",    # cost: fatigue
        cls.MIND:       "wit"         # cost: focus
    }

    @classmethod
    def create_currencies(cls):
        from tangl.mechanics.progression.stat_currency import StatCurrency
        for k, v in cls.stat_currency().items():
            StatCurrency(label=v, base_stat=k)

PsychosomaticDomains.create_currencies()
