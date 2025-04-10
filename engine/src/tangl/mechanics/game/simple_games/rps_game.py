import random
from enum import Enum

from tangl.mechanics.games.game_handler import Game, GameHandler, GameResult

class RpsGameHandler(GameHandler):

    class RpsMove( Enum ):
        ROCK = "rock"
        PAPER = "paper"
        SCISSORS = "scissors"

    @classmethod
    def get_possible_moves(cls, game: Game) -> list[RpsMove]:
        return list(cls.RpsMove)

    @classmethod
    def _resolve_round(cls, game: Game, player_move: RpsMove, opponent_move: RpsMove):
        
        # Update the score
        if player_move is opponent_move:
            return GameResult.DRAW
        elif (player_move is cls.RpsMove.ROCK and opponent_move is cls.RpsMove.SCISSORS) or \
           (player_move is cls.RpsMove.PAPER and opponent_move is cls.RpsMove.ROCK) or \
           (player_move is cls.RpsMove.SCISSORS and opponent_move is cls.RpsMove.PAPER):
            game.score["player"] += 1
            return GameResult.WIN
        else:
            game.score["opponent"] += 1
            return GameResult.LOSE

    @GameHandler.opponent_strategy
    def always_rock(cls, game: Game, player_move: RpsMove = None) -> RpsMove:
        return cls.RpsMove.ROCK

    @GameHandler.opponent_strategy
    def always_paper(cls, game: Game, player_move: RpsMove = None) -> RpsMove:
        return cls.RpsMove.PAPER

    @GameHandler.opponent_strategy
    def always_scissors(cls, game: Game, player_move: RpsMove = None) -> RpsMove:
        return cls.RpsMove.SCISSORS

    @GameHandler.opponent_strategy
    def force_win(cls, game: Game, player_move: RpsMove) -> RpsMove:
        if player_move is cls.RpsMove.ROCK:
            return cls.RpsMove.PAPER
        elif player_move is cls.RpsMove.PAPER:
            return cls.RpsMove.SCISSORS
        else:  # player_move == RpsGameHandler.Choice.SCISSORS
            return cls.RpsMove.ROCK

    @GameHandler.opponent_strategy
    def force_lose(cls, game: Game, player_move: RpsMove) -> RpsMove:
        if player_move is RpsGameHandler.RpsMove.ROCK:
            return RpsGameHandler.RpsMove.SCISSORS
        elif player_move is RpsGameHandler.RpsMove.PAPER:
            return RpsGameHandler.RpsMove.ROCK
        else:  # player_move == RpsGameHandler.Choice.SCISSORS
            return RpsGameHandler.RpsMove.PAPER

class RpsGame(Game):
    game_handler_cls = RpsGameHandler

class RpslsGameHandler(GameHandler):
    """
    Extends the existing rules of Rock-Paper-Scissors with Lizard and Spock moves.

    Rock crushes scissors and crushes lizard, scissors cuts paper and decapitates lizard, paper covers rock and disproves Spock, lizard poisons Spock and eats paper, Spock smashes scissors and vaporizes rock.

    RPS can be further extended to any odd number, n*2+1, of moves as long as each move beats n of the other moves.
    """
    class RpslsMove( Enum ):
        ROCK = "rock"
        PAPER = "paper"
        SCISSORS = "scissors"
        LIZARD = "lizard"
        SPOCK = "spock"

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
        return list(cls.RpslsMove)

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

    @GameHandler.opponent_strategy
    def force_win(cls, game: Game, player_move: RpslsMove) -> RpslsMove:
        for move, beats in cls.WINNING_RPSLMOVES.items():
            if player_move in beats:
                return move
        # fallback
        return cls.make_random_move()

    @GameHandler.opponent_strategy
    def force_lose(cls, game: Game, player_move: RpslsMove) -> RpslsMove:
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
