
from __future__ import annotations
import itertools
from typing import *
import random
from enum import Enum, IntEnum

import attr

from tangl.utils.attrs import define
from tangl.utils.enum_utils import EnumUtils
from .basic_game import BasicGame
from .basic_player import BasicPlayer, RuntimeMultiRenderable
from .enums import Result


class TwentyOneMove(EnumUtils, IntEnum):
    NO_MOVE = 0
    STAND = 1
    HIT = 2



@define
class TwentyOnePlayer( BasicPlayer ):

    current_move: TwentyOneMove = attr.ib( converter=TwentyOneMove, default=TwentyOneMove.NO_MOVE )

    hand: dict[Enum, RuntimeMultiRenderable] = attr.ib()
    @hand.default
    def _mk_hand(self):
        res = { TwentyOneMove.HIT:  RuntimeMultiRenderable(uid=TwentyOneMove.HIT,
                                                           text="hit"),
                TwentyOneMove.STAND: RuntimeMultiRenderable(uid=TwentyOneMove.STAND, text="stand") }
        return res

    cards: List[Card] = attr.ib( factory=list )

    @property
    def current_score(self):
        return Card.sum( self.cards )

    # def pick_move(self, game: Game = None, **kwargs):
    #     # this is essentially a solitaire game, opponent has no strategy
    #     self.current_move = TwentyOneMove.NO_MOVE


# todo: need mechanism to make multiple sub-moves per round...

@define
class TwentyOneGame(BasicGame):
    """
    Blackjack-like variant on :class:\`BasicGame\`

    Solitaire card game model

    Get as close as possible to a target score given a randomly dealt hand.
    Considered as single-player game, as dealer/opponent moves are deterministic.
    """

    _move_typ = TwentyOneMove

    player: TwentyOnePlayer = attr.ib( factory=TwentyOnePlayer )
    opponent: TwentyOnePlayer = attr.ib( factory=TwentyOnePlayer )
    deck: List[Card] = attr.ib( factory=Card.fresh_deck )

    def reset(self):
        super().reset()
        self.player.cards = list()
        self.opponent.cards = list()

        deck_field = attr.fields_dict(self.__class__)['deck']
        self.deck = deck_field.default.factory()

        self.player.cards.append( self.deck.pop() )
        self.player.cards.append( self.deck.pop() )
        self.opponent.cards.append( self.deck.pop() )
        self.opponent.cards.append( self.deck.pop() )

    @property
    def game_status(self) -> Result:

        # Game is over
        if self.player.current_score > 21:      # pl bust
            return Result.LOSE
        elif self.player.current_score == 21:   # pl perfect
            return Result.WIN
        elif TwentyOneMove.STAND not in [ move[0] for move in self.player.history ]:
            # Game not over yet
            return Result.CONT
        elif self.opponent.current_score > 21:  # deal bust
            return Result.WIN
        else:
            # No one is bust
            if self.player.current_score > self.opponent.current_score:
                return Result.WIN
            elif self.player.current_score < self.opponent.current_score:
                return Result.LOSE
            else:
                return Result.DRAW

    def _compute_round_result(self):
        if self.player.current_move is TwentyOneMove.HIT:
            self.player.cards.append(self.deck.pop())
        elif self.player.current_move is TwentyOneMove.STAND:
            while self.opponent.current_score <= 16:
                self.opponent.cards.append( self.deck.pop() )
        self.player.history.append( (self.player.current_move, self.player.current_score) )

    def text(self, **kwargs) -> str:

        s = ""
        print(f"ROUND {self.round} -------------------")

        if self.player.current_move is TwentyOneMove.NO_MOVE:
            s +=  f"You are dealt {' '.join([str(c) for c in self.player.cards])} (total: {self.player.current_score}) \n"
            s += f"Dealer shows {self.opponent.cards[0]} (+{self.opponent.cards[1]} total: {self.opponent.current_score})"
        elif self.game_status is Result.CONT:
            s += f"You get a {self.player.cards[-1]} (total: {self.player.current_score})"
        else:
            s += f"Dealer shows {self.opponent.cards[1]}"
            if len( self.opponent.cards ) > 2:
                s += f" and takes {' '.join([str(c) for c in self.opponent.cards[2:]])}"
            s += f" (total: {self.opponent.current_score})\n{self.game_status}"
        return s


