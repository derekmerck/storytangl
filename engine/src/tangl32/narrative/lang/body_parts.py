from enum import Enum, auto, Flag

from tangl.utils.enum_plus import EnumPlusMixin

class BodyRegion(EnumPlusMixin, Enum):
    """A coarse body region enum"""
    # Basic divisions
    HEAD = auto()
    TOP = auto()
    BOTTOM = auto()

    ARMS = auto()      # Upper extremities
    HANDS = auto()

    LEGS = auto()      # Lower extremities
    FEET = auto()


class BodyPart(EnumPlusMixin, Flag):
    """A more detailed hierarchical body region enum"""

    FACE = auto()
    SKULL = auto()
    NECK = auto()
    HEAD = SKULL | FACE | NECK

    CHEST = auto()
    ABDOMEN = auto()
    FRONT = CHEST | ABDOMEN

    UPPER_BACK = auto()
    LOWER_BACK = auto()
    LEFT_BUTTOCK = auto()
    RIGHT_BUTTOCK = auto()
    BACK = UPPER_BACK | LOWER_BACK | LEFT_BUTTOCK | RIGHT_BUTTOCK

    TORSO = FRONT | BACK

    LEFT_ARM = auto()
    LEFT_HAND = auto()
    LEFT_UPPER_EXTREMITY = LEFT_HAND | LEFT_ARM

    RIGHT_ARM = auto()
    RIGHT_HAND = auto()
    RIGHT_UPPER_EXTREMITY = RIGHT_ARM | RIGHT_HAND

    UPPER_EXTREMITIES = RIGHT_UPPER_EXTREMITY | LEFT_UPPER_EXTREMITY
    HANDS = RIGHT_HAND | LEFT_HAND

    TOP = TORSO | UPPER_EXTREMITIES

    HIPS = auto()
    GENS = auto()
    ASS = LEFT_BUTTOCK | RIGHT_BUTTOCK
    PELVIS = HIPS | GENS | ASS

    TAIL = auto()

    LEFT_LEG = auto()
    LEFT_FOOT = auto()
    LEFT_LOWER_EXTREMITY = LEFT_LEG | LEFT_FOOT

    RIGHT_LEG = auto()
    RIGHT_FOOT = auto()
    RIGHT_LOWER_EXTREMITY = RIGHT_LEG | RIGHT_FOOT

    LOWER_EXTREMITIES = LEFT_LOWER_EXTREMITY | RIGHT_LOWER_EXTREMITY | TAIL
    FEET = LEFT_FOOT | RIGHT_FOOT

    BOTTOM = PELVIS | LOWER_EXTREMITIES

    ANYWHERE = HEAD | TOP | BOTTOM
