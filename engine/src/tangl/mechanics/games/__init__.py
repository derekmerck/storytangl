"""
Game mechanics core - pure domain logic.

This package provides the foundational game state machine with no VM dependencies.
It can be tested in isolation and bolted onto the VM phase bus later.

Core Classes
------------
Game : BaseModel
    Stateful game instance container.
GameHandler : ABC
    Stateless rules engine that operates on Game instances.
RoundRecord : dataclass
    Immutable record of a single round's outcome.

Enums
-----
GamePhase : Enum
    Lifecycle phase (PENDING, READY, RESOLVING, TERMINAL).
GameResult : Enum
    Game outcome (IN_PROCESS, WIN, LOSE, DRAW).
RoundResult : Enum
    Per-round outcome (WIN, LOSE, DRAW, CONTINUE).

Registries
----------
opponent_strategies : StrategyRegistry
    Named strategies for opponent move selection.
scoring_strategies : StrategyRegistry
    Named strategies for terminal condition evaluation.

Example
-------
>>> from game_core import Game, GameHandler, GamePhase, GameResult
>>> 
>>> class MyGame(Game):
...     pass
>>> 
>>> class MyHandler(GameHandler[MyGame]):
...     def get_available_moves(self, game):
...         return ["move_a", "move_b"]
...     
...     def resolve_round(self, game, player_move, opponent_move):
...         # ... game logic ...
...         return RoundResult.WIN
>>> 
>>> game = MyGame()
>>> handler = MyHandler()
>>> handler.setup(game)
>>> handler.receive_move(game, "move_a")
"""

from .enums import GamePhase, GameResult, RoundResult
from .game import Game, RoundRecord, Move
from .handler import GameHandler, SimpleGameHandler
from .strategies import (
    StrategyRegistry,
    opponent_strategies,
    scoring_strategies,
)

__all__ = [
    # Enums
    "GamePhase",
    "GameResult", 
    "RoundResult",
    # Core classes
    "Game",
    "RoundRecord",
    "Move",
    "GameHandler",
    "SimpleGameHandler",
    # Registries
    "StrategyRegistry",
    "opponent_strategies",
    "scoring_strategies",
]
