from enum import Enum

from tangl.utils.enum_plus import EnumPlusMixin as BetterEnum

class HairColor(BetterEnum, Enum):
    BLONDE = "blonde"
    BROWN = BRUNETTE = "brown"
    DARK = "dark"
    RED = "red"
    GRAY = "gray"
    WHITE = "white"
    AUBURN = "auburn"
    BLUE = "blue"
    GREEN = "green"
    HIGHLIGHTS = "highlights"

class SkinColor(BetterEnum, Enum):
    FAIR = PALE_SKIN = "fair"
    TAN = "tan"
    DARK = DARK_SKIN = "dark"
    ASIAN = "asian"
    EURASIAN = "eurasian"
    LATINA = "latina"
    SEMITIC = "semitic"
    AMERIND = "amerind"

class BodyPhenotype(BetterEnum, Enum):
    AVERAGE = "average"
    CURVY = "curvy"
    SLIM = "slim"
    FIT = "fit"

class EyeColor(BetterEnum, Enum):
    BLUE = "blue"
    BROWN = "brown"
    GREEN = HAZEL = "green"
    GRAY = "gray"

class HairStyle(BetterEnum, Enum):
    VERY_LONG = VERY_LONG_HAIR = "v_long"
    LONG = LONG_HAIR = "long"
    SHORT = SHORT_HAIR = "short"
    VERY_SHORT = VERY_SHORT_HAIR = "v_short"
    CURLY = CURLY_HAIR = "curly"
    PONY_TAIL = "pony_tail"
    LONG_PONY_TAIL = "long_pony_tail"
    PIGTAILS = "pigtails"
    LONG_PIGTAILS = "long_pigtails"
    BRAID = "braid"
    LONG_BRAID = "long_braid"
    BUN = "bun"
    SIDE_BUNS = "side_buns"
    UPDO = "updo"
    FLIP = "flip"
    BALD = NO_HAIR = "bald"
