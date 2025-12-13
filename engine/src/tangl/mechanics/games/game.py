"""
Game state container.

The Game class holds all mutable state for a game instance.
GameHandler classes operate on Game instances to implement rules.

This module has minimal dependencies - just Pydantic for validation
and the local enums/strategies.

Must derive from entity to use with dispatch tho.
"""
from __future__ import annotations
from typing import Any, Callable, ClassVar, Generic, TypeVar
from dataclasses import dataclass
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict

from tangl.core import Entity
from .enums import GamePhase, GameResult, RoundResult

# Generic type for moves (each game defines its own move enum/type)
Move = TypeVar("Move")


@dataclass(frozen=True)
class RoundRecord(Generic[Move]):
    """
    Immutable record of a single round's outcome.
    
    Stored in game.history for strategy analysis and journal generation.
    """
    round_number: int
    player_move: Move
    opponent_move: Move | None
    result: RoundResult
    
    # Optional metadata for richer journal output
    notes: dict[str, Any] | None = None


class Game(Entity, Generic[Move]):
    """
    Base class for game state.
    
    Holds all mutable state for a game instance. The corresponding
    GameHandler operates on this state to implement game rules.
    
    Subclasses add game-specific state (token counts, card hands, etc.)
    and may override field defaults.
    
    Fields marked with `json_schema_extra={"reset_field": True}` are
    reset to their defaults when `reset()` is called.
    
    Attributes
    ----------
    uid : UUID
        Unique identifier for this game instance.
    phase : GamePhase
        Current lifecycle phase (PENDING, READY, RESOLVING, TERMINAL).
    result : GameResult
        Current outcome (IN_PROCESS until terminal).
    round : int
        Current round number (1-indexed after first move).
    score : dict
        Score tracking, typically {"player": n, "opponent": m}.
    history : list[RoundRecord]
        Complete history of all rounds for analysis/replay.
        
    Configuration
    -------------
    scoring_n : int
        Parameter for scoring strategies (rounds or points, depending on strategy).
    scoring_strategy : str
        Name of registered scoring strategy for terminal evaluation.
    opponent_strategy : str
        Name of registered strategy for opponent pre-selection.
    opponent_revision_strategy : str | None
        Optional strategy for opponent to revise move after seeing player's.
    opponent_next_move : Move | None
        Pre-selected opponent move (the "tell"), set during setup/after each round.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Identity
    uid: UUID = Field(default_factory=uuid4)
    
    # Lifecycle state
    phase: GamePhase = Field(
        default=GamePhase.PENDING,
        json_schema_extra={"reset_field": True}
    )
    result: GameResult = Field(
        default=GameResult.IN_PROCESS,
        json_schema_extra={"reset_field": True}
    )
    
    # Round tracking
    round: int = Field(
        default=0,
        json_schema_extra={"reset_field": True}
    )
    score: dict[str, int] = Field(
        default=None,
        json_schema_extra={"reset_field": True}
    )
    
    def model_post_init(self, __context) -> None:
        """Initialize mutable defaults after model construction."""
        if self.score is None:
            self.score = {"player": 0, "opponent": 0}
        if self.history is None:
            self.history = []
    history: list[RoundRecord] = Field(
        default=None,
        json_schema_extra={"reset_field": True}
    )
    
    # Configuration (not reset)
    scoring_n: int = 3
    scoring_strategy: str = "best_of_n"
    opponent_strategy: str = "random"
    opponent_revision_strategy: str | None = None
    
    # Pre-selected opponent move (reset each round or on setup)
    opponent_next_move: Any = Field(
        default=None,
        json_schema_extra={"reset_field": True}
    )
    
    # ─────────────────────────────────────────────────────────────────────
    # State accessors
    # ─────────────────────────────────────────────────────────────────────
    
    @property
    def is_terminal(self) -> bool:
        """True if game has reached a final state."""
        return self.phase == GamePhase.TERMINAL
    
    @property
    def is_ready(self) -> bool:
        """True if game is ready to receive a player move."""
        return self.phase == GamePhase.READY
    
    @property
    def last_round(self) -> RoundRecord | None:
        """Most recent round record, or None if no rounds played."""
        return self.history[-1] if self.history else None
    
    # ─────────────────────────────────────────────────────────────────────
    # Reset mechanism
    # ─────────────────────────────────────────────────────────────────────
    
    @classmethod
    def _get_reset_fields(cls) -> dict[str, Any]:
        """
        Collect fields marked with reset_field=True and their defaults.
        
        Walks the MRO to collect from all parent classes.
        """
        reset_fields = {}
        for klass in cls.__mro__:
            if not hasattr(klass, "model_fields"):
                continue
            for name, field_info in klass.model_fields.items():
                extra = field_info.json_schema_extra or {}
                if extra.get("reset_field"):
                    reset_fields[name] = field_info.default
        return reset_fields
    
    def reset(self) -> None:
        """
        Reset all fields marked with reset_field=True to their defaults.
        
        Called by GameHandler.setup() to initialize/reinitialize game state.
        """
        reset_values = self._get_reset_fields()
        for name, default in reset_values.items():
            setattr(self, name, default)
        
        # Re-initialize mutable defaults
        self.score = {"player": 0, "opponent": 0}
        self.history = []
    
    # ─────────────────────────────────────────────────────────────────────
    # Abstract interface (implemented via handler, but useful for duck typing)
    # ─────────────────────────────────────────────────────────────────────
    
    def get_available_moves(self) -> list[Move]:
        """
        Return list of currently available moves.
        
        Default implementation raises NotImplementedError.
        Subclasses should either override this or use a handler.
        """
        raise NotImplementedError(
            "Subclass must implement get_available_moves() or use GameHandler"
        )

    def matches(self, *, predicate: Callable[[Any], bool] | None = None, **criteria: Any) -> bool:
        """Behavior selection helper for VM dispatch registries."""

        if predicate is not None and not predicate(self):
            return False

        for key, expected in criteria.items():
            if key == "is_instance":
                if not isinstance(self, expected):
                    return False
                continue

            if not hasattr(self, key):
                return False

            current = getattr(self, key)
            if (key.startswith("has_") or key.startswith("is_")) and callable(current):
                if not current(expected):
                    return False
            elif current != expected:
                return False

        return True
    
    # ─────────────────────────────────────────────────────────────────────
    # Context export (for namespace injection)
    # ─────────────────────────────────────────────────────────────────────
    
    def to_namespace(self) -> dict[str, Any]:
        """
        Export game state as a flat namespace for condition evaluation.
        
        This is the data available to predicates like `game_result is R.WIN`.
        """
        R = GameResult  # Alias for predicate convenience
        
        last = self.last_round
        
        return {
            # Enums for predicate evaluation
            "GamePhase": GamePhase,
            "GameResult": GameResult,
            "RoundResult": RoundResult,
            "R": GameResult,  # Short alias
            
            # Phase and result
            "game_phase": self.phase,
            "game_result": self.result,
            "game_is_ready": self.is_ready,
            "game_is_terminal": self.is_terminal,
            
            # Scores
            "game_round": self.round,
            "player_score": self.score.get("player", 0),
            "opponent_score": self.score.get("opponent", 0),
            
            # Last round (if any)
            "last_player_move": last.player_move if last else None,
            "last_opponent_move": last.opponent_move if last else None,
            "last_round_result": last.result if last else None,
            
            # Result predicates
            "player_won_game": self.result == R.WIN,
            "player_lost_game": self.result == R.LOSE,
            "game_is_draw": self.result == R.DRAW,
            "game_in_progress": self.result == R.IN_PROCESS,
            
            # Last round predicates
            "player_won_round": last.result == RoundResult.WIN if last else False,
            "player_lost_round": last.result == RoundResult.LOSE if last else False,
            "round_is_draw": last.result == RoundResult.DRAW if last else False,
            
            # Tell (pre-selected opponent move)
            "opponent_next_move": self.opponent_next_move,
            
            # Configuration
            "scoring_n": self.scoring_n,
            "scoring_strategy": self.scoring_strategy,
        }
