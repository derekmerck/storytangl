from __future__ import annotations
import random
from enum import Enum

from bson.regex import str_flags_to_int

from tangl.core import HandlerRegistry
from tangl.mechanics.game.game_handler import Game, GameHandler, GameResult

from ..game_handler import opponent_strategies, scoring_strategies
# opponent_strategies = HandlerRegistry(label='opponent_strategies')
# scoring_strategies = HandlerRegistry(label='scoring_strategies')


class RpsMove(Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"


class RpsGameHandler(GameHandler):

    @classmethod
    def get_possible_moves(cls, game: Game) -> list[RpsMove]:
        return list(RpsMove)

    @classmethod
    def _resolve_round(cls, game: Game, player_move: RpsMove, opponent_move: RpsMove):
        
        # Update the score
        if player_move is opponent_move:
            return GameResult.DRAW
        elif (player_move is RpsMove.ROCK and opponent_move is RpsMove.SCISSORS) or \
           (player_move is RpsMove.PAPER and opponent_move is RpsMove.ROCK) or \
           (player_move is RpsMove.SCISSORS and opponent_move is RpsMove.PAPER):
            game.score["player"] += 1
            return GameResult.WIN
        else:
            game.score["opponent"] += 1
            return GameResult.LOSE

    @opponent_strategies.register()
    @staticmethod
    def always_rock(game: Game, player_move: RpsMove = None) -> RpsMove:
        return RpsMove.ROCK

    @opponent_strategies.register()
    @staticmethod
    def always_paper(game: Game, player_move: RpsMove = None) -> RpsMove:
        return RpsMove.PAPER

    @opponent_strategies.register()
    @staticmethod
    def always_scissors(game: Game, player_move: RpsMove = None) -> RpsMove:
        return RpsMove.SCISSORS

    @opponent_strategies.register()
    @staticmethod
    def force_win(game: Game, player_move: RpsMove) -> RpsMove:
        if player_move is RpsMove.ROCK:
            return RpsMove.PAPER
        elif player_move is RpsMove.PAPER:
            return RpsMove.SCISSORS
        else:  # player_move == RpsGameHandler.Choice.SCISSORS
            return RpsMove.ROCK

    @opponent_strategies.register
    @staticmethod
    def force_lose(game: RpsGame, player_move: RpsMove) -> RpsMove:
        if player_move is RpsGameHandler.RpsMove.ROCK:
            return RpsGameHandler.RpsMove.SCISSORS
        elif player_move is RpsGameHandler.RpsMove.PAPER:
            return RpsGameHandler.RpsMove.ROCK
        else:  # player_move == RpsGameHandler.Choice.SCISSORS
            return RpsGameHandler.RpsMove.PAPER

class RpsGame(Game):
    game_handler_cls = RpsGameHandler

class RpslsMove( Enum ):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"
    LIZARD = "lizard"
    SPOCK = "spock"

class RpslsGameHandler(GameHandler):
    """
    Extends the existing rules of Rock-Paper-Scissors with Lizard and Spock moves.

    Rock crushes scissors and crushes lizard, scissors cuts paper and decapitates lizard, paper covers rock and disproves Spock, lizard poisons Spock and eats paper, Spock smashes scissors and vaporizes rock.

    RPS can be further extended to any odd number, n*2+1, of moves as long as each move beats n of the other moves.
    """

    WINNING_RPSLMOVES = {
        RpslsMove.ROCK: [RpslsMove.SCISSORS, RpslsMove.LIZARD],
        RpslsMove.PAPER: [RpslsMove.ROCK, RpslsMove.SPOCK],
        RpslsMove.SCISSORS: [RpslsMove.PAPER, RpslsMove.LIZARD],
        RpslsMove.LIZARD: [RpslsMove.SPOCK, RpslsMove.PAPER],
        RpslsMove.SPOCK: [RpslsMove.SCISSORS, RpslsMove.ROCK],
    }

    # @classmethod
    # def aliases(cls) -> typ.ClassVar[typ.Dict['Move', typ.List[str]]]:
    #     return {
    #         cls.ROCK:     ["stone",  "force",  "heavy"],
    #         cls.SCISSORS: ["iron",   "charm",  "ranged"],
    #         cls.PAPER:    ["glass",  "sly",    "fast"],
    #         cls.LIZARD:   ["fire",             "hack"],
    #         cls.SPOCK:    ["water",            "ice"],
    #         cls.WIN:      ["adaptive"],
    #         cls.LOSE:     ["pass"]
    #     }

    @classmethod
    def get_possible_moves(cls, game: Game) -> list[RpslsMove]:
        return list(RpslsMove)

    @classmethod
    def _resolve_round(cls, game: Game, player_move: RpslsMove, opponent_move: RpslsMove):

        # Update the score
        if opponent_move in cls.WINNING_RPSLMOVES[player_move]:
            game.score["player"] += 1
            return GameResult.WIN
        elif player_move in cls.WINNING_RPSLMOVES[opponent_move]:
            game.score["opponent"] += 1
            return GameResult.LOSE
        return GameResult.DRAW

    @opponent_strategies.register()
    @staticmethod
    def force_win(game: Game, player_move: RpslsMove) -> RpslsMove:
        for move, beats in cls.WINNING_RPSLMOVES.items():
            if player_move in beats:
                return move
        # fallback
        return cls.make_random_move()

    @opponent_strategies.register()
    @staticmethod
    def force_lose(game: Game, player_move: RpslsMove) -> RpslsMove:
        return random.choice( cls.WINNING_RPSLMOVES[player_move] )

class RpslsGame(Game):
    game_handler_cls = RpslsGameHandler

# # Original implementation used 'payout matrices' that could be swapped out for different outcome effects.
# # payouts:
# rps3_payout = [
#     [0, 1, 0],
#     [0, 0, 1],
#     [1, 0, 0]
# ]
#
# rps3_penalty_payout = [
#     [0, 1, -1],
#     [-1, 0, 1],
#     [1, -1, 0]
# ]
#
# rps5_payout = [
#     [0, 1, 0, 1, 0],
#     [0, 0, 1, 0, 1],
#     [1, 0, 0, 1, 0],
#     [0, 1, 0, 0, 1],
#     [1, 0, 1, 0, 0]
# ]
#
# rps5_chasing_payout = [
#     [0, 1, 1, 0, 0],
#     [0, 0, 1, 1, 0],
#     [0, 0, 0, 1, 1],
#     [1, 0, 0, 0, 1],
#     [1, 1, 0, 0, 0]
# ]
