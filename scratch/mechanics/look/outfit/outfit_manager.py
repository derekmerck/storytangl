from __future__ import annotations

from pydantic import BaseModel

from tangl.core import Entity
from ..wearable import Wearable


class OutfitManager():

    def __init__(self, node: HasOutfit):
        self.node = node

    def can_wear(self, item):
        ...

    def wear(self, item):
        ...

    def can_open(self, item):
        ...

    def open(self, item):
        ...

    def can_tear(self, item):
        ...

    def tear(self, item):
        ...

    def can_remove(self, item):
        ...

    def remove(self, item):
        ...

    def is_exposed(self, body_part):
        ...

    def expose(self, body_part):
        # Open or remove the top-most layer covering X
        ...

    def is_covered(self, body_part):
        ...

    def cover(self, body_part):
        # Put on or close the bottom-most layer covering X
        ...

    def describe(self) -> str:
        ...


class HasOutfit(Entity):

    @property
    def wearables(self) -> list[Wearable]:
        return self.find_children(Wearable)

    @property
    def outfit(self):
        # accessor for expressions like `actor.outfit.wear(item)`
        return OutfitManager(self)

    @on_render.strategy
    def render(self):
        return {'outfit': self.outfit.describe()}
