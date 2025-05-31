from pydantic import field_validator

from tangl.core import Entity
from tangl.core import on_render
from tangl.narrative.lang.gens import Gens
from tangl.narrative.lang.age_range import AgeRange

from .enums import HairColor, HairStyle, BodyPhenotype, SkinTone, EyeColor
from .ornaments import Ornamentation

Outfit = object


class Look(Entity):

    # default_reduce_flag: ClassVar[bool] = True

    hair_color: HairColor = None
    eye_color: EyeColor = None
    body_phenotype: BodyPhenotype = None
    skin_tone: SkinTone = None
    hair_style: HairStyle = None
    apparent_age: AgeRange = None

    @field_validator("skin_tone", "hair_color", mode="before")
    @classmethod
    def _replace_spaces(cls, value):
        if isinstance(value, str) and " " in value:
            value = value.replace(" ", "_")
        return value

    @on_render.register()
    def _describe_look(self, *, gens: 'Gens' = "xx", outfit: 'Outfit' = None, **context):
        # Provide description, including current outfit if the caller provides it
        # with the request.
        # todo: or we want to invoke a narrative creation service here...
        ...

    # body type vector for more specific stats:
    sz: float = 0.5      # size scalar for aab gens, f: (0-0.7), m: (0.3-1.0)
    ch: float = 0.5      # average for age/sex, m: (0-0.2), f: (0.2-1.0+)
    fit: float = 0.5     # average bmi, fit < 0.3, heavy > 0.7

    # face
    f2m: float = 0.5          # fem < 0.4, masc > 0.6
    aesthetics: float = 0.5   # average

    @property
    def apparent_gender(self) -> Gens:
        if self.f2m <= 0.4:
            return Gens.XX
        elif self.f2m <= 0.6:
            return Gens.X_
        return Gens.XY

    reference_model: str = None

    preg: bool = False

    # todo: handle lipstick, makeup?

    def describe(self):
        # person, outfit/state, visible ornamentation, attitude
        ...

    # def get_media_spec(self, spec_type: Type[MediaSpec] = MediaSpec) -> MediaSpec:
    #     ...

class HasLook(Entity):

    look: Look
    outfit: Outfit
    ornamentation: Ornamentation

    @on_render.register()
    def _provide_look_desc(self):
        return { 'look': self.look.describe() }

class FantasticLook(Look):
    # For creatures with unusual features

    body_type: str = None  # human, snakelike, taur, robot
    arm_type: str = None   # human, insect, tentacle, robot
    leg_type: str = None   # horse, goat, dog, insect, tentacle, robot

    fur_color: str = None

    horn_type: str = None  # goat, oni, unicorn
    horn_color: str = None # bone
    horn_count: int = None

    wing_type: str = None  # bug, dragonfly, butterfly, bird/feathered, bat/leather, robotic
    wing_palette: str = None

    tail_type: str = None  # catlike, spaded, forked, prehensile
    tail_color: str = None

