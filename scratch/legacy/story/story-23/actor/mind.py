import attr

@attr.s(auto_attribs=True)
class Mind():
    name: str      = None
    surname: str   = None
    nickname: str  = None
    label: str     = None  # Epithet: Princess, Friend

    @property
    def full_name(self):
        return f"{self.name} {self.surname}"

    mind: int      = [40, 60]
    mhealth: int   = [40, 60]
    obedience: int = [40, 60]
    fluency: int   = [40, 60]

    mental_age: int = None

    # outfit_type_pref: str = ["simple", "fancy"]
    outfit_palette_pref: str = ["neutral", "cool", "warm"]

    def competent(self) -> bool:
        return self.mhealth > 30

    def mind_broken(self) -> bool:
        return self.mhealth <= 0
