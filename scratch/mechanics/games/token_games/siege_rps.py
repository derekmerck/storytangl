"""
# Attacker/Defender Game Scenario

Defender commits units (num, type)
  - creates a posture + total pow, rock=dig in, iron=draw out, glass=flank
  - signal: type, number

Attacker selects units (num, type)
  - creates a posture + total pow, rock=assault, iron=draw out, glass=lightning

resolution - payout * total pow decimates opponent forces, payouts = 1, 0.5, 0.2

defender reinforces
  - may change posture
  - change effective pow
  - signal: type, number

attacker reinforces
  - may change posture
  - change effective pow

resolution - payout * total pow decimates opponent forces

continues until time limit or one player has no units left

upgrades include better signals, force multipliers, leader units w adaptive types
"""

from __future__ import annotations
import numbers
import collections
from typing import *
import random
import math
from enum import Enum
from numbers import Number

import attr

from tangl.utils.attrs import define
from tangl.story import StoryNode
from tangl.story.asset.token import Token, TokenBag
from tangl.utils.enum_utils import EnumUtils
from .basic_game import BasicGame
from .enums import Result
from .basic_player import BasicMove, BasicPlayer, RuntimeMultiRenderable


@define
class SiegeUnit(Token):

    last_down: bool = False  # Heroes are always last down in bag

    @classmethod
    def load_inline(cls, units: list[dict]):
        if not units:
            return
        for kwargs in units:
            SiegeUnit(**kwargs)


class SiegeSquad(TokenBag):

    def __init__(self,
                 *args,
                 wallet_typ = SiegeUnit,
                 **kwargs):
        super().__init__(*args, wallet_typ=wallet_typ, **kwargs)

    def decimate(self, damage: numbers.Number) -> collections.Counter:
        reduced_power = self.power - damage
        res = self.__class__()
        if reduced_power < 0:
            return +self
        while self.power > reduced_power:
            print(list(self.elements()))
            key = random.choice( list(self.elements()) )
            # todo: if item is last down and other items exist, try again
            # todo, if you are going to go negative, [6->-2] then
            #    you have a 2/8 chance to save unit and break
            self[key] -= 1
            res[key] += 1
        return res


class SiegeMove(EnumUtils, Enum):
    NO_MOVE = "no_move"
    COMMIT = "commit"
    WITHDRAW = "withdraw"

    def __int__(self):
        map = {
            SiegeMove.NO_MOVE: -1,
            SiegeMove.COMMIT: 1,
            SiegeMove.WITHDRAW: -2
        }
        return map[self]


@define
class SiegePlayer(BasicPlayer):

    current_move: SiegeMove = attr.ib(converter=SiegeMove, default=SiegeMove.NO_MOVE)

    def make_move(self, move: SiegeMove, game: SiegeGame, commitment: SiegeSquad = None, **kwargs):
        if not commitment:
            return
        try:
            self.reserve -= commitment
            assert self.reserve == +self.reserve  # No negative values
            self.committed += commitment
        except (ValueError, AssertionError) as e:
            raise "Failed to commit units"
        # else:
        #     _committing = self.strategy( self.reserve )
        #     self.committed += _committing
        #     self.reserve = -_committing

    # this is the starting force for reference
    forces: SiegeSquad = attr.ib(default=None, converter=SiegeSquad)
    reserve: SiegeSquad = attr.ib(factory=SiegeSquad, init=False)
    committed: SiegeSquad = attr.ib(factory=SiegeSquad, init=False)
    down: SiegeSquad = attr.ib(factory=SiegeSquad, init=False)

    def reset(self):
        super().reset()
        self.reserve = +self.forces
        self.committed = SiegeSquad()
        self.down = SiegeSquad()

    @property
    def current_posture(self) -> Tuple[ Number, Enum ]:
        return self.active.power(), self.active.alignment()

    hand: dict[SiegeMove, RuntimeMultiRenderable] = attr.ib( converter=SiegeMove.typed_keys )
    @hand.default
    def _mk_hand(self):
        res = {SiegeMove.COMMIT: RuntimeMultiRenderable(uid=SiegeMove.COMMIT, descs=["commit"])}
        return res


@define
class SiegeGame(BasicGame):
    """Rock-paper-scissors variant on :class:\`BasicGame\`"""

    # before anything else, this is empty, it just instructs attrs to
    # load the field and init new assets if required
    unit_types: List[SiegeUnit] = attr.ib(default=None)

    player: SiegePlayer = attr.ib(factory=SiegePlayer)
    opponent: SiegePlayer = attr.ib(factory=SiegePlayer)

    @property
    def game_status(self) -> Result:
        if len( self.player.committed + self.player.reserve ) <= 0:
            return Result.LOSE
        elif len( self.opponent.committed + self.opponent.reserve ) <= 0:
            return Result.WIN
        return Result.CONT

    payout: ClassVar[list[list[Number]]] = [ [ 1, 2, 0 ],
                                             [ 0, 1, 2 ],
                                             [ 2, 0, 1 ] ]

    # 4x, 1x, 1/4x
    graded_payout: ClassVar[list[list[Number]]] = [
        [1,    4,    0.25],
        [0.25, 1,    4],
        [4,    0.25, 4]
    ]

    def _compute_result(self):
        # Lookup the weights for each force relative to the other
        player_impact = self.payout[ self.player.current_posture[1] ][ self.opponent.current_posture[1] ]
        opponent_impact = self.payout[ self.opponent.current_posture[1] ][ self.player.current_posture[1] ]

        # Compute the weighted power for each
        player_weighted_pow   = self.player.current_posture[0] * float(player_impact)
        opponent_weighted_pow = self.opponent.current_posture[0] * float(opponent_impact)

        # Decimate player active forces
        pr_down = self.player.active.decimate( opponent_weighted_pow )
        self.player.down += pr_down
        self.player.history.append( player_weighted_pow, pr_down )

        # Decimate opponent active forces
        or_down = self.opponent.active.decimate( player_weighted_pow )
        self.opponent.down += or_down
        self.opponent.history.append( opponent_weighted_pow, or_down )

        if player_weighted_pow > opponent_weighted_pow:
            return Result.WIN
        return Result.LOSE

    def _round_desc(self):
        s = ""
        if self.game_status == Result.CONT:
            if self.opponent.down.total() > self.player.down.total():
                s = "Your forces are dominant."
            else:
                s = "Your forces are being beaten back."

        # s += f"The player looses {self.player.history[-1][1].__repr__}"
        # s += f"The opponent looses {self.opponent.history[-1][1].__repr__}"

        return s

    def _status_desc(self) -> str:
        s = ""
        if self.game_status != Result.CONT:
            if self.rounds < 3:
                s += "The conflict is short and one-sided, and finally "
            elif self.game_status != Result.CONT and self.rounds:
                s += "The conflict is long and challenging, but finally "
            if self.status == Result.WIN:
                s += "your forces prevail."
            else:
                s += "your forces are defeated."

        s += f"Total losses for the player are {self.player.down}\n"
        s += f"Total losses for the opponent are {self.opponent.down}\n"
        return s

    def desc(self, **kwargs) -> str:

        s = ""
        s += self._status_desc() + "\n"
        s += self._round_desc() + "\n"

        res = self._render( s, **( self.ns() | kwargs ) )
        return res

# class SiegeStrategy(Strategy):
#
#     @classmethod
#     def commit_half(cls, bag: Squad) -> Squad:
#         return bag // 2  # half of remaining
#
#     @classmethod
#     def all_in(cls, bag: Squad) -> Squad:
#         print("Going all in")
#         return bag

