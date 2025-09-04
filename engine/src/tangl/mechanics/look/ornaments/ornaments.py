"""
Ornaments are tattoos, burns, scars, and piercings on an Actor's body.
Ornamentation is the manager for all ornaments associated with an Actor.
This is analogous to the Wearable/Outfit paradigm.

However, ornaments are not represented as assets because they are unique
to each actor's body.
"""

# todo: refactor using outfit_manager/credential_manager paradigm

from __future__ import annotations
from typing import *
from collections import defaultdict
from enum import auto, Flag

from pydantic import Field

from tangl.core.entity import Entity
from tangl.core.graph import Node, Graph
# from tangl.core import Renderable, on_render
# from tangl.story.story_node import StoryNode
from tangl.lang.helpers import oxford_join
from tangl.lang.body_parts import BodyPart
from .enums import OrnamentType


class Ornament(Entity):
    # Has a UID
    body_part: BodyPart
    ornament_type: OrnamentType
    #: short text, such as "a dragon" tattoo, "tasteful studs in" piercing, "your house" brand,
    text: str

    @classmethod
    def marks_on_her(cls, ornament_type: OrnamentType, texts: List[str], body_part: BodyPart):
        desc = oxford_join( texts )
        s = None
        match ornament_type:
            case OrnamentType.SCAR:
                s = f"scars on her { body_part.lower() }"
            case OrnamentType.TATTOO:
                s = f"{desc} tattoo on her {body_part.lower() }"
            case OrnamentType.PIERCING:
                s = f"{desc} her pierced {body_part.lower()}"
            case OrnamentType.BRAND:
                s = f"{desc} brand is burned into the flesh of her {body_part.lower()}"
            case OrnamentType.MARKER:
                s = f"someone has written {desc} on her {body_part.lower()} in permanent ink"
            case OrnamentType.BURN:
                s = f"burns covering her { body_part.lower() }"
        return s

    def describe(self):
        return self.marks_on_her( self.ornament_type, [self.text], self.body_part)


# todo: should implement this like outfit manager/credential manager
class Ornamentation(Node):

    collection: List[Ornament] = Field(default_factory=list)

    def by_part_type(self, covered_regions: list = None):
        # todo: filter covered regions
        covered_regions = covered_regions or []
        res = defaultdict(list)
        for ornament in self.collection:
            res[ornament.ornament_type, ornament.body_part].append(ornament)
        return dict(res)

    def add_ornament(self, ornament: Ornament ):
        self.collection.append(ornament)

    def remove_ornament(self, ornament: Ornament ):
        # todo: add a convenience accessor
        if ornament in self.collection:
            self.collection.remove(ornament)

    # def __bool__(self):
    #     return len(self.ornaments) > 0

    # @on_render.register()
    def describe(self):

        covered_regions = []
        # if hasattr(self.parent, "outfit"):
        #     covered_regions = self.parent.outfit.get_uncovered_regions()

        # todo: determine if by part or by type is more concise
        #       arm has tattoo and scar vs. scars on her arms and face

        ot = self.by_part_type(covered_regions)
        items = []
        for (pt, ty), orns in ot.items():
            items.append(Ornament.marks_on_her(pt, [x.text for x in orns], ty))
        s = "She has " + oxford_join(items) + "."

        return {'ornaments': s}

    def __bool__(self):
        return len(self.collection) > 0



