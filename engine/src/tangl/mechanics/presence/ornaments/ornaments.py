"""
Ornaments are tattoos, burns, scars, and piercings on an Actor's body.
Ornamentation is the manager for all ornaments associated with an Actor.
This is analogous to the Wearable/Outfit paradigm.

However, ornaments are not represented as assets because they are unique
to each actor's body.
"""

# todo: refactor using outfit_manager/credential_manager paradigm

from __future__ import annotations
from collections import defaultdict
from typing import Any

from pydantic import Field

from tangl.core import Entity, Node
# from tangl.core import Renderable, on_render
# from tangl.story.story_node import StoryNode
from tangl.lang.helpers import oxford_join
from tangl.lang.body_parts import BodyPart, BodyRegion
from .enums import OrnamentType


class Ornament(Entity):
    # Has a UID
    body_part: BodyPart
    ornament_type: OrnamentType
    #: short text, such as "a dragon" tattoo, "tasteful studs in" piercing, "your house" brand,
    text: str

    @classmethod
    def describe_mark(
        cls,
        ornament_type: OrnamentType,
        texts: list[str],
        body_part: BodyPart,
        *,
        possessive: str = "their",
    ) -> str:
        desc = oxford_join(texts)
        body_text = body_part.lower().replace("_", " ")
        s = None
        match ornament_type:
            case OrnamentType.SCAR:
                s = f"scars on {possessive} {body_text}"
            case OrnamentType.TATTOO:
                s = f"{desc} tattoo on {possessive} {body_text}"
            case OrnamentType.PIERCING:
                s = f"{desc} {possessive} pierced {body_text}"
            case OrnamentType.BRAND:
                s = f"{desc} brand is burned into the flesh of {possessive} {body_text}"
            case OrnamentType.MARKER:
                s = f"someone has written {desc} on {possessive} {body_text} in permanent ink"
            case OrnamentType.BURN:
                s = f"burns covering {possessive} {body_text}"
        return s

    @classmethod
    def marks_on(
        cls,
        ornament_type: OrnamentType,
        texts: list[str],
        body_part: BodyPart,
        *,
        possessive: str = "their",
    ) -> str:
        return cls.describe_mark(ornament_type, texts, body_part, possessive=possessive)

    @classmethod
    def marks_on_her(
        cls,
        ornament_type: OrnamentType,
        texts: list[str],
        body_part: BodyPart,
    ) -> str:
        return cls.marks_on(ornament_type, texts, body_part, possessive="her")

    def describe(self):
        return self.marks_on(
            self.ornament_type,
            [self.text],
            self.body_part,
            possessive="their",
        )


# todo: should implement this like outfit manager/credential manager
class Ornamentation(Node):

    collection: list[Ornament] = Field(default_factory=list)

    def by_part_type(self, covered_regions: list[Any] = None) -> dict[tuple[OrnamentType, BodyPart], list[Ornament]]:
        covered_regions = covered_regions or []
        covered_mask = BodyPart.NONE
        for region in covered_regions:
            if isinstance(region, BodyRegion):
                covered_mask |= region.to_part_mask()
            elif isinstance(region, BodyPart):
                covered_mask |= region
            elif isinstance(region, str):
                resolved_region = BodyRegion._missing_(region)
                if isinstance(resolved_region, BodyRegion):
                    covered_mask |= resolved_region.to_part_mask()
                    continue
                resolved_part = BodyPart._missing_(region)
                if isinstance(resolved_part, BodyPart):
                    covered_mask |= resolved_part

        res = defaultdict(list)
        for ornament in self.collection:
            if covered_mask and bool(ornament.body_part & covered_mask):
                continue
            res[ornament.ornament_type, ornament.body_part].append(ornament)
        return dict(res)

    def add_ornament(self, ornament: Ornament) -> None:
        self.collection.append(ornament)

    def remove_ornament(self, ornament: Ornament) -> None:
        # todo: add a convenience accessor
        if ornament in self.collection:
            self.collection.remove(ornament)

    # def __bool__(self):
    #     return len(self.ornaments) > 0

    def describe_items(self, *, possessive: str = "their") -> list[str]:
        """Return concise ornament phrases suitable for appearance summaries."""
        covered_regions: list[Any] = []
        grouped = self.by_part_type(covered_regions)

        items: list[str] = []
        for (ornament_type, body_part), ornaments in sorted(
            grouped.items(),
            key=lambda item: (item[0][0].name, item[0][1].name),
        ):
            items.append(
                Ornament.describe_mark(
                    ornament_type,
                    [ornament.text for ornament in ornaments],
                    body_part,
                    possessive=possessive,
                )
            )
        return items

    def describe_summary(self, *, possessive: str = "their") -> str:
        """Return a compact joined ornament summary without sentence framing."""
        return oxford_join(self.describe_items(possessive=possessive))

    # @on_render.register()
    def describe(self) -> dict[str, str]:
        summary = self.describe_summary(possessive="their")
        if not summary:
            return {"ornaments": ""}
        return {"ornaments": f"They have {summary}."}

    def __bool__(self) -> bool:
        return len(self.collection) > 0
