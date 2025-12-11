import typing as typ
import random
import attr
from tangl.utils.gender_enum import Gender as G
from tangl.manager import ManagedObject
from tangl.shared import Cost
from .mind import Mind
from .body import Body
from .decomposable import DecomposableMixin
from .person_text import PersonTextMixin


@attr.s(auto_attribs=True)
class Person(Mind, Body, PersonTextMixin, DecomposableMixin, ManagedObject):

    def incr_age(self):
        self.age += 1
        self.mental_age += 1

    @property
    def weeks_until_expiry(self):
        return self.age - 15 * 12
        # Get expiry age from game config, compute distance

    def update_state(self, state):
        self.incr_age()
        # if self.weeks_until_expiry <= 0:
        #     # TODO: Need an event mint for retirements and other scheduled events
        #     retirement = state.event_mint.mint_scheduled("Retirement", self)
        #     state.events.queue.append(retirement)
        # TODO: Check expiry, grow hair, change weight, etc.
        self._update_state(state)

    def communicates(self):
        return self.voice > 30 and self.fluency > 30

    def finalize(self):
        """Call if freshly minted"""
        if self.birth_gender == G.XX:
            self.height = int( self.height * 0.9 )
            self.face_type = int( self.face_type * 0.8 )
            self.has_xx = 50
            self.breasts = random.randint(60, 90)
        elif self.birth_gender == G.XY:
            self.height = int( self.height * 1.1 )
            self.face_type = int( self.face_type * 1.2 )
            self.has_xy = 50
            self.breasts = random.randint(10, 40)
        elif self.birth_gender == G.XXY:
            self.has_xx = 50
            self.has_xy = 50
            self.breasts = random.randint(40, 60)
        self.mental_age = self.age

    # For creating an outfit
    avatar_base: str = None
    avatar_variants: typ.List[str] = None  # ie, [wsword] if bodyguard
    avatar_outfit: str = "underwear"
    avatar_groups: typ.List[str] = None
    avatar_svg: str = None         # SVG for display, recompute whenever avatar props are changed

    # TODO: Need a way to indicate mandatory uniform

    # Which section this chattel is assigned to work in
    assignment: ManagedObject = attr.ib(init=False, default=None)  # Careful or it will recurse section->chattel->section etc

    # This should be based on cash/turn, num turns of value, and depth into the game
    def purchase_price(self, base_price=2000) -> int:

        price = base_price
        for k in ["strength", "mind", "phealth", "mhealth", "fluency", "obedience", "attractiveness"]:
            price += getattr(self, k) * 10

        # For classes with skills
        # for k in self.skills:
        #     price += self.traits[k]

        return price