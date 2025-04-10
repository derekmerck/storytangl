"""
An abstract 2-player "game" has a set of possible moves and a resolution strategy or
payout matrix.

More complex forms can have different moves per player or evolving payouts.

Games progress over "rounds", to distinguish them from story "turns".  One turn
of the base structure may include multiple games with multiple rounds.

Examples:
- Turn-by-turn _solo_ env payouts -- blackjack (deterministic), slots, stock market investment
- Turn-by-turn _shared_ direct comparison payouts -- rock/paper/scissors, war, auctions
- Turn-by-turn _shared_ env payouts -- uno, rummy, chess, monopoly, nim, hana fuda
- Turn-by-turn _solo_ evolution/resources -- cookie clicker, dark room, realm grinder, balatro
- Turn-by-turn _shared_ evolution/resources -- the holy grail...
"""

from __future__ import annotations
import random
from typing import Callable, TypeVar, ClassVar, Optional, Type
from abc import ABC, abstractmethod
from enum import Enum

from pydantic import Field, field_validator, model_validator

from tangl.core.handlers import PipelineStrategy
from tangl.core.graph import Node
from tangl.core.handlers import on_gather_context
from .enums import GameResult

# Move-type for any GameHandler may be a simple Enum or a more complex
# parameterized dataclass
Move = TypeVar("Move")

# Annotated strategies should follow these sigs:
OpponentStrategyFunc = Callable[[Type['GameHandler'], 'Game', Optional[Move]], Move]
# Requires player move param for opponent strategy, but not for opponent next move
# strategy, which is called _before_ player move is determined
ScoringStrategyFunc = Callable[[Type['GameHandler'], 'Game'], GameResult]

GameType = TypeVar("GameType", bound='Game')

# todo: definitely need each game handler to have it's OWN strategy registry
opponent_strategies = StrategyRegistry(label='game_opponent_strategies')
scoring_strategies = StrategyRegistry(label='game_scoring_strategies')


