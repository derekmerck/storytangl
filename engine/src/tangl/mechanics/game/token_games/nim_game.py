from __future__ import annotations
from typing import List
from enum import Enum
from collections import Counter

from pydantic import Field

from tangl.mechanics.game.game_handler import GameHandler, Game, GameResult
from .token import Token
from .token_game import TokenGameHandler, TokenGame

class NimGameHandler(TokenGameHandler):
    """
    - Player and opponent each have a token reserve
    - Field contains tokens from both player or opponent
    - Moves are to add or take tokens from the field according to rules
    """

    class TokenGameMove(Enum):
        TAKE_ONE   = "take_one"
        TAKE_TWO   = "take_two"
        TAKE_THREE = "take_three"

    @classmethod
    def get_possible_moves(cls, game: TokenGame) -> List[TokenGameMove]:
        moves = []
        if game.field_tokens['total'] >= 1:
            moves.append(cls.TokenGameMove.TAKE_ONE)
        if game.field_tokens['total'] >= 2:
            moves.append(cls.TokenGameMove.TAKE_TWO)
        if game.field_tokens['total'] >= 3:
            moves.append(cls.TokenGameMove.TAKE_THREE)
        return moves

    @classmethod
    def _resolve_round(cls, game: TokenGame, player_move: TokenGameMove, opponent_move: TokenGameMove = None):
        if player_move == cls.TokenGameMove.TAKE_ONE:
            game.field_tokens['total'] -= 1
        elif player_move == cls.TokenGameMove.TAKE_TWO:
            game.field_tokens['total'] -= 2
        elif player_move == cls.TokenGameMove.TAKE_THREE:
            game.field_tokens['total'] -= 3

        if game.field_tokens['total'] <= 0:
            return GameResult.WIN

        # Opponent's move (for simplicity, we assume opponent always takes one token)
        if opponent_move is not None:
            if opponent_move == cls.TokenGameMove.TAKE_ONE:
                game.field_tokens['total'] -= 1
            elif opponent_move == cls.TokenGameMove.TAKE_TWO:
                game.field_tokens['total'] -= 2
            elif opponent_move == cls.TokenGameMove.TAKE_THREE:
                game.field_tokens['total'] -= 3

            if game.field_tokens['total'] <= 0:
                return GameResult.LOSE

        return GameResult.IN_PROCESS

    @classmethod
    def handle_player_move(cls, game: TokenGame, player_move: TokenGameMove) -> GameResult:
        result = cls._resolve_round(game, player_move)
        if result == GameResult.IN_PROCESS:
            opponent_move = cls.get_possible_moves(game)[0]  # Simplified opponent strategy
            result = cls._resolve_round(game, player_move, opponent_move)
        return result

    @classmethod
    def setup_game(cls, game: TokenGame):
        super().setup_game(game)
        game.field_tokens['total'] = 21  # Example starting number of tokens


class NimGame(Game):
    game_handler_cls = TokenGameHandler
    field_tokens: Counter = Field(default_factory=Counter)

    def reset(self):
        self.field_tokens = Counter({'total': 21})  # Example starting number of tokens
