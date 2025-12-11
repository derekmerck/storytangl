
from __future__ import annotations
from typing import *

from tangl.core import RenderableMixin
if TYPE_CHECKING:  # pragma: no cover
    from old.actor.actor.actor import Actor
else:
    Actor = object

from tangl.story.actor.enums import Gens as G

class ActorDescMixin(RenderableMixin, Actor):

    @property
    def full_name(self):
        if self.surname:
            return f"{self.name} {self.surname}"
        else:
            return self.name

    # Gendered and Titled Address
    # -------------------
    @property
    def gendered_address(self) -> str:
        if self.gens == G.XY:
            return "Mr."
        return "Ms."
    mr = gendered_address
    ms = gendered_address

    def title(self):
        """To represent a gendered title, use _title = ('Queen', 'King') """
        if isinstance( self._title, list ):
            return self.title[0] if not test(self) else self.title[1]
        return self._title

        # if self.assignment and self == self.assignment.boss \
        #         and self.assignment.boss_title:
        #     _title = self.assignment.boss_title
        # elif self.assignment and self in self.assignment.chattel \
        #         and self.assignment.chattel_title:
        #     _title = self.assignment.chattel_title
        # elif self.title:
        #     _title = self.title

    @property
    def titled_name(self) -> str:
        if not self.title():
            return self.name
        return f"{self.title()} {self.name}"

    @property
    def titled_full_name(self) -> str:
        if not self.title():
            return self.full_name
        return f"{self.title()} {self.full_name}"

    def _body_desc(self, use_name: bool = False):

        for attrib in ['skin_color', 'hair_color', 'eye_color', 'wing_palette', 'wing_type']:
            if not hasattr(self, attrib):
                raise TypeError(f"No common body traits on actor {self}")

        s = ""
        s += f"{self.name if use_name else self.She} is {self.female}, " \
             f"with {self.skin_color.lower()} skin, {self.hair_color.lower()} hair, " \
             f"and {self.eye_color.lower()} eyes.  "

        if hasattr(self, "wing_palette") and hasattr(self, "wing_type"):
            s += f"{self.She} has {self.wing_palette.lower()} {self.wing_type.lower()} wings."

        return s

    def desc(self, **kwargs):

        s = self._body_desc(use_name=True)

        if self.ornaments:
            s += "\n" + self.ornaments.desc()

        if self.outfit:
            s += "\n" + self.outfit.desc()

        return s

        # All vars in actor descs are macro'd directly
        # return self._render( s )

