from pydantic import field_validator

from tangl.core.entity import Entity
from tangl.core.handlers import on_render

from .enums import HairColor, HairStyle, BodyPhenotype, SkinTone, EyeColor

class Look(Entity):
    hair_color: HairColor = None
    eye_color: EyeColor = None
    phenotype: BodyPhenotype = None
    skin_tone: SkinTone = None
    hair_style: HairStyle = None

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
