import typing as typ
import attr
from tangl.manager import ManagedObject
from tangl.utils.gender_enum import Gender as G


@attr.s(auto_attribs=True)
class Body(ManagedObject):
    strength: int = [40, 60]
    phealth: int = [40, 60]

    # Gender
    birth_gender: G = {G.XY: 49, G.XX: 49, G.XXY: 2}
    has_xx: int = 0  # Set when gender is applied during naming
    has_xy: int = 0

    @property
    def working_gender(self):
        if self.has_xx <= 0 and self.has_xy <= 0:
            return G.NULL
        elif self.has_xx >  0 and self.has_xy <= 0:
            return G.XX
        elif self.has_xx <= 0 and self.has_xy > 40:
            return G.XY
        elif self.has_xx >  0 and self.has_xy > 40:
            return G.XXY
        elif self.has_xy <= 40:
            return G.XYz
        else:
            raise TypeError

    # Body type
    face_type: int = [40, 60]
    attractiveness: int = [40, 60]
    # Attractiveness should be heavily influenced by bmi and social standards

    height: int = [60, 68]
    bmi: float = 22.5
    ave_height: typ.ClassVar = 64
    ave_bmi: typ.ClassVar = 22

    @property
    def weight(self):
        return (self.bmi / 703) * self.height**2
    @weight.setter
    def weight(self, value):
        self.bmi = (value / self.height**2) * 703

    ethnicity: str  = None
    skin_color: str = ["light", "dark"]
    hair_color: str = ["blonde", "brunette"]
    hair_len: str   = ["none", "short", "medium", "long", "vlong"]

    breasts: int = attr.ib(default=None)

    age: int = [20, 40]

    voice: int   = 50
    hearing: int = 50
    sight: int   = 50
    arms: int    = 50
    legs: int    = 50

    ornaments: typ.Dict = None  # Scars, brands, piercings

    def mobile(self) -> bool:
        return self.legs > 30 and self.phealth > 30

    def healthy(self) -> bool:
        return self.phealth > 30

    def near_death(self) -> bool:
        return self.phealth <= 0
