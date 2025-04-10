from __future__ import annotations
from typing import Literal
from enum import Enum
from collections import Counter

from pydantic import Field

from tangl.core.graph import SingletonNode
from tangl.mechanics.game.game_handler import GameHandler, Game
from tangl.mechanics.game.strategy_games.rps_game import RpsGame, RpsGameHandler
from .game_token import GameToken

class TokenGameHandler(GameHandler):
    """
    - Player and opponent each have a token reserve
    - Field contains tokens from both player or opponent
    - Moves are to add or take tokens from the field according to rules

    examples:
    - nim: take 1, 2, or 3, loser takes last
    """

    class TokenGameMove(Enum):
        TAKE_ONE = "take_one"
        PUT_ONE  = "put_one"
        TAKE_FEW = "take_few"    # or 2
        PUT_FEW  = "put_few"
        TAKE_MANY = "take_many"  # or 3
        PUT_MANY  = "put_many"

    @classmethod
    def _resolve_round(cls, game: Game, player_move: TokenGameMove, opponent_move: TokenGameMove):
        ...

    @classmethod
    def get_possible_moves(cls, game: TokenGame):
        return list(cls.TokenGameMove)

class TokenGame(Game):
    player_tokens: Counter = Field(default_factory=Counter)
    opponent_tokens: Counter = Field(default_factory=Counter)
    field_tokens: Counter = Field(default_factory=Counter)

# -------


class RpsGameToken(GameToken):
    affiliation: Enum | str = None


class RpsTokenGameHandler(RpsGameHandler, TokenGameHandler):
    ...

class RpsTokenGame(TokenGame, RpsGame):
    ...
