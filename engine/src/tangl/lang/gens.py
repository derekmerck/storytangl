from __future__ import annotations
from enum import Enum
from typing import Protocol,Self
import random

from tangl.utils.enum_plus import EnumPlusMixin

class IsGendered(Protocol):
    @property
    def is_xx(self) -> bool: ...

class Gens(EnumPlusMixin, Enum):

    XX  = F  = "XX"    # female, "she"
    XY  = M  = "XY"    # male, "he"
    X_  = N  = "X_"    # androgynous/nb, "they"

    @property
    def is_xx(self) -> bool:
        # todo: need 3 states now, they's are she's for now
        if self in { self.XX, self.X_ }:
            return True
        return False

    @classmethod
    def pick(cls, rand = None) -> Self:
        rand = rand or random.Random()
        return rand.choice([cls.XX, cls.XY])

class ExtGens(EnumPlusMixin, Enum):
    # Slightly more biologically motivated and precise for subtle variants

    XX = F = Gens.XX.value  # bio-female, 'she'
    XY = M = Gens.XY.value  # bio-male, 'he'

    # Trans-person
    Xx = TF = "Xx"          # trans female, 'she'
    Xy = TM = "Xy"          # trans male, 'he'

    # Non-binary
    XXY = NB = "XXY"        # androgynous/non-binary, 'they'
    # XXy = AFAB = "XXy"      # nb bio-female
    # XxY = AMAB = "XxY"      # nb bio-male

    # Asexual/Neuter
    X_ = A = Gens.X_.value  # asexual, 'they' for persons, 'it' for objects
    # XX_ = _F  = "XX_"       # asexual bio-female
    # XY_ = _M  = "XY_"       # asexual bio-male, gelding

    @classmethod
    def _missing_(cls, value, *args, **kwargs):
        if isinstance(value, Gens):
            return cls(value.lower())
        return super()._missing_(value)

    @property
    def is_xx(self) -> bool:
        # todo: need 3 states, they's are she's for now
        if self in { ExtGens.F, ExtGens.TF, ExtGens.XXY, ExtGens.X_ }:
            return True
        return False

    @classmethod
    def pick(cls, rand = None) -> Self:
        rand = rand or random.Random()
        return rand.choice([cls.XX, cls.XY])

