import types

from enum import IntEnum

from tangl.utils.enum_plus import EnumPlusMixin as EnumUtils  # Provides casting by value


class Quality(EnumUtils, IntEnum):
    # Are NONE and MAX useful?
    # NONE                     = 0
    VERY_LOW                 = 1
    LOW                      = 2
    MID = AVERAGE            = 3
    HIGH                     = 4
    VERY_HIGH                = 5
    # MAX                      = 6

class Size(EnumUtils, IntEnum):
    VERY_SMALL = TINY       = 1
    SMALL                   = 2
    MID                     = 3
    LARGE                   = 4
    VERY_LARGE = HUGE       = 5

class Ability(EnumUtils, IntEnum):
    VERY_WEAK   = UNSKILLED  = 1
    WEAK        = NOVICE     = 2
    OK          = SKILLED    = 3
    STRONG      = MASTER     = 4
    VERY_STRONG = EXPERT     = 5

class Difficulty(EnumUtils, IntEnum):
    VERY_EASY   = TRIVIAL    = 1
    EASY                     = 2
    CHALLENGING              = 3
    HARD        = DIFFICULT  = 4
    VERY_HARD   = IMPOSSIBLE = 5

class Result(EnumUtils, IntEnum):
    VERY_POOR   = TERRIBLE   = 1
    POOR                     = 2
    AVERAGE                  = 3
    GOOD                     = 4
    VERY_GOOD   = EXCELLENT  = 5

class Rarity(EnumUtils, IntEnum):
    VERY_COMMON              = 1
    COMMON                   = 2
    UNCOMMON                 = 3
    RARE                     = 4
    VERY_RARE                = 5

class Grade(EnumUtils, IntEnum):
    F = FAIL                 = 1  # 70
    C = PASS                 = 2  # 80
    B                        = 3  # 90
    A                        = 4  # 99
    S = SUPERIOR             = 5  # 100

class Grade15(EnumUtils, IntEnum):
    F_MINUS                  = 1   # 40
    F = FAIL                 = 2   # 55
    F_PLUS                   = 3   # 60
    D_MINUS                  = 4   # 63
    D                        = 5   # 67
    D_PLUS                   = 6   # 70

    C_MINUS = LOW_PASS       = 7   # 73
    C = PASS                 = 8   # 77
    C_PLUS                   = 9   # 80

    B_MINUS                  = 10  # 83
    B                        = 11  # 87
    B_PLUS                   = 12  # 90

    A_MINUS                  = 13  #, 93
    A                        = 14  #, 99

    S = SUPERIOR             = 15  #, 100

class Affection(IntEnum):
    HATEFUL                  = 1
    SOUR                     = 2
    NEUTRAL                  = 3
    AMIABLE                  = 4
    LOVING                   = 5

class Trust(IntEnum):
    VERY_FEARFUL = TERRIFIED = 1
    FEARFUL                  = 2
    AMBIVALENT               = 3
    TRUSTING                 = 4
    VERY_TRUSTING = LOYAL    = 5

class Willingness(IntEnum):
    DEFIANT                  = 1
    RESISTANT                = 2
    AMBIVALENT               = 3
    WILLING                  = 4
    EXCITED                  = 5


# Collect all enum values into a dictionary for namespace evals
measure_namespace = dict()
for enum_class in [Quality, Size, Ability, Difficulty, Result, Rarity, Grade, Affection, Trust, Willingness]:
    for name, member in enum_class.__members__.items():
        measure_namespace[name] = member
measure_namespace["NONE"] = 0
measure_namespace["MAX"] = 100
measure_namespace = types.SimpleNamespace(**measure_namespace)

def measure_of(value: str) -> IntEnum:
    # convert strings into Measure/Ints
    return getattr(measure_namespace, value.upper(), None)

