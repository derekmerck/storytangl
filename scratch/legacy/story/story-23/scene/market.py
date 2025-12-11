"""
Markets are objects not under direct player control
- unlocked workers may be collected here for costs
- unlocked policies may be set, leading to effects
  (typically, affecting the market itself)
- markets may have multiple levels, unlocked based
  on conditions, only the max level is used
"""

import typing as typ
import random
import attr
from tangl.manager import ManagedObject
from tangl.person import Person
from tangl.shared import StateConditions, Effects
from tangl.policy import Policies
from tangl.utils import render_templ



@attr.s(auto_attribs=True)
class MarketUpgrade(ManagedObject):

    desc: str = None
    conditions: StateConditions = attr.ib(converter=StateConditions, factory=list)
    effects: Effects = attr.ib(converter=Effects, factory=list)
    policies: Policies = attr.ib(converter=Policies, factory=list)

    # minted based on template, held over, or boomeranged
    chattel: typ.List[typ.Dict] = attr.Factory(list)
    menials: typ.Dict = attr.Factory(dict)


def mk_upgrades(level_items: typ.List) -> typ.List[MarketUpgrade]:
    result = []
    for item in level_items:
        upgrade = MarketUpgrade(**item)
        result.append( upgrade )
    return result


@attr.s(auto_attribs=True)
class Market(ManagedObject):

    name: str = None
    icon: str = None
    desc: str = None  # Base desc

    # Should be init=False, maybe add a repr so it is exported?
    relationship: int = attr.ib(default=0)
    cur_level: int = attr.ib(default=0)

    policies: Policies = attr.ib(converter=Policies, factory=list)
    upgrades: typ.List[MarketUpgrade] = attr.ib(converter=mk_upgrades, factory=list)

    chattel_avail: typ.List[Person] = attr.Factory(list)
    menials_avail: typ.Dict = attr.Factory(dict)

    def refresh(self):
        # TODO: should check conditions and set the cur_level

        self.chattel_avail = []
        chattel_stock = self.upgrades[self.cur_level].chattel
        from tangl.chattel import get_chattel_mint
        with get_chattel_mint() as g:
            for item in chattel_stock:
                phenotype_args = item.get("phenotype", {})
                count_range = item.get("count")
                count = random.randint(count_range[0], count_range[1])
                for c in range(count):
                    p = g.mint(**phenotype_args)
                    self.chattel_avail.append(p)
        # TODO: Have to add to the chattel stock so they can be retrieved
        #       or force the api to always use market + uid until bought
        #       Add to chattle, then remove any until refresh, flag a couple
        #       with "repeat"

    def update_state(self, state):
        print("Calling mkt update")
        self.refresh()          # Should be refresh_stock?
        if self.policies:
            self.policies.update_state(state)
        self._update_state(state)

    # TODO: No purchase costs
    def purchase_chattel(self, which):
        c = self.chattel_avail[which]
        # if c.purchase_price().can_pay():
        #     c.purchase_price().pay(), etc.
        self.chattel_avail.remove(c)
        # self.upgrades[self.cur_level].effects.invoke()  # Trigger all on-purchase instants
        from tangl.state import get_state
        with get_state() as g:
            g.chattel.push_new(c)  # Add to the review and assign queue

    # TODO: No purchase cost
    # def purchase_menials(self, which: str, number: int):
    #     if which in self.menials_avail and self.menials_avail[which] > number:
    #             self.menials_avail[which] -= number
    #             with get_game() as g:
    #                 g.player.menials[which] += number

    def cur_desc(self):
        s  = self.desc
        s += self.upgrades[self.cur_level].desc
        from tangl.state import get_state
        with get_state() as g:
            desc = render_templ(s,
                                player=g.player.data,
                                market=self.as_dict())
            return desc