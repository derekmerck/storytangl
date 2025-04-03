from __future__ import annotations
from enum import Enum

class PoV(Enum):
    # Perspective
    _1s = 1  # first person, etc.
    _2s = 2
    _3s = 3

    _1p = 4  # first person plural, etc.
    _2p = 5
    _3p = 6

    def person_and_plural(self) -> tuple[int, bool]:
        person: int = (((self.value - 1) % 3) + 1)
        plural: bool = bool((self.value - 1) // 3) > 0
        return person, plural

    def plural(self) -> PoV:
        match self:
            case PoV._1s | PoV._1p:
                return PoV._1p
            case PoV._2s | PoV._2p:
                return PoV._2p
            case PoV._3s | PoV._3p:
                return PoV._3p
        raise ValueError

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str) and not value.startswith("_"):
            value = "_" + value
            return cls(value)
        if isinstance(value, tuple):
            # it's a (person, plural) description
            match value:
                case (1, False):
                    return PoV._1s
                case 2, False:
                    return PoV._2s
                case 3, False:
                    return PoV._3s
                case 1, True:
                    return PoV._1p
                case 2, True:
                    return PoV._2p
                case 3, True:
                    return PoV._3p
        for name, member in cls._member_map_.items():
            if value == name:
                return member
