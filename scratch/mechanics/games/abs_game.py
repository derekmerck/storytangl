import abc
import typing as typ
from enum import IntEnum
import random

import attr


@attr.define
class Payout(object):
    data: typ.List[typ.List] = None

    def get(self, player: int, opponent: int) -> int:
        # Get outcome from pairing
        if player == -1 or opponent == -2:  # player force win or opponent force loss
            return max(self.data[player])   # max score this player could get
        if player == -2 or opponent == -1:  # player force loss or opponent force win
            return min(self.data[player])   # min score this player could get
        # both unbeatable or both losses, draw goes to min's for both (I think)
        return self.data[player][opponent]

    def wins_against(self, move: int) -> typ.List[int]:
        # Find a winning strategy against a move
        candidates = [i[move] for i in self.data]  # get the column
        best_outcome = max(candidates)
        winners = [candidates.index(v) for v in candidates if v == best_outcome]
        return [v for v in winners]

    def loses_against(self, move: int) -> typ.List[int]:
        # Find a winning strategy against a move
        candidates = [i[move] for i in self.data]  # get the column
        best_outcome = min(candidates)
        winners = [candidates.index(v) for v in candidates if v == best_outcome]
        return [v for v in winners]


class Strategy(object):

    @classmethod
    def random(cls, caller: 'GamePlayer', game: 'AbstractGame'):
        if caller.allowed_moves:
            candidates = caller.allowed_moves
        else:
            candidates = list(game.moves)[:len(game.payout.data)]
        return random.choice(candidates)

    @classmethod
    def insight(cls, caller: 'GamePlayer', game: 'AbstractGame', win=True):
        if game.player1 == caller:
            opponent = game.player2
        else:
            opponent = game.player1
        op_move = opponent.peek_move(game)
        if win:
            candidates = game.payout.wins_against(op_move)
        else:
            candidates = game.payout.loses_against(op_move)
        random.shuffle(candidates)
        move = candidates.pop()
        return move


@attr.define
class GamePlayer(object):

    allowed_moves: typ.List[int] = None
    strategy: typ.Callable = Strategy.random

    _move: typ.Optional[IntEnum] = attr.ib(default=None, init=False)
    def peek_move(self, game: 'AbstractGame'):
        # if opponent is using insight, stash the likely guess
        # warning! this will infinitely recurse if both players use insight
        self._move = self.strategy( self, game )
        return self._move

    def make_move(self, game: 'AbstractGame'):
        if self._move is not None:
            res = self._move
            self._move = None
        else:
            res = self.strategy( self, game )

        return game.moves( res )


@attr.define(eq=False, hash=False, init=False, slots=False)
# @attr.define
class AbstractGame_(abc.ABC):
    """
    Basic usage:
    ch = MyGame( RPS_PAYOUT, RPS_MOVES )
    ch.p1.set_move( 0 )
    ch.p2.set_move( 1 )
    """

    # Core attributes
    payout: Payout = None
    moves: typ.Type[IntEnum] = attr.ib(default=IntEnum, repr=False)
    player1: 'GamePlayer' = attr.ib(factory=GamePlayer)
    player2: 'GamePlayer' = attr.ib(factory=GamePlayer)

    # Administration
    score: typ.List = [0, 0]
    wins_at: typ.List = [3, 3]
    draw_at: int = 7
    draw_goes_to: int = -1

    history: typ.List = attr.ib(init=False, factory=list)

    def reset(self):
        self.score = [0, 0]
        self.history = []

    @property
    def round(self):
        return len(self.history)

    round_winner: int = -1

    def has_winner(self, *args, **kwargs):
        # -1 = draw
        #  0 = no winner
        #  1 = p1
        #  2 = p2
        if self.score[0] >= self.wins_at[0]:
            return 1
        elif self.score[1] >= self.wins_at[1]:
            return 2
        elif self.round > self.draw_at:
            return self.draw_goes_to
        else:
            return 0

    def do_round(self, *args, **kwargs) -> int:
        p1 = self.player1.make_move(self)
        p2 = self.player2.make_move(self)

        p1_payout = self.payout.get(p1, p2)
        p2_payout = self.payout.get(p2, p1)

        self.score[0] += p1_payout
        self.score[1] += p2_payout

        if p1_payout > p2_payout:
            self.round_winner = 1
        elif p2_payout > p1_payout:
            self.round_winner = 2
        else:
            self.round_winner = -1

        self.history.append( (p1, p2) )
        return self.has_winner()
