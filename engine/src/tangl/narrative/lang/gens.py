from __future__ import annotations
from enum import Enum
from typing import Protocol
import random

from tangl.utils.enum_plus import EnumPlusMixin

class IsGendered(Protocol):
    @property
    def is_xx(self) -> bool: ...

class Gens(EnumPlusMixin, Enum):

    XX  = F  = "XX"    # bio female
    XY  = M  = "XY"    # bio male
    X_  = N  = "X_"    # androgynous

    @property
    def is_xx(self) -> bool:
        if self in { self.XX, self.X_ }:
            return True
        return False

    @classmethod
    def pick(cls) -> Gens:
        return random.choice([cls.XX, cls.XY])

class ExtGens(EnumPlusMixin, Enum):

    XX = F = Gens.XX.value  # female
    XY = M = Gens.XY.value  # male
    X_ = N = Gens.X_.value  # androgynous/null

    Xx  = SF = AMAB = "Xx"    # surgical/trans female
    Xy  = SM = AFAB = "Xy"    # surgical/trans male

    XXY = H  = "XXY"   # herm
    # XXy = FH = "XXy"   # female surgical herm
    # XxY = MH = "XxY"   # male surgical herm

    # Castrated
    Xz  = G  = "Xz"    # gelding
    XXz = GH = "XXz"   # herm gelding
    # Xxz = GMH = "Xxz"  # male surgical herm gelding
    # XXz = GFH = "XXz"  # female surgical herm gelding

    @classmethod
    def _missing_(cls, value, *args, **kwargs):
        if isinstance(value, Gens):
            return cls(value.lower())
        return super()._missing_(value)

    @property
    def is_xx(self) -> bool:
        if self in { ExtGens.XX, ExtGens.Xx,
                     ExtGens.XXY, ExtGens.XxY, ExtGens.XXz,
                     ExtGens.X_ }:
            return True
        return False

    @classmethod
    def pick(cls) -> Gens:
        return random.choice([ExtGens.XX, ExtGens.XY])

