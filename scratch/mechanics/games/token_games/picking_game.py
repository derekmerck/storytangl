from collections import Iterable
from enum import Enum

from tangl.mechanics.game.game_handler import GameHandler, Game
from .token import Token

Move = Enum

class PickingGameHandler(GameHandler):

    def _resolve_round(cls, game: Game, player_move: Move, opponent_move: Move):
        ...

    def get_possible_moves(cls, game: Game) -> list[Move]:
        ...


class PickingGame(Game):
    """
    Tokens are exposed in the field, the player must recognize and pick out
    tokens with particular features.

    Examples:
    - match similar tokens (optionally with reveal in pairs)
    - identify added/removed tokens (spot the difference, kim's game)
    - which comes next (pattern recognition)

    The credential-checking mechanic uses this as a basis, credential parts
    are converted to tokens in this framework.
    """

    game_field: Iterable[Token] = None