class GameHandler(ABC):
    """
    Provides a base class for game handler logic that can be wrapped in a challenge block.

    It encapsulates all functionality into just a few public api calls:

    - `setup_game`  # or reset
    - `get_possible_moves`
    - `handle_player_move`
    - `check_game_status`

    Two purely abstract methods: the public `get_player_moves`, and the private
    `_resolve_round`, must be implemented for each different game-type.

    When adding named opponent strategies, they should be decorated in the handler with
    `@opponent_strategy`.

    If adding additional scoring strategies, they should be decorated in the handler with
    `@scoring_strategy`.

    This provides maps for function names to be dereferenced from simple string fields in
    the Game dataclass.

    The Game class itself is only responsible for resetting and dumping state to when required,
    such as for assigning namespace variables to evaluate win conditions at higher levels.
    """

    # These methods _must_ be implemented for each subclass game-type
    @classmethod
    @abstractmethod
    def get_possible_moves(cls, game: Game) -> list[Move]:
        """
        Generate the possible moves for the player based on the current game state.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _resolve_round(cls, game: Game, player_move: Move, opponent_move: Move = None):
        """
        Update the game state for this round, based on provided the player move and
        optional opponent move.
        """
        raise NotImplementedError

    # These methods are fairly generic, but may be overridden when useful
    @classmethod
    def setup_game(cls, game: Game):
        """
        Reset all transient fields annotated with `json_schema_extra={reset_field:True}`
        """
        Game.reset_fields(game)
        # initialize opponent move
        game.opponent_next_move = cls._get_opponent_move(game)

    @classmethod
    def handle_player_move(cls, game: Game, player_move: Move) -> GameResult:
        """Handle a user action, updating the game state appropriately."""
        opponent_move = cls._revise_opponent_move(game, player_move=player_move)
        # Increment the round number
        # game.round += 1  # could use the number of round results available
        round_result = cls._resolve_round(game, player_move, opponent_move)
        cls._update_game_history(game, player_move, opponent_move, round_result)
        res = cls.check_game_result(game)
        if res is GameResult.IN_PROCESS:
            game.opponent_next_move = cls._get_opponent_move(game)
        return res
        # Convenience return value for evaluating continue in test loops without
        # calling game instance for full status

    @classmethod
    def _update_game_history(cls, game: Game,
                             player_move: Move,
                             opponent_move: Move,
                             round_result: GameResult):
        game.history.append((player_move, opponent_move, round_result))

    @staticmethod
    def opponent_strategy(func: OpponentStrategyFunc):
        """
        Decorator to mark a method an opponent move-selection strategy.
        """
        opponent_strategies.register_strategy(func, func.__name__)
        return func

    @classmethod
    def get_opponent_strategy(cls, name: str) -> Callable:
        res = opponent_strategies.get_strategies(name)
        if res:
            return res[0]

    # Opponent move selection strategies are registered with `@opponent_move_strategy`
    @classmethod
    @opponent_strategy
    def make_random_move(cls, game: Game, player_move: Move = None) -> Move:
        # Override this for more complex move types
        return random.choice(cls.get_possible_moves(game))

    @classmethod
    def _get_opponent_move(cls, game: Game):
        if not game.opponent_move_strategy:
            return None
        strategy_func = cls.get_opponent_strategy( game.opponent_move_strategy )
        if strategy_func:
            return strategy_func(cls, game, None)

    @classmethod
    def _revise_opponent_move(cls, game: Game, player_move: Move) -> Move:
        if not game.opponent_revise_move_strategy:
            return game.opponent_next_move
        strategy_func = cls.get_opponent_strategy( game.opponent_revise_move_strategy )
        if strategy_func:
            return strategy_func(cls, game, player_move)

    @staticmethod
    def scoring_strategy(func: ScoringStrategyFunc):
        """
        Decorator to mark a method as a scoring strategy.
        """
        scoring_strategies.register_strategy(func, func.__name__)

    # Scoring strategies are registered with `@scoring_strategy`
    @classmethod
    @scoring_strategy
    def best_of_n(cls, game: Game) -> GameResult:
        """Check if the game has ended using best-of-n."""
        total_rounds = game.scoring_n
        player_wins = sum([1 if r[2] is GameResult.WIN else 0 for r in game.history])
        opponent_wins = sum([1 if r[2] is GameResult.LOSE else 0 for r in game.history])
        if player_wins >= total_rounds // 2 + 1:
            return GameResult.WIN
        elif opponent_wins >= total_rounds // 2 + 1:
            return GameResult.LOSE
        elif game.round > total_rounds:
            return GameResult.DRAW
        return GameResult.IN_PROCESS

    @classmethod
    @scoring_strategy
    def highest_at_n(cls, game: Game) -> GameResult:
        """Check if the game has ended using highest-score"""
        total_rounds = game.scoring_n
        if game.round > total_rounds:
            if game.score["player"] > game.score["opponent"]:
                return GameResult.LOSE
            elif game.score["player"] == game.score["opponent"]:
                return GameResult.DRAW
            return GameResult.WIN
        return GameResult.IN_PROCESS

    @classmethod
    @scoring_strategy
    def first_to_n(cls, game: Game) -> GameResult:
        """Check if the game has ended using first-to-n"""
        total_score = game.scoring_n
        if game.score["player"] >= total_score:
            return GameResult.WIN
        elif game.score["opponent"] >= total_score:
            return GameResult.DRAW
        return GameResult.IN_PROCESS

    @classmethod
    def check_game_result(cls, game: Game) -> GameResult:
        strategy_func = scoring_strategies.get_strategies( game.scoring_strategy )
        if strategy_func:
            strategy_func = strategy_func[0]
            return strategy_func(cls, game)
        raise ValueError(f"Invalid scoring strategy: {game.scoring_strategy}")


class Game(HasNamespace, Node):
    # Games are `Nodes`, so they have access to the parent block's namespace
    # to get situational effects or global bonuses for identifying possible moves,
    # resolving rounds, or computing opponent strategies.

    score: dict = Field(
        default_factory=lambda: {"player": 0, "opponent": 0},
        json_schema_extra={'reset_field': True})
    # round_result: GameResult = Field(None, json_schema_extra = {'reset_field': True})
    # round: int = Field(1, json_schema_extra={'reset_field': True})
    history: list[tuple[Move, Move, GameResult]] = Field(
        default_factory=list,
        json_schema_extra={'reset_field': True} )
    # history is available for computing memory-dependent strategies like tit-for-tat

    scoring_n: int = 3
    scoring_strategy: str = "best_of_n"

    opponent_move_strategy: str = "make_random_move"
    opponent_revise_move_strategy: str = None
    opponent_next_move: Move = None
    # Opponents planned next move will be selected when the round is setup.  If the opponent
    # has a "tell", it can be broadcast.
    # However, opponents get a chance to _revise_ their move after the player move is
    # declared. This allows the script to force wins or losses.

    game_handler_cls: ClassVar[Type[GameHandler]] = GameHandler

    @field_validator("scoring_strategy",
                     "opponent_move_strategy",
                     "opponent_revise_move_strategy")
    @classmethod
    def _is_valid_strategy(cls, value):
        if value not in set(scoring_strategies.keys() + opponent_strategies.keys()):
            raise ValueError(f"No such strategy: {value}")
        return value

    @model_validator(mode='after')
    def _setup_game(self):
        self.game_handler_cls.setup_game(self)

    @property
    def round(self):
        return len(self.history) + 1

    @property
    def round_result(self):
        if self.history:
            return self.history[-1][2]
        return GameResult.IN_PROCESS

    @property
    def result(self):
        return self.game_handler_cls.check_game_result(self)

    @on_gather_context.register
    def _include_game_status(self):
        R = GameResult
        res = {
            "player_move": self.history[-1][0] if self.history else None,
            "opponent_move": self.history[-1][1] if self.history else None,
            "opponent_next_move": self.opponent_next_move,

            "game_round": self.round,
            "round_result": self.round_result,
            "player_won_round": self.round_result is R.WIN,
            "player_lost_round": self.round_result is R.LOSE,
            "round_is_draw": self.round_result is R.DRAW,
            "player_score": self.score["player"][-1] if self.score["player"] else None,
            "opponent_score": self.score["opponent"][-1] if self.score["opponent"] else None,

            "game_result": self.result,
            "player_won_game": self.result is R.WIN,
            "player_lost_game": self.result is R.LOSE,
            "game_is_draw": self.result is R.DRAW,
            "game_in_process": self.result is R.IN_PROCESS,

            "game_scoring_strategy": self.scoring_strategy,
            "game_total_rounds": self.scoring_n,
            "game_total_points": self.scoring_n,
        }
        return res

    @on_gather_context.register
    def _add_game_result_enum_to_ns(self):
        # for evaluating enums like `R.WIN`
        return {'R': GameResult}

    # convenience functions to access the node's GameHandler
    def get_possible_moves(self) -> list[Move]:
        # invoked by challenge.render()
        return self.game_handler_cls.get_possible_moves(self)

    def handle_player_move(self, player_move: Move) -> GameResult:
        # invoked by challenge.enter()
        return self.game_handler_cls.handle_player_move(self, player_move)
