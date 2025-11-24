"""
Trivial game implementation.

A minimal game where the player explicitly chooses to WIN, LOSE, or DRAW.
Used for testing the game state machine without game logic complexity.

The opponent can be configured to always pick a particular outcome,
which makes it easy to test all terminal conditions.
"""
from __future__ import annotations
from enum import Enum
from typing import ClassVar, Type

from pydantic import Field

from .enums import GamePhase, GameResult, RoundResult
from .game import Game, RoundRecord
from .handler import GameHandler, SimpleGameHandler
from .strategies import opponent_strategies, scoring_strategies


class TrivialMove(Enum):
    """Explicit outcome selection."""
    WIN = "win"
    LOSE = "lose"
    DRAW = "draw"


class TrivialGame(Game[TrivialMove]):
    """
    Game state for the trivial "choose your outcome" game.
    
    Default configuration plays 3 rounds, best-of-n scoring.
    """
    scoring_n: int = 3
    scoring_strategy: str = "best_of_n"
    opponent_strategy: str = "trivial_random"


class TrivialGameHandler(SimpleGameHandler[TrivialGame]):
    """
    Handler for the trivial game.
    
    Resolution is straightforward:
    - If player and opponent pick the same: DRAW
    - If player picks WIN: player wins (regardless of opponent)
    - If player picks LOSE: player loses (regardless of opponent)
    
    This means the player has direct control over per-round outcomes,
    making it trivial to test all game states.
    """
    
    moves: ClassVar[list[TrivialMove]] = list(TrivialMove)
    game_cls: ClassVar[Type[Game]] = TrivialGame
    
    def resolve_round(
        self,
        game: TrivialGame,
        player_move: TrivialMove,
        opponent_move: TrivialMove | None,
    ) -> RoundResult:
        """
        Resolve based on player's explicit choice.
        
        Player's choice directly determines the round outcome.
        Opponent move is used for strategies that react (e.g., always_agree).
        """
        if player_move == opponent_move:
            # Both picked same - draw, no score change
            game.score["player"] += 1
            game.score["opponent"] += 1
            return RoundResult.DRAW
        
        if player_move == TrivialMove.WIN:
            game.score["player"] += 2
            return RoundResult.WIN
        
        if player_move == TrivialMove.LOSE:
            game.score["opponent"] += 2
            return RoundResult.LOSE
        
        # Player picked DRAW but opponent didn't
        game.score["player"] += 1
        game.score["opponent"] += 1
        return RoundResult.DRAW


# ─────────────────────────────────────────────────────────────────────────────
# Opponent strategies for trivial game
# ─────────────────────────────────────────────────────────────────────────────

@opponent_strategies.register("trivial_random")
def _trivial_random(game: TrivialGame, **ctx) -> TrivialMove:
    """Random trivial move."""
    import random
    return random.choice(list(TrivialMove))


@opponent_strategies.register("trivial_win")
def _trivial_always_win(game: TrivialGame, **ctx) -> TrivialMove:
    """Opponent always picks WIN (doesn't affect outcome)."""
    return TrivialMove.WIN


@opponent_strategies.register("trivial_lose")
def _trivial_always_lose(game: TrivialGame, **ctx) -> TrivialMove:
    """Opponent always picks LOSE (doesn't affect outcome)."""
    return TrivialMove.LOSE


@opponent_strategies.register("trivial_draw")
def _trivial_always_draw(game: TrivialGame, **ctx) -> TrivialMove:
    """Opponent always picks DRAW."""
    return TrivialMove.DRAW


@opponent_strategies.register("trivial_agree")
def _trivial_agree(game: TrivialGame, player_move: TrivialMove = None, **ctx) -> TrivialMove:
    """
    Revision strategy: opponent agrees with player's choice.
    
    This forces a DRAW every round, useful for testing.
    """
    if player_move is None:
        return TrivialMove.DRAW
    return player_move


@opponent_strategies.register("trivial_oppose")
def _trivial_oppose(game: TrivialGame, player_move: TrivialMove = None, **ctx) -> TrivialMove:
    """
    Revision strategy: opponent picks opposite of player.
    
    WIN→LOSE, LOSE→WIN, DRAW→DRAW
    """
    if player_move is None:
        return TrivialMove.DRAW
    if player_move == TrivialMove.WIN:
        return TrivialMove.LOSE
    if player_move == TrivialMove.LOSE:
        return TrivialMove.WIN
    return TrivialMove.DRAW
