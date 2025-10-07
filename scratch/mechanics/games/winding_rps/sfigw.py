"""
Stone, fire, iron, glass, water

A 5-class variant of sig (extended rps)
"""

import typing as typ
from enum import Enum
import attr
from .sig import SigPrimary, Force as Force_, Unit as Unit_

# 5-element SigType requires some over-rides and passing num_bins back into rps class funcs
SIG_TYPES = ["STONE", "FIRE", "IRON", "GLASS", "WATER"]

SigType = Enum(
    "SigType", SIG_TYPES, type=SigPrimary
)

# Have to over-ride Unit and Force to reference the 5-element SigType
@attr.s(auto_attribs=True)
class Unit(Unit_):

    @property
    def _bin(self) -> typ.Optional[int]:
        if self.sig_typ is None:
            return None
        return self.sig_typ._bin

    @_bin.setter
    def _bin(self, value: int):
        self.sig_typ = SigType.of_bin(value)


@attr.s(auto_attribs=True, repr=False)
class Force(Force_):

    def sig_typ(self) -> str:
        return SigType.closest(self.pseudobary())

    def winding_dist(self, other: "Force"):
        return self.adaptive_winding_dist(other, num_bins=len(SigType))
