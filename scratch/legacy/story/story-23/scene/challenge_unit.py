from typing import *

import attr

from tangl.31.entity import Renderable_, Entity
# from tangl.31.entity.structure import structure_as
from tangl.31.asset.unit import Unit, UnitGroup
from tangl.31.game.bag_rps import BagRpsGame_, BagRpsPlayer
from .action import Action
from .block import Block
from .challenge import Challenge, SubmitAction


@attr.define( slots=False, eq=False, hash=False )
class UnitCommitAction(SubmitAction):

    def _label(self, **kwargs):
        return "Commit!"

    def callback(self, **kwargs):
        """Assumes passed-back kwargs are new commitment levels"""
        pl_commitment = UnitGroup(kwargs)
        self.parent: UnitChallenge
        self.parent.player1._move = pl_commitment
        self.parent.update()


# Action.variants['UnitCommitAction'] = UnitCommitAction


@attr.define( slots=False, eq=False, hash=False )
class UnitChallengePlayer(BagRpsPlayer, Entity):

    # forces: UnitGroup = attr.ib(default=None,
    #                             converter=UnitGroup)

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        # cast to proper form
        self.forces = UnitGroup( self.forces )
        self.reserve = UnitGroup( self.reserve )
        self.committed = UnitGroup( self.committed )
        self.defeated = UnitGroup( self.defeated )

    def __entity_init__(self, **kwargs):
        # every world has its own unit registry
        self.forces.item_cls = self.ctx.world.units
        self.reserve.item_cls = self.ctx.world.units
        self.committed.item_cls = self.ctx.world.units
        self.defeated.item_cls = self.ctx.world.units


# structure_as doesn't work here b/c we have to cast from a dict directly to
# a class, not to a dict full of instances
def mk_player(data: Dict):
    return UnitChallengePlayer( **data )


@attr.define( init=False, eq=False, slots=False, hash=False )
class UnitChallenge(BagRpsGame_, Challenge):

    player1: UnitChallengePlayer = attr.ib(default=None, converter=mk_player)
    player2: UnitChallengePlayer = attr.ib(default=None, converter=mk_player)

    unit_types: List[Unit] = attr.ib(factory=list, metadata={'init': 'ignore'})

    def __entity_init__(self, **kwargs):
        super().__entity_init__(**kwargs)
        # register extra unit types to register with the world index
        # pointless to redo this in the game itself rather than in the world init
        # fix later...
        for ut in self.unit_types:
            # print( f"registering unit: {ut.uid}" )
            self.ctx.world.units._instances[ut.uid] = ut

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        commit = UnitCommitAction(parent=self)
        self.actions.append(commit)

        # debug, magic block names
        win = Action(label="Force win", next="win", parent=self,
                     ctx=self.ctx, factory=self.factory)
        lose = Action(label="Force loss", next="lose", parent=self,
                      ctx=self.ctx, factory=self.factory)
        self.actions += [win, lose]

    def update(self, *args, **kwargs) -> int:
        BagRpsGame_.do_round(self, *args, **kwargs)

    def render(self, **kwargs):
        r = super().render(**kwargs)

        r["units"] = {}
        for k in self.player1.forces.keys():
            r["units"][k] = {
                # "info": self.ctx.world.units.instance(k).render(),
                "reserve": self.player1.reserve[k],
                "committed": self.player1.committed[k],
                "defeated": self.player1.defeated[k],
                "to_commit": 0
            }

        # from pprint import pprint
        # pprint(r)

        __init__ = Entity.__init__

        return r


UnitChallenge.__init_entity_subclass__()
