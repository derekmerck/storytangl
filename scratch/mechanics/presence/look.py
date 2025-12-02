# tangl/mechanics/look/look.py

from typing import Self
from pydantic import field_validator

from tangl.lang.age_range import AgeRange
from tangl.core import Entity
# from tangl.vm.vm_dispatch import on_render
from tangl.story.concepts import Concept
from tangl.lang.gens import Gens

from .enums import HairColor, HairStyle, BodyPhenotype, SkinTone, EyeColor
from .ornaments import Ornamentation
# from .outfit import Outfit

Outfit = object


class Look(Concept):

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

    # @on_render.register()
    def describe(self: Self, *, ctx=None, **_ ):
        # person, outfit/state, visible ornamentation, attitude
        # Provide description, including current outfit if the caller provides it
        # with the request.
        # todo: or we want to invoke a narrative creation service here...
        ...

    def adapt_media_spec(self: Self, *, ctx=None, **_ ):
        ...

    # body type vector for more specific stats:
    sz: float = 0.5      # size scalar for relative renders, f: (0-0.7), m: (0.3-1.0)
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

    # todo: handle makeup similar to ornament?

    # def get_media_spec(self, spec_type: Type[MediaSpec] = MediaSpec) -> MediaSpec:
    #     ...

class HasLook(Entity):

    look: Look
    outfit: Outfit
    ornamentation: Ornamentation

    # @on_render.register()
    def _provide_look_desc(self):
        return { 'look': self.look.describe() }

    # @on_create_media.register()
    def _provide_media_spec(self):
        return self.look.adapt_media_spec()

class FantasticLook(Look):
    # For creatures with unusual features
    # Quite probably need a BodyPart map for this

    body_type: str = None  # human, snakelike, taur, robot

    eye_count: int = 2
    eye_type: str = None   # human, cat, spider (6)

    mandible_type: str = None # human (1, vertical), insectoid (2, lateral), snout
    mandible_count: int = 1

    arm_count: int = 2
    arm_type: str = None   # human, insect, tentacle, robot

    leg_count: int = 2     # indicate digitigrade
    leg_type: str = None   # horse, goat, dog, insect, tentacle, robot

    fur_color: str = None

    horn_count: int = 0
    horn_type: str = None  # goat (2), oni (1), unicorn (1)
    horn_color: str = None # bone

    wing_count: int = 0
    wing_type: str = None  # bug, dragonfly, butterfly, bird/feathered, bat/leather, robotic
    wing_palette: str = None

    tail_count: int = 0
    tail_type: str = None  # catlike, spaded, forked, prehensile
    tail_color: str = None

    ovipositor_type: str = None
    ovipositor_color: str = None
    stinger_type: str = None   # scorpion, wasp
    stinger_color: str = None

