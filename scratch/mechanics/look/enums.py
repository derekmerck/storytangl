"""
Provides a common vocabulary for the physical traits of human-like actors.

Using a structured format enables extending the `describe` and `media_spec` adapters
for additional voices and media styles.
"""

from enum import Enum, IntEnum

from tangl.utils.enum_plus import EnumPlusMixin

class HairColor(EnumPlusMixin, Enum):
    BLONDE = GOLD = "blonde"
    BRUNETTE = BROWN = "brown"  # n
    DARK = "dark"               # k
    RED = "red"
    GRAY = "gray"
    WHITE = "white"
    AUBURN = "auburn"

    BLUE = NAVY = "blue"
    PINK = "pink"
    PURPLE = "purple"
    GREEN = "green"

    CANDYFLOSS = "candyfloss"   # pink and periwinkle
    WATERMELON = "watermelon"   # pink and sea green

    HIGHLIGHTS = "highlights"   # use tags to inspect
    MULTICOLOR = "multicolor"   # use tags to inspect
    OTHER = "other"             # use tags to inspect

class SkinTone(EnumPlusMixin, Enum):
    LIGHT = PALE = FAIR = "light"
    TAN = "tan"
    OLIVE = "olive"   # Mediterranean
    DARK = "dark"
    ASIAN = "asian"
    EURASIAN = "eurasian"
    LATINA  = CAFE = "latina"
    SEMITIC = "semitic"
    AMERIND = "amerind"

    OTHER = "other"  # use tags to inspect

class BodyPhenotype(EnumPlusMixin, Enum):
    """
    Common body-types:
    https://www.calculator.net/body-type-calculator.html
    """
    # Basic types
    AVERAGE                           = "average"
    SLIM  = RECTANGLE    = BANANA     = "slim"      # 1/1/1, low bmi
    FIT   = INV_TRIANGLE = STRAWBERRY = "fit"       # 2/1/1
    CURVY = HOURGLASS                 = "curvy"     # 2/1/2, low bmi, high ch
    ROUND                = APPLE      = "round"     # 1/2/1, high bmi
    TRIANGLE             = PEAR       = "pear"      # 1/1/2, high bmi, low ch

    CURVY_PLUS                        = "curvy+"    # 3/1/3, augmented
    ROUND_PLUS                        = "round+"    # 1/3/1, obese
    FIT_PLUS = CUT                    = "fit+"      # 3/1/1, jacked

    OTHER = "other"                                 # use tags to inspect

class Height(EnumPlusMixin, Enum):
    VERY_SHORT = "very_short"
    SHORT = "short"
    AVERAGE = "average"
    TALL = "tall"
    VERY_TALL = "very_tall"
    OTHER = "other"

class EyeColor(EnumPlusMixin, Enum):
    BLUE = "blue"
    BROWN = "brown"
    GREEN = HAZEL = "green"
    GRAY = "gray"
    BLACK = DARK = "black"

    HETEROCHROME = "heterochrome"                   # use tags to inspect
    OTHER = "other"                                 # use tags to inspect

class HairStyle(EnumPlusMixin, Enum):
    VERY_LONG = VERY_LONG_HAIR = "v_long"
    LONG = LONG_HAIR = "long"
    SHORT = SHORT_HAIR = NEAT = "short"
    VERY_SHORT = VERY_SHORT_HAIR = "v_short"
    SHAVED = "shaved"
    BALD = NO_HAIR = "bald"

    MESSY = MESSY_HAIR = "messy"
    WILD = WILD_HAIR = "wild"
    CURLY = CURLY_HAIR = "curly"
    BOB = "bob"
    SHAVED_SIDES = "shaved_sides"  # "sidecut" in booru
    FLIP = "flip"

    PONY_TAIL = "pony_tail"
    LONG_PONY_TAIL = "long_pony_tail"
    PIGTAILS = "pigtails"      # double pony, twin tails for double braids
    LONG_PIGTAILS = "long_pigtails"

    BRAID = "braid"
    LONG_BRAID = "long_braid"
    TWIN_TAILS = "twin_tails"  # double braid, pigtails for double pony
    CORNROWS = "cornrows"

    BUN = "bun"
    MESSY_BUN = "messy_bun"
    SIDE_BUNS = "side_buns"
    UPDO = "updo"

    OTHER = "other"                                 # use tags to inspect

class PresentingGender(EnumPlusMixin, Enum):
    XY = MASCULINE = "masculine"
    XX = FEMININE = "feminine"
    XXY = ANDROGYNOUS = "androgynous"
    OTHER = "other"                                  # use tags to inspect

class Attitude(EnumPlusMixin, Enum):
    SAD = "sad"
    EXCITED = "excited"
    SCARED = "scared"
    LEWD = "lewd"
    ANGRY = "angry"
    HURT = "hurt"

class VocalAccent(EnumPlusMixin, Enum):
    US = "us"
    GB = "gb"
    AU = "au"
    RU = "ru"
    JP = "jp"
