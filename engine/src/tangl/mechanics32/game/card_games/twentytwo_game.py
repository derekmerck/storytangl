from __future__ import annotations
from typing import List, Union, Tuple
import itertools
import random
from enum import Enum

from pydantic import Field

from tangl.mechanics.game.game_handler import GameHandler, Game, GameResult
from .card_game import CardGame

class MndCard:
    """mn-dimensional card with m-values and n-types"""

    def __init__(self, values: List[int], types: List[str]):
        self.values = values
        self.types = types

    @classmethod
    def fresh_deck(cls, values: List[Union[int, List[int]]], types: List[Union[int, List[str]]], shuffle: bool = False):
        """
        Generate a fresh deck of mn-dimensional cards.
        """
        def _cast_int_to_range(val):
            if isinstance(val, int) and val > 0:
                return list(range(1, val + 1))
            elif isinstance(val, int) and val < 0:
                return list(range(-1, val - 1, -1))
            return val

        values_ = [_cast_int_to_range(m) for m in values]
        types_ = [_cast_int_to_range(n) for n in types]

        cards = [cls(v, t) for v, t in itertools.product(itertools.product(*values_), itertools.product(*types_))]

        if shuffle:
            random.shuffle(cards)
        return cards

    @classmethod
    def sum(cls, cards: List[MndCard]) -> List[int]:
        _sum = [0] * len(cards[0].values)
        for card in cards:
            for i, v in enumerate(card.values):
                _sum[i] += v
        return _sum

    def __str__(self):
        return f"{self.types}:{self.values}"

    def __repr__(self):
        return f"{self.types}:{self.values}"

class TwentyTwoGameHandler(GameHandler):
    """
    Handler for a multi-dimensional variant of Blackjack (22).
    """

    class TwentyTwoMove(Enum):
        NO_MOVE = 0
        STAND = 1
        HIT = 2

    @classmethod
    def get_possible_moves(cls, game: Game) -> List[TwentyTwoMove]:
        return [cls.TwentyTwoMove.HIT, cls.TwentyTwoMove.STAND]

    @classmethod
    def _resolve_round(cls, game: Game, player_move: TwentyTwoMove, opponent_move: TwentyTwoMove = None) -> GameResult:
        player_score = MndCard.sum(game.player_hand)
        opponent_score = MndCard.sum(game.opponent_hand)

        if any(score > game.lose_target for score in player_score):
            return GameResult.LOSE
        elif any(score >= game.win_target for score in player_score):
            return GameResult.WIN

        if player_move == cls.TwentyTwoMove.STAND:
            while max(opponent_score) < 17 or (max(opponent_score) < max(player_score) and max(opponent_score) < 21):
                game.opponent_hand.append(game.card_deck.pop())
                opponent_score = MndCard.sum(game.opponent_hand)

            if any(score > game.lose_target for score in opponent_score):
                return GameResult.WIN
            elif max(player_score) > max(opponent_score):
                return GameResult.WIN
            elif max(player_score) < max(opponent_score):
                return GameResult.LOSE
            else:
                return GameResult.DRAW

        return GameResult.IN_PROCESS

    @classmethod
    def handle_player_move(cls, game: Game, player_move: TwentyTwoMove) -> GameResult:
        if player_move == cls.TwentyTwoMove.HIT:
            game.player_hand.append(game.card_deck.pop())
            return cls._resolve_round(game, player_move)
        elif player_move == cls.TwentyTwoMove.STAND:
            return cls._resolve_round(game, player_move)

    @classmethod
    def setup_game(cls, game: Game):
        super().setup_game(game)
        game.player_hand = [game.card_deck.pop(), game.card_deck.pop()]
        game.opponent_hand = [game.card_deck.pop(), game.card_deck.pop()]


class TwentyTwoGame(CardGame):
    game_handler_cls = TwentyTwoGameHandler
    card_deck: list[MndCard] = Field(default_factory=lambda: MndCard.fresh_deck([-3, 3], [['a', 'b', 'c']], shuffle=True), json_schema_extra={'reset_field': True})
    player_hand: list[MndCard] = Field(default_factory=list, json_schema_extra={'reset_field': True})
    opponent_hand: list[MndCard] = Field(default_factory=list, json_schema_extra={'reset_field': True})
    win_target: int = 22
    lose_target: int = 22
