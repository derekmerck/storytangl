from enum import Flag, auto

from tangl.utils.enum_plus import EnumPlusMixin

class BodyRegion(EnumPlusMixin, Flag):

    LIPS = auto()
    NOSE = auto()
    EYES = auto()
    FACE = LIPS | EYES | NOSE

    EARS = auto()
    SKULL = EARS

    NECK = auto()
    HEAD = FACE | SKULL | NECK

    TORSO = auto()
    R_HAND = auto()
    L_HAND = auto()
    HANDS = R_HAND | L_HAND
    R_ARM = auto()
    L_ARM = auto()
    ARMS = R_ARM | L_ARM
    UPPER = UPPER_BODY = TORSO | ARMS | HANDS

    PELVIS = auto()
    R_LEG = auto()
    L_LEG = auto()
    LEGS = R_LEG | L_LEG
    R_FOOT = auto()
    L_FOOT = auto()
    FEET = R_FOOT | L_FOOT
    LOWER = LOWER_BODY = PELVIS | LEGS | FEET

    BODY = TORSO | PELVIS
    ALL = HEAD | BODY
