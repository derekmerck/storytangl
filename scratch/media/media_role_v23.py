from aenum import extend_enum, Enum, StrEnum, auto
import random

from tangl.utils.enum_utils import EnumUtils

class EnumPlus(Enum):

    def __new__(cls, *args, description = None, **kwargs):
        name = args[0] if args else auto()
        member = super()(name)
        desc = args[1] if len(args) > 1 else description
        member.description = desc
        return member

    @classmethod
    def add_role(cls, name: str, description: str = "", aliases: list[str] = None):
        role = cls(name, description=description)
        if aliases:
            for alias in aliases:
                cls._value2member_map_[cls._normalize(alias)] = role
        return role


class MediaRole(StrEnum, EnumPlus):
    NARRATIVE_IMAGE = auto()
    VOICE_OVER = auto()
    CHARACTER_AVATAR = auto()



    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            normalized = cls._normalize(value)
            return cls._value2member_map_.get(normalized)
        return None

    @staticmethod
    def _normalize(s: str) -> str:
        return s.lower().replace('_', '').strip()

    @classmethod
    def pick(cls) -> 'MediaRole':
        return random.choice(list(cls))

    def __str__(self):
        return self.name

# Define initial roles with descriptions
MediaRole.NARRATIVE_IMAGE.description = "An image used in story narration"
MediaRole.VOICE_OVER.description = "Audio for narration"
MediaRole.CHARACTER_AVATAR.description = "Visual representation of a character"

# Usage
MediaRole.add_role("ID_CARD_PICTURE", "A picture used for character identification", aliases=["id_pic", "idcard"])

# Accessing roles
print(MediaRole.NARRATIVE_IMAGE)  # Output: NARRATIVE_IMAGE
print(MediaRole.NARRATIVE_IMAGE.description)  # Output: An image used in story narration
print(MediaRole.ID_CARD_PICTURE)  # Output: ID_CARD_PICTURE
print(MediaRole("id pic"))  # Output: ID_CARD_PICTURE
print(MediaRole.pick())  # Output: Random role