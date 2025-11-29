from __future__ import annotations
from typing import Self
from enum import Enum, auto, IntFlag, KEEP, CONFORM, Flag

from tangl.utils.enum_plus import EnumPlusMixin

class BodyRegion(EnumPlusMixin, Enum):
    """A coarse body region enum."""
    # Basic divisions
    HEAD = auto()
    TOP = auto()
    BOTTOM = auto()

    ARMS = auto()      # Upper extremities
    HANDS = auto()

    LEGS = auto()      # Lower extremities
    FEET = auto()

    def to_part_mask(self) -> BodyPart:
        """
        Coarse region → fine-grained BodyPart mask.
        Relies on BodyPart exposing matching composite aliases
        (e.g., HEAD, TOP, BOTTOM, ARMS, HANDS, LEGS, FEET).
        """
        return BodyPart[self.name]


class BodyPart(EnumPlusMixin, IntFlag):
    """
    A more detailed hierarchical body region enum, inspired by
    DICOM conventions.
    """
    NONE = 0

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
    BUTT = LEFT_BUTTOCK | RIGHT_BUTTOCK
    BACK = UPPER_BACK | LOWER_BACK
    # Butt removed from back for semantic reasons, contrary to phisological definitions
    # BACK = UPPER_BACK | LOWER_BACK | BUTT

    TORSO = FRONT | BACK

    LEFT_ARM = auto()
    LEFT_HAND = auto()
    LEFT_UPPER_EXTREMITY = LEFT_HAND | LEFT_ARM

    RIGHT_ARM = auto()
    RIGHT_HAND = auto()
    RIGHT_UPPER_EXTREMITY = RIGHT_ARM | RIGHT_HAND

    UPPER_EXTREMITIES = RIGHT_UPPER_EXTREMITY | LEFT_UPPER_EXTREMITY
    ARMS = RIGHT_ARM | LEFT_ARM
    HANDS = RIGHT_HAND | LEFT_HAND

    TOP = TORSO | UPPER_EXTREMITIES

    HIPS = auto()
    GENS = auto()
    PELVIS = HIPS | GENS | BUTT

    TAIL = auto()

    LEFT_LEG = auto()
    LEFT_FOOT = auto()
    LEFT_LOWER_EXTREMITY = LEFT_LEG | LEFT_FOOT

    RIGHT_LEG = auto()
    RIGHT_FOOT = auto()
    RIGHT_LOWER_EXTREMITY = RIGHT_LEG | RIGHT_FOOT

    LOWER_EXTREMITIES = LEFT_LOWER_EXTREMITY | RIGHT_LOWER_EXTREMITY | TAIL
    LEGS = LEFT_LEG | RIGHT_LEG
    FEET = LEFT_FOOT | RIGHT_FOOT

    BOTTOM = PELVIS | LOWER_EXTREMITIES

    RIGHT_SIDE = RIGHT_UPPER_EXTREMITY | RIGHT_LOWER_EXTREMITY | RIGHT_BUTTOCK
    LEFT_SIDE = LEFT_UPPER_EXTREMITY | LEFT_LOWER_EXTREMITY | LEFT_BUTTOCK

    ANYWHERE = HEAD | TOP | BOTTOM

    def __bool__(self):
        return self is not BodyPart.NONE

    def __sub__(self, other: Self) -> Self:
        """
        Treat BodyPart values as bitmasks and implement subtraction as
        removing bits from this mask that are present in `other`.

        Example:
            BodyPart.TOP - BodyPart.ARMS
        """
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.value & ~other.value

    def to_regions(self) -> set[BodyRegion]:
        """
        Map a fine mask back to the set of coarse BodyRegion values it overlaps.

        This relies on BodyRegion and BodyPart sharing names for their
        coarse composites, e.g. BodyRegion.TOP → BodyPart.TOP, etc.
        """
        regions: set[BodyRegion] = set()
        for region in BodyRegion:
            part_mask = BodyPart[region.name]
            if self & part_mask:
                regions.add(region)
        return regions

    @classmethod
    def from_tags(cls, item) -> BodyPart | None:
        """
        Normalize item location to a BodyPart mask.

        We allow both:
        - part:<name>   (fine-grained BodyPart aliases)
        - region:<name> (coarse BodyRegion-style labels)

        Since BodyPart defines composite aliases with the same names
        as BodyRegion (e.g., HEAD, TOP, BOTTOM, ARMS, HANDS, LEGS, FEET),
        we can treat both prefixes as producing BodyPart values and
        simply OR them together.
        """
        if not hasattr(item, "get_tag_kv"):
            return None

        mask = BodyPart(0)
        for prefix in ("part", "region"):
            parts = item.get_tag_kv(prefix=prefix, enum_type=BodyPart)
            if parts:
                for p in parts:
                    mask |= p

        return mask or None
