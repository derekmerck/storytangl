
from __future__ import annotations

import collections
from typing import *
from enum import IntEnum
import itertools
import random

import attr

from tangl.utils.attrs import define
from tangl.story import StoryNode
from .basic_game import BasicGame
from .twentyone import Card, TwentyOnePlayer

from .twentyone import TwentyOneMove as Move
from .enums import Result

class MndCard:
    """mn-dimensional card with m-values and n-types"""

    def __init__(self, values: list[int], types: list):
        self.values = values
        self.types = types

    @classmethod
    def fresh_deck(cls, values: list[list|int], types: list[list|int], shuffle=False):
        """
        val1 = 1:3
        val2 = -1:-3
        type1 = [a,b]
        type2 = [d,e]

        fresh_deck( [3,-3], [ [a,b], [d,e] ] )
        """

        def _cast_int_to_range(val):
            if isinstance( val, int ) and val > 0:
                return list(range( 1, val+1 ))
            elif isinstance( val, int ) and val < 0:
                return list(range( -1, val-1, -1 ))
            return val

        values_ = []
        for m in values:
            values_.append(_cast_int_to_range( m ))
        values_ = itertools.product( *values_ )
        types_ = []
        for n in types:
            types_.append(_cast_int_to_range( n ))
        types_ = itertools.product( *types_ )

        cards = [cls(v, s) for v, s in itertools.product(values_, types_)]

        if shuffle:
            random.shuffle( cards )
        return cards

    @classmethod
    def sum(cls, cards: List ) -> list[int]:
        _sum = [0] * len( cards[0].values )
        for c in cards:
            for i, v in enumerate( c.values ):
                _sum[i] += v
        return _sum

    def __str__(self):
        return f"{self.types}:{self.values}"

    def __repr__(self):
        return f"{self.types}:{self.values}"


@define
class TwentyTwoGame(BasicGame):
    """
    Multi-dimensional variant on :class:\`TwentyOneGame\`

    Beat win target score while staying under lose target score in x turns,
    given various moves with +/- values, interesting when adding dynamic rules
    like no b's until take an a, or c's count 2x.

    Like 21, primarily a single-player/solitaire game

    Can be used as a framework for "raise a value while keeping a value below x
    given a set of available plays"
    """

    player: TwentyOnePlayer = attr.ib( factory=TwentyOnePlayer )
    opponent: TwentyOnePlayer = attr.ib( factory=TwentyOnePlayer )

    win_target: int = 22
    lose_target: int = 22

    cards: MndCard = attr.ib()
    @cards.default
    def _mk_cards(self):
        cards = MndCard.fresh_deck( [-3, 3], [['a', 'b', 'c']])
        random.shuffle( cards )
        return cards

    @property
    def game_status(self) -> Result:

        win, lose = self.player.current_score
        owin, olose = self.opponent.current_score

        if win >= self.win_target:
            return Result.WIN
        elif lose >= self.lose_target:
            return Result.LOSE
        elif Move.STAND not in [ move[0] for move in self.player.history ]:
            # Game not over yet
            return Result.CONT
        elif olose > self.lose_target:  # deal bust
            return Result.WIN
        else:
            # No one is bust, see who has the better 'win' score...
            if win > owin:
                return Result.WIN
            elif owin < owin:
                return Result.LOSE
            else:
                return Result.DRAW

    def _compute_round_result(self):

        if self.player.current_move is Move.HIT:
            self.player.cards.append(self.deck.pop())
        elif self.player.current_move is Move.STAND:
            while max( self.opponent.current_score ) <= 22:
                self.opponent.cards.append( self.deck.pop() )
        self.player.history.append( (self.player.current_move, self.player.current_score) )

    def text(self, **kwargs) -> str:

        s = ""
        print(f"ROUND {self.round} -------------------")

        if self.player.current_move is Move.NO_MOVE:
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
