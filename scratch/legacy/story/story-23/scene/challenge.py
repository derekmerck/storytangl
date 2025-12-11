# Challenges are complex blocks that include callback actions and logic

from typing import *
import attr

from tangl.31.entity import Entity, Renderable_, Conditional_
from tangl.31.entity.renderable import PolyRenderable_
from tangl.31.game import AbstractGame_, GamePlayer, RpsGame_, RpsMove
from .block import Block
from .action import Action


@attr.define(init=False, eq=False, hash=False, slots=False)
class SubmitAction(Action):

    # Override or hook this to create complex passbacks
    def callback(self, **kwargs):
        pass

    def apply(self, **kwargs):
        super().apply(**kwargs)
        self.callback(**kwargs)

    def deref(self) -> 'Traversable':
        self.parent: 'Challenge'
        return self.parent

    def avail(self, **kwargs):
        self.parent: RpsChallenge
        return not self.parent.has_winner() and super().avail()


SubmitAction.__init_entity_subclass__()

@attr.define( slots=False, hash=False, eq=False, init=False )
class PolyRenderable_(PolyRenderable_, Conditional_, Entity):
    ...


# challenge state data is not currently saved in flatten
@attr.define( slots=False, hash=False, eq=False, init=False )
class Challenge(AbstractGame_, Block):

    game_typ: str = attr.ib(default=None)

    results: Dict[str, PolyRenderable_] = attr.ib(factory=dict)

    def update(self, **kwargs):
        super().do_round(**kwargs)

    def ns(self) -> dict:
        _ns = super().ns( )
        _ns |= {
            'has_winner': self.has_winner,
            'round': self.round,
            'reset': self.reset,
            'player1': self.player1,
            'player2': self.player2
        }
        return _ns


Challenge.__init_entity_subclass__()


@attr.define(slots=False, hash=False, eq=False, init=False)
class RpsChallengeAction(SubmitAction):

    move: RpsMove = attr.ib( default=None, converter=RpsMove )

    def _icon(self) -> Optional[str]:
        res = super()._icon()
        if not res:
            # check for a world icon
            res_ = "{{" + f"ICON.{ self.move.name}" + "}}"
            res = self._render( res_ )
        if res:
            return res

    def callback(self, **kwargs):
        # a challenge action may include parameters
        self.parent: RpsChallenge
        self.parent.player1._move = self.move
        self.parent.update()


RpsChallengeAction.__init_entity_subclass__()


def keys2moves( d: dict ):
    return { RpsMove(k): v for k, v in d.items() }


@attr.define( slots=False, hash=False, eq=False, init=False )
class RpsChallenge(RpsGame_, Challenge):

    player_moves: Dict[RpsMove, PolyRenderable_] = attr.ib(factory=dict, converter=keys2moves)
    opponent_moves: Dict[RpsMove, PolyRenderable_] = attr.ib(factory=dict, converter=keys2moves)

    def _desc(self) -> Optional[str]:

        _desc = ""
        _desc += f"-> The game state is: {self.score} of {self.wins_at}\n\n"
        _desc += f"-> Winner: {self.has_winner()}\n\n"

        if self.history:
            mv = self.history[-1][0]  # most recent player move
            _desc += f"-> You do move: {mv} \n\n"
            pl = self.player_moves[mv]
            _resp = pl._desc()
            _desc += f"{_resp}\n\n"

            mv = self.history[-1][1]  # most recent opponent move
            _desc += f"-> Op did move: {mv}\n\n"

            # Round results
            resp = None
            if self.round_winner == 1 and 'player_won_round' in self.results:
                resp = self.results['player_won_round']
            elif 'player_lost_round' in self.results:
                resp = self.results['player_lost_round']
            if resp:
                _resp = resp._desc()
                _desc += f"-> Turn outcome: {self.round_winner}\n\n"
                _desc += f"{_resp}\n\n"

        # todo: change this to "player winning" and "player losing"?

        # if "player_score" in self.results:
        #     # compute where players are in their targets
        #     p_score_frac = int( self.score[0] / (len( self.results['player_score'].descs ) + 1))
        #     if p_score_frac < 0 or p_score_frac >= len( self.results['player_score'].descs ):
        #         raise IndexError( f"psf: {p_score_frac} of {len( self.results['player_score'].descs ) }")
        #     p_score_desc = self.results['player_score'].descs[int(p_score_frac)]
        #     _desc += f"{p_score_desc}\n\n"

        # if "op_score" in self.results:
        #     op_score_frac = int( self.score[1] / (len( self.results['opponent_score'].descs ) + 1))
        #     if op_score_frac < 0 or op_score_frac >= len( self.results['opponent_score'].descs ):
        #         raise IndexError( f"opsf: {op_score_frac} of {len( self.results['opponent_score'].descs ) }")
        #     op_score_desc = self.results['opponent_score'].descs[int(op_score_frac)]
        #     _desc += f"{op_score_desc}\n\n"

        if not self.has_winner():
            # print("------------MOVES-----------")
            # print( self.player_moves )
            # print( self.opponent_moves )
            # print("-----------/MOVES-----------")

            mv_ = self.player2.peek_move(self)
            _desc += f"Opponent telegraphs: {mv_}\n\n"
            mv = self.opponent_moves[mv_]
            _desc += mv._desc() + "\n\n"
            _desc += "What do you want to do?\n"

        # res = Renderable._render( _desc )
        return _desc

    __hash__ = Entity.__hash__
    __eq__ = Entity.__eq__
    __init__ = Entity.__init__

    def __attrs_post_init__(self):

        # # todo: hack to convert dict str keys to move-type keys (converter?)
        # res = {}
        # for k, v in self.player_moves.items():
        #     res[RpsMove(k)] = v
        # self.player_moves = res
        # res = {}
        # for k, v in self.opponent_moves.items():
        #     res[RpsMove(k)] = v
        # self.opponent_moves = res

        # Set restrictions
        pl_moves = list( self.player_moves.keys() )
        self.player1.allowed_moves = pl_moves
        op_moves = list( self.opponent_moves.keys() )
        self.player2.allowed_moves = op_moves

        # Create actions
        for move_typ, move_info in self.player_moves.items():
            # print(move_info)
            ac = RpsChallengeAction(
                label = move_info.label,
                icon = move_info.icon,
                move = move_typ,
                parent = self,
                conditions = move_info.conditions,
                factory=self.factory,
                ctx=self.ctx,
            )
            self.actions.append(ac)

        super().__attrs_post_init__()

RpsChallenge.__init_entity_subclass__()
