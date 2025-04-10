from __future__ import annotations
from enum import Enum
from typing import Type, ClassVar
import random

from pydantic import ConfigDict, Field

from .game_handler import GameHandler, Game
from .enums import GameResult


class TrivialGameHandler(GameHandler):
    """
    A trivial game handler for testing and demonstrating the game mechanic framework.

    This game simulates a simple "Win-Lose-Draw" scenario where:
    - Players choose to either Win, Lose, or Draw.
    - The outcome depends on both the player's and opponent's choices.
    - Different scoring strategies and opponent behaviors can be easily implemented.

    It serves as a minimal example of how to implement a custom game within the
    StoryTangl game mechanic system, showcasing:
    - Custom move types
    - Various opponent strategies
    - Different scoring methods
    - Integration with the larger story context
    """

    class WinLoseMove(Enum):
        WIN = "win"
        LOSE = "lose"
        DRAW = "draw"

    @classmethod
    def get_possible_moves(cls, game: Game) -> list[WinLoseMove]:
        return list(cls.WinLoseMove)

    @classmethod
    def _resolve_round(cls, game: Game, player_move: WinLoseMove, opponent_move: WinLoseMove):
        if player_move is opponent_move:
            game.score["player"] += 1
            game.score["opponent"] += 1
            return GameResult.DRAW
        elif player_move is cls.WinLoseMove.WIN:
            game.score["player"] += 2
            return GameResult.WIN
        else:
            game.score["opponent"] += 2
            return GameResult.LOSE

    @GameHandler.opponent_strategy
    def always_win(cls, game: Game, player_move: WinLoseMove = None) -> WinLoseMove:
        return cls.WinLoseMove.WIN

    @GameHandler.opponent_strategy
    def always_lose(cls, game: Game, player_move: WinLoseMove = None) -> WinLoseMove:
        return cls.WinLoseMove.LOSE

    @GameHandler.opponent_strategy
    def always_draw(cls, game: Game, player_move: WinLoseMove = None) -> WinLoseMove:
        return cls.WinLoseMove.DRAW

    # todo: these are revision _only_ strategies b/c they required a player move
    @GameHandler.opponent_strategy
    def always_oppose(cls, game: Game, player_move: WinLoseMove) -> WinLoseMove:
        if player_move == cls.WinLoseMove.WIN:
            return cls.WinLoseMove.LOSE
        elif player_move == cls.WinLoseMove.LOSE:
            return cls.WinLoseMove.WIN
        return cls.WinLoseMove.DRAW

    @GameHandler.opponent_strategy
    def always_agree(cls, game: Game, player_move: WinLoseMove) -> WinLoseMove:
        return player_move

    @GameHandler.scoring_strategy
    def most_wins_played(cls, game: Game) -> GameResult:
        """Determine the winner based on who played the most wins after n rounds."""
        if game.round > game.scoring_n:
            player_wins = sum(1 for result in game.history if result[0] == cls.WinLoseMove.WIN)
            opponent_wins = sum(1 for result in game.history if result[1] == cls.WinLoseMove.WIN)
            if player_wins > opponent_wins:
                return GameResult.WIN
            elif opponent_wins > player_wins:
                return GameResult.LOSE
            else:
                return GameResult.DRAW
        else:
            return GameResult.IN_PROCESS

    @GameHandler.scoring_strategy
    def points_after_n(cls, game: TrivialGame) -> GameResult:
        """End the game after n rounds, win if player has at least m points else lose."""
        if game.round > game.scoring_n:
            if game.score["player"] >= game.point_threshold:
                return GameResult.WIN
            return GameResult.LOSE
        else:
            return GameResult.IN_PROCESS


class TrivialGame(Game):
    """
    Represents an instance of the Trivial Game.

    This class holds the state of a TrivialGame and provides methods to interact
    with it. It can be used within a GameChallenge to integrate the game into
    the larger story context.

    Attributes:
        point_threshold (int): The number of points required to win the game
                               when using the 'point_threshold' scoring strategy.
        difficulty (int): A difficulty modifier that can affect game behavior.

    The game state can be accessed and modified through the inherited attributes
    from the Game class, such as 'score', 'round', 'history', etc.
    """
    game_handler_cls: ClassVar[Type[GameHandler]] = TrivialGameHandler
    scoring_strategy: str = "most_wins_played"

    point_threshold: int = Field(5, description="Points needed to win when using 'point_threshold' scoring")

    def handle_player_move(self, player_move: TrivialGameHandler.WinLoseMove) -> GameResult:

        try:
            # Example of how game might interact with story context
            if "lucky_charm" in self.graph.player.inv:
                self.opponent_revise_move_strategy = "always_lose"
        except AttributeError:
            # for testing without a story
            pass

        return super().handle_player_move(player_move)
