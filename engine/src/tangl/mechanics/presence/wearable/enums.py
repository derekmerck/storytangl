from enum import IntEnum, Enum, Flag, auto
import functools

from tangl.utils.enum_plus import EnumPlusMixin

@functools.total_ordering
class WearableLayer(EnumPlusMixin, IntEnum):
    """
    An enum representing the layer of clothing that a `Wearable` covers.

    Attributes
    ----------
    INNER: int
        Represents an inner layer of clothing.
    OUTER: int
        Represents an outer, visible layer of clothing.
    OVER: int
        Represents the outer-most layer of clothing like over coats
    """
    BODY  = 20
    INNER = 40     # hides body
    OUTER = 60     # hides inner
    OVER  = 80     # hides outer

    def __gt__(self, other):
        return self.value > other.value


@functools.total_ordering
class WearableState(IntEnum):

    ON   = 100     # being worn
    OPEN = 50      # undone or partially removed
    TORN = 30      # variant for "open"
    OFF  = 10      # removed, but still part of the outfit for tracking

    @classmethod
    def rev_aliases(cls):
        return {
            cls.OFF:  ["remove", "strip"],
            cls.OPEN: ["shifted", "shift"],
            cls.TORN: ["tear"]
        }

    def __gt__(self, other):
        return self.value > other.value

@functools.total_ordering
class WearableCondition(EnumPlusMixin, Enum):

    DESTROYED = 1  # implies REMOVED but still tracked for state
    DAMAGED = 2    # implies TORN
    WORN = 3       # or MENDED if previously damaged and repaired
    # MENDED
    FINE = 4
    NEW = 5

    def __gt__(self, other):
        return self.value > other.value
