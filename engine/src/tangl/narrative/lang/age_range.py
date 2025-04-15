from enum import IntEnum

from tangl.utils.enum_plus import EnumPlusMixin

class AgeRange(EnumPlusMixin, IntEnum):
    VERY_YOUNG = CHILD = 1  # 10     ~2^(n+2)?
    YOUNG = TEEN = 2        # 20
    MID = ADULT = 3         # 40
    OLD = 4                 # 80
    VERY_OLD = 5            # 100

    OTHER = -1                                      # use tags to inspect
