from enum import IntEnum, Enum, Flag, auto

from tangl.utils.enum_plus import EnumPlusMixin


class WearableLayer(EnumPlusMixin, IntEnum):
    # These are just quantized levels on an integer scale

    BODY  = 20
    INNER = 40     # hides body
    OUTER = 60     # hides inner
    OVER  = 80     # hides outer


class WearableState(IntEnum):

    ON   = 100     # being worn
    OPEN = 50      # undone or partially removed
    TORN = 30      # variant for "open"
    OFF  = 10      # removed, but still part of the outfit for tracking
