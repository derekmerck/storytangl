"""
Game mechanics enumerations.

Pure domain types with no framework dependencies.
"""
from enum import Enum


class GamePhase(Enum):
    """
    Lifecycle phase of a game instance.
    
    State machine:
        PENDING ──setup()──► READY ◄────────────────┐
                               │                    │
                               │ receive_move()     │ (continue)
                               ▼                    │
                           RESOLVING ──► evaluate() ─┴─► IN_PROCESS
                               │
                               │ evaluate() → WIN/LOSE/DRAW
                               ▼
                           TERMINAL
    """
    PENDING = "pending"        # setup() not yet called
    READY = "ready"            # awaiting player move
    RESOLVING = "resolving"    # transient: processing move
    TERMINAL = "terminal"      # game over, result is final


class GameResult(Enum):
    """
    Outcome of a game.
    
    IN_PROCESS means the game is still ongoing.
    Terminal results are WIN, LOSE, DRAW from the player's perspective.
    """
    IN_PROCESS = "in_process"
    WIN = "win"
    LOSE = "lose"
    DRAW = "draw"
    
    @property
    def is_terminal(self) -> bool:
        return self is not GameResult.IN_PROCESS


class RoundResult(Enum):
    """
    Outcome of a single round within a game.
    
    Similar to GameResult but represents per-round outcomes,
    which may accumulate toward the final GameResult.
    """
    WIN = "win"
    LOSE = "lose"
    DRAW = "draw"
    CONTINUE = "continue"  # round processed but no clear winner (e.g., card draw)
    
    def to_game_result(self) -> GameResult:
        """Convert to equivalent GameResult (for single-round games)."""
        if self is RoundResult.WIN:
            return GameResult.WIN
        elif self is RoundResult.LOSE:
            return GameResult.LOSE
        elif self is RoundResult.DRAW:
            return GameResult.DRAW
        return GameResult.IN_PROCESS
