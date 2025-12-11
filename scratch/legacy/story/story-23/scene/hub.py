# Hubs are persistent scenes that can include assets and referred actions

from typing import *

import attr

from tangl.31.entity import Condition
from tangl.31.entity.entity import as_eid
from tangl.31.asset import AssetWallet
from tangl.31.asset.chattel import ActorStock
from tangl.31.actor import Role, Actor
from .action import ReferredAction
from .block import Block
from .scene import Scene


@attr.define(slots=False, init=False, eq=False, hash=False)
class HubBlock(Block):

    show_boss: bool = False
    show_chattel: bool = False
    show_assets: bool = False

    boss_actions: List[ReferredAction] = attr.ib(factory=list)
    chattel_actions: List[ReferredAction] = attr.ib(factory=list)
    asset_actions: List[ReferredAction] = attr.ib(factory=list)

    # todo: this only renders chattel, ie, actor assets
    #       maybe easiest is to use "show_assets" as a nominal, "boss", "goods",
    #       "chattel", "upgrades" and use a different block for each asset class
    def render(self, **kwargs) -> Dict:
        res = super().render(**kwargs)
        if self.show_chattel:
            assets_ = []
            for i, asset in enumerate( self.parent.chattel ):
                asset_ = asset.render()
                r_acs = []
                for ac in self.chattel_actions:
                    r_acs.append( ac.render(referent=asset) )
                if r_acs:
                    asset_['actions'] = r_acs
                if asset_:
                    assets_.append(asset_)
            res['chattel'] = assets_
        return res


HubBlock.__init_entity_subclass__()

GoodsStock = object

@attr.define(slots=False, init=False, eq=False, hash=False)
class Hub(Scene):

    scene_typ: str = "hub"
    blocks: Dict[str, HubBlock] = attr.ib(factory=dict, metadata={"state": True})

    # mutable, do not assign directly, get from role or assignment
    boss: Actor = attr.ib(default=None, metadata={"state": True})
    boss_role: Optional[Role] = attr.ib(default=None)
    boss_reqs: List[Condition] = attr.ib( factory=list )
    boss_title: str = None

    # mutable, do not assign directly, get from role, assignment, or restock
    chattel: List[Actor] = attr.ib(factory=list, repr=as_eid, metadata={"state": True})
    chattel_reqs: List[Condition] = attr.ib( factory=list )
    chattel_roles: List[Role] = attr.ib(factory=list)
    chattel_stock: List[ActorStock] = attr.ib(factory=list)
    chattel_title: str = None
    restock_chattel: bool = False

    assets: AssetWallet = attr.ib(factory=AssetWallet, metadata={"state": True})
    asset_stock: Optional[Dict] = None
    restock_assets: bool = False

    goods_stock: List[GoodsStock] = attr.ib(factory=list)
    restock_goods: bool = False

    def ns(self) -> dict:
        _ns = super().ns( )
        _ns |= {
            'chattel': self.chattel,
            'c': self.chattel,
            'boss': self.boss,
            'b': self.boss,
            'assets': self.assets,
        }
        return _ns

    def __attrs_post_init__(self):

        if self.boss_role and isinstance(self.boss_role, dict):
            self.boss_role = Role( uid="ro_boss", **self.boss_role,
                                   parent=self, factory=self.factory,
                                   ctx=self.ctx )
        super().__attrs_post_init__()

    def __init_entity__(self, **kwargs):

        for r in self.chattel_roles:
            r.cast(**kwargs)
            if r.actor:
                self.chattel.append( r.actor )
            else:
                raise RuntimeError(f"Failed to cast {r}")
        self.chattel_roles = []

        if self.boss_role:
            self.boss_role.cast()
            if self.boss_role.actor:
                self.boss = self.boss_role.actor
            else:
                raise RuntimeError(f"Failed to cast {self.boss_role}")
        self.boss_role = None

        self.restock()

        super().__init_entity__(**kwargs)

    def restock(self, clear=False):

        res = []
        if self.restock_chattel and self.chattel_stock:
            for stk in self.chattel_stock:
                if hasattr(stk, "restock"):
                    res += stk.restock()  # generate a random number of actors
                else:
                    print("Failed to restock incompletely initialized stock")
                    print( self.chattel_stock )
        if clear:
            self.chattel = res
        else:
            self.chattel += res

        if self.restock_assets:
            raise NotImplementedError

    def assign(self, a: Actor, role: str = None):
        if role is None:
            if a is not None and a not in self.chattel:
                self.chattel.append( a )
        elif role == "boss":
            self.boss = a

    def unassign(self, a: Actor):
        if a in self.chattel:
            self.chattel.remove( a )
        elif self.boss == a:
            self.boss = None

    def __done__(self):
        self.restock()

Hub.__init_entity_subclass__()
