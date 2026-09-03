from enum import Enum, auto
from typing import Optional, Type, TYPE_CHECKING, Self

from scratch.progression.measures import Quality
if TYPE_CHECKING:
    from scratch.progression.measured_value import MeasuredValueHandler

class PsychosomaticStatDomain(Enum):
    BODY = auto()
    MIND = auto()

    @property
    def stat_measure(self):
        return Quality

    @property
    def stat_handler(self) -> Optional[Type['MeasuredValueHandler']]:
        # None defaults to the MVHandler
        return None

    @classmethod
    def stat_currencies(cls):
        return {
            cls.BODY: "stamina",
            cls.MIND: "wit"
        }

    @property
    def stat_currency(self):
        return self.stat_currencies()[self]

    @classmethod
    def _missing_(cls, key) -> Self:
        if isinstance(key, str):
            key = key.upper()
            if key in cls._member_map_:
                return cls._member_map_[key]
