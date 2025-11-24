"""
Strategy registries for game mechanics.

Provides named strategy registration and lookup for opponent move selection
and game scoring/terminal condition evaluation.

This is a simplified registry pattern that can later be backed by the full
DispatchRegistry if needed, but has no framework dependencies for testability.
"""
from __future__ import annotations
from typing import Callable, TypeVar, Generic, Any, TYPE_CHECKING
from dataclasses import dataclass, field
import random

if TYPE_CHECKING:
    from .game import Game
    from .enums import GameResult

# Type variable for move types (each game defines its own)
Move = TypeVar("Move")


@dataclass
class StrategyRegistry(Generic[Move]):
    """
    A simple registry mapping names to strategy functions.
    
    Strategies are callables that take a game instance and optional context,
    returning some result (a Move for opponent strategies, a GameResult for
    scoring strategies).
    
    Usage:
        opponent_strategies = StrategyRegistry[RpsMove]()
        
        @opponent_strategies.register("always_rock")
        def always_rock(game: RpsGame, **ctx) -> RpsMove:
            return RpsMove.ROCK
        
        # Later:
        move = opponent_strategies.execute("always_rock", game)
    """
    label: str = "strategies"
    _registry: dict[str, Callable] = field(default_factory=dict)
    
    def register(self, name: str | None = None):
        """
        Decorator to register a strategy function.
        
        If name is not provided, uses the function's __name__.
        """
        def decorator(func: Callable) -> Callable:
            key = name or func.__name__
            self._registry[key] = func
            return func
        return decorator
    
    def register_func(self, func: Callable, name: str | None = None) -> None:
        """Imperative registration (non-decorator form)."""
        key = name or func.__name__
        self._registry[key] = func
    
    def get(self, name: str) -> Callable | None:
        """Retrieve a strategy by name, or None if not found."""
        return self._registry.get(name)
    
    def execute(self, name: str, game: Game, **context) -> Any:
        """
        Execute a named strategy.
        
        Raises KeyError if strategy not found.
        """
        func = self._registry.get(name)
        if func is None:
            raise KeyError(f"No strategy registered with name: {name}")
        return func(game, **context)
    
    def execute_or_default(self, name: str | None, game: Game, default: Any = None, **context) -> Any:
        """Execute a strategy if name provided and exists, otherwise return default."""
        if name is None:
            return default
        func = self._registry.get(name)
        if func is None:
            return default
        return func(game, **context)
    
    def names(self) -> list[str]:
        """List all registered strategy names."""
        return list(self._registry.keys())
    
    def __contains__(self, name: str) -> bool:
        return name in self._registry


# ─────────────────────────────────────────────────────────────────────────────
# Global registries
# ─────────────────────────────────────────────────────────────────────────────

opponent_strategies: StrategyRegistry = StrategyRegistry(label="opponent_strategies")
"""
Registry for opponent move selection strategies.

Strategies should have signature:
    (game: Game, player_move: Move | None = None, **context) -> Move

The player_move parameter is provided for "revision" strategies that react
to what the player chose. Pre-selection strategies receive player_move=None.
"""

scoring_strategies: StrategyRegistry = StrategyRegistry(label="scoring_strategies")
"""
Registry for game terminal condition evaluation.

Strategies should have signature:
    (game: Game, **context) -> GameResult

Returns IN_PROCESS if game should continue, or a terminal result.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Built-in opponent strategies
# ─────────────────────────────────────────────────────────────────────────────

@opponent_strategies.register("random")
def _opponent_random(game: Game, **context) -> Any:
    """Select a random move from available moves."""
    moves = game.get_available_moves()
    if not moves:
        raise ValueError("No available moves to select from")
    return random.choice(moves)


# ─────────────────────────────────────────────────────────────────────────────
# Built-in scoring strategies  
# ─────────────────────────────────────────────────────────────────────────────

@scoring_strategies.register("best_of_n")
def _scoring_best_of_n(game: Game, **context) -> GameResult:
    """
    Game ends when either player wins majority of rounds.
    
    Requires game.scoring_n (total rounds) and game.history.
    Counts WIN/LOSE round results, not raw score values.
    """
    from .enums import GameResult, RoundResult
    
    n = game.scoring_n
    wins_needed = n // 2 + 1
    
    # Count round outcomes from history
    player_wins = sum(1 for r in game.history if r.result == RoundResult.WIN)
    opponent_wins = sum(1 for r in game.history if r.result == RoundResult.LOSE)
    
    if player_wins >= wins_needed:
        return GameResult.WIN
    elif opponent_wins >= wins_needed:
        return GameResult.LOSE
    elif len(game.history) >= n:
        # All rounds played, no majority
        if player_wins > opponent_wins:
            return GameResult.WIN
        elif opponent_wins > player_wins:
            return GameResult.LOSE
        return GameResult.DRAW
    
    return GameResult.IN_PROCESS


@scoring_strategies.register("first_to_n")
def _scoring_first_to_n(game: Game, **context) -> GameResult:
    """
    Game ends when either player reaches n points.
    
    Requires game.scoring_n (point target) and game.score dict.
    """
    from .enums import GameResult
    
    target = game.scoring_n
    
    player_score = game.score.get("player", 0)
    opponent_score = game.score.get("opponent", 0)
    
    if player_score >= target:
        return GameResult.WIN
    elif opponent_score >= target:
        return GameResult.LOSE
    
    return GameResult.IN_PROCESS


@scoring_strategies.register("highest_after_n")
def _scoring_highest_after_n(game: Game, **context) -> GameResult:
    """
    Game ends after n rounds, highest score wins.
    
    Requires game.scoring_n (round limit), game.round, and game.score dict.
    """
    from .enums import GameResult
    
    if game.round < game.scoring_n:
        return GameResult.IN_PROCESS
    
    player_score = game.score.get("player", 0)
    opponent_score = game.score.get("opponent", 0)
    
    if player_score > opponent_score:
        return GameResult.WIN
    elif opponent_score > player_score:
        return GameResult.LOSE
    else:
        return GameResult.DRAW


@scoring_strategies.register("single_round")
def _scoring_single_round(game: Game, **context) -> GameResult:
    """
    Game ends after one round. Round result becomes game result.
    """
    from .enums import GameResult
    
    if not game.history:
        return GameResult.IN_PROCESS
    
    # Last round result determines game outcome
    last_round = game.history[-1]
    return last_round.result.to_game_result()
