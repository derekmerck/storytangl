"""
Game handler - stateless rules engine.

GameHandler classes encapsulate game logic and operate on Game instances.
They are stateless - all mutable state lives in the Game.

This separation allows:
- Testing game logic without graph/VM dependencies
- Reusing handlers across multiple game instances
- Clean serialization (only Game state needs to be saved)
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, ClassVar, Type, Any

from .enums import GamePhase, GameResult, RoundResult
from .game import Game, RoundRecord, Move
from .strategies import opponent_strategies, scoring_strategies


GameT = TypeVar("GameT", bound=Game)


class GameHandler(ABC, Generic[GameT]):
    """
    Abstract base class for game rule handlers.
    
    Subclasses implement game-specific logic by overriding:
    - get_available_moves(game) -> list[Move]
    - resolve_round(game, player_move, opponent_move) -> RoundResult
    
    The handler drives the game through its lifecycle:
    
        PENDING ──setup()──► READY
                               │
                               │ receive_move()
                               ▼
                           RESOLVING ──evaluate()──► back to READY or TERMINAL
    
    Example
    -------
    >>> class RpsHandler(GameHandler[RpsGame]):
    ...     def get_available_moves(self, game):
    ...         return [Move.ROCK, Move.PAPER, Move.SCISSORS]
    ...     
    ...     def resolve_round(self, game, player, opponent):
    ...         # ... compare moves, update score ...
    ...         return RoundResult.WIN
    >>> 
    >>> game = RpsGame()
    >>> handler = RpsHandler()
    >>> handler.setup(game)
    >>> handler.receive_move(game, Move.ROCK)
    """
    
    # Subclasses can set this to bind a handler to a game type
    game_cls: ClassVar[Type[Game]] = Game
    
    # ─────────────────────────────────────────────────────────────────────
    # Abstract methods - must be implemented by subclasses
    # ─────────────────────────────────────────────────────────────────────
    
    @abstractmethod
    def get_available_moves(self, game: GameT) -> list[Move]:
        """
        Return the list of moves currently available to the player.
        
        Called during READY phase to generate choices.
        May depend on game state (e.g., only valid cards in hand).
        """
        raise NotImplementedError
    
    @abstractmethod
    def resolve_round(
        self,
        game: GameT,
        player_move: Move,
        opponent_move: Move | None,
    ) -> RoundResult:
        """
        Apply game rules to determine round outcome.
        
        This method should:
        1. Compare moves according to game rules
        2. Update game.score as appropriate
        3. Update any game-specific state (tokens, cards, etc.)
        4. Return the round result
        
        It should NOT:
        - Change game.phase (handled by receive_move)
        - Change game.result (handled by evaluate)
        - Append to game.history (handled by receive_move)
        """
        raise NotImplementedError
    
    # ─────────────────────────────────────────────────────────────────────
    # Lifecycle methods
    # ─────────────────────────────────────────────────────────────────────
    
    def setup(self, game: GameT) -> None:
        """
        Initialize or reset game to starting state.
        
        Resets all fields marked with reset_field=True, then
        pre-selects the opponent's first move.
        
        After setup(), game.phase == READY.
        """
        game.reset()
        game.phase = GamePhase.READY
        game.round = 0
        
        # Pre-select opponent move (the "tell")
        self._preselect_opponent_move(game)
        
        # Hook for subclass initialization
        self.on_setup(game)
    
    def on_setup(self, game: GameT) -> None:
        """
        Hook for subclass-specific initialization.
        
        Called at the end of setup() after standard reset.
        Override to initialize game-specific state (shuffle deck, etc.).
        """
        pass
    
    def receive_move(self, game: GameT, player_move: Move) -> RoundResult:
        """
        Process a player move.
        
        This is the main entry point for game progression:
        1. Validates game is in READY phase
        2. Determines final opponent move (may revise based on player choice)
        3. Resolves the round via resolve_round()
        4. Records the round in history
        5. Evaluates for terminal condition
        6. If not terminal, pre-selects next opponent move
        
        Returns the round result for immediate feedback.
        Caller should check game.result for terminal state.
        """
        if game.phase != GamePhase.READY:
            raise RuntimeError(
                f"Cannot receive move in phase {game.phase}. "
                f"Call setup() first or wait for READY phase."
            )
        
        # Transition to resolving
        game.phase = GamePhase.RESOLVING
        game.round += 1
        
        # Determine opponent move (may revise based on player's choice)
        opponent_move = self._finalize_opponent_move(game, player_move)
        
        # Apply game rules
        round_result = self.resolve_round(game, player_move, opponent_move)
        
        # Record history
        record = RoundRecord(
            round_number=game.round,
            player_move=player_move,
            opponent_move=opponent_move,
            result=round_result,
        )
        game.history.append(record)
        
        # Check for terminal condition
        game.result = self.evaluate(game)
        
        if game.result.is_terminal:
            game.phase = GamePhase.TERMINAL
        else:
            # Prepare for next round
            game.phase = GamePhase.READY
            self._preselect_opponent_move(game)
        
        return round_result
    
    def evaluate(self, game: GameT) -> GameResult:
        """
        Check if game has reached a terminal condition.
        
        Delegates to the registered scoring strategy.
        Override for custom terminal logic.
        """
        return scoring_strategies.execute(game.scoring_strategy, game)
    
    # ─────────────────────────────────────────────────────────────────────
    # Opponent move handling
    # ─────────────────────────────────────────────────────────────────────
    
    def _preselect_opponent_move(self, game: GameT) -> None:
        """
        Pre-select opponent's next move using the configured strategy.
        
        This allows providing a "tell" in the narrative before the
        player commits to their choice.
        """
        game.opponent_next_move = opponent_strategies.execute_or_default(
            game.opponent_strategy,
            game,
            default=None,
        )
    
    def _finalize_opponent_move(self, game: GameT, player_move: Move) -> Move | None:
        """
        Determine the final opponent move, potentially revising the pre-selection.
        
        If opponent_revision_strategy is set, the opponent can change their
        move in response to the player's choice. This enables:
        - Forced outcomes for narrative purposes
        - "Cheating" opponents that react to player
        - Dramatic reveals
        
        If no revision strategy, returns the pre-selected move.
        """
        if game.opponent_revision_strategy:
            revised = opponent_strategies.execute_or_default(
                game.opponent_revision_strategy,
                game,
                default=None,
                player_move=player_move,
            )
            if revised is not None:
                return revised
        
        return game.opponent_next_move
    
    # ─────────────────────────────────────────────────────────────────────
    # Validation helpers
    # ─────────────────────────────────────────────────────────────────────
    
    def is_valid_move(self, game: GameT, move: Move) -> bool:
        """Check if a move is currently valid."""
        return move in self.get_available_moves(game)
    
    def validate_move(self, game: GameT, move: Move) -> None:
        """Raise ValueError if move is not valid."""
        if not self.is_valid_move(game, move):
            available = self.get_available_moves(game)
            raise ValueError(
                f"Invalid move: {move}. Available moves: {available}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience base for simple games
# ─────────────────────────────────────────────────────────────────────────────

class SimpleGameHandler(GameHandler[GameT]):
    """
    Base for state-independent games with fixed move sets.
    
    Subclasses just need to define:
    - moves: ClassVar[list[Move]] - available moves
    - resolve_round() - comparison logic
    """
    
    moves: ClassVar[list[Any]] = []
    
    def get_available_moves(self, game: GameT) -> list[Move]:
        """Return the fixed move list."""
        return list(self.moves)
