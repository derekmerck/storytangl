from builtins import print

import pytest

from tangl.mechanics.games.game_handler import Game, GameResult, GameHandler
from tangl.mechanics.games.simple_games.rps_game import RpsGameHandler as RPS_GH, RpslsGameHandler as RPSLS_GH, RpsMove, RpslsMove

pytest.skip(allow_module_level=True)

class RpsGame(Game):
    game_handler_cls = RPS_GH

def test_rps_game_handler1():
    game = RpsGame()
    Move = RpsMove

    # Test initial state
    assert game.round == 1
    assert game.score == {"player": 0, "opponent": 0}

    # Test handling actions
    for _ in range(3):
        RPS_GH.handle_player_move(game, Move.ROCK)
        assert game.round >= 2 and game.round <= 4

    # Test game over
    assert RPS_GH.check_game_result(game) in {GameResult.WIN, GameResult.LOSE, GameResult.DRAW}

def test_rps_game_handler2():

    game = RpsGame()
    Move = RpsMove

    game.handle_player_move( player_move=Move.ROCK )
    assert game.result is GameResult.IN_PROCESS
    while game.result is GameResult.IN_PROCESS:
        game.handle_player_move(player_move=Move.PAPER)

    # reset and do it again

    game.reset_fields()

    # Test initial state
    assert game.round == 1
    assert game.score == {"player": 0, "opponent": 0}

    game.opponent_next_move = Move.SCISSORS
    game.handle_player_move( Move.ROCK )

    assert game.round == 2
    assert game.round_result is GameResult.WIN
    assert game.score == {"player": 1, "opponent": 0}
    assert game.result is GameResult.IN_PROCESS

    game.opponent_next_move = Move.SCISSORS
    game.handle_player_move( Move.PAPER )

    assert game.round == 3
    assert game.round_result is GameResult.LOSE
    assert game.score == {"player": 1, "opponent": 1}
    assert game.result is GameResult.IN_PROCESS

    game.opponent_next_move = Move.ROCK
    game.handle_player_move( Move.PAPER )
    assert game.score == {"player": 2, "opponent": 1}
    assert game.round_result is GameResult.WIN
    assert game.result is GameResult.WIN


class RpslsGame(Game):
    game_handler_cls = RPSLS_GH

def test_rpsls_game_handler():
    # Create a new game handler
    game = RpslsGame()
    handler = RPSLS_GH
    Move = RpslsMove

    # Test initial state
    assert game.round == 1
    assert game.score == {"player": 0, "opponent": 0}
    assert handler.check_game_result(game) == GameResult.IN_PROCESS

    # Test handling actions
    handler.handle_player_move(game, Move.ROCK)
    assert game.round == 2
    # The outcome of the round depends on the random choice of the opponent, so we can't assert on the score.

    handler.handle_player_move(game, Move.SPOCK)
    assert game.round == 3
    # Again, the score can't be asserted on because of the randomness.

    # Simulate a game where user always chooses ROCK, until game is over
    while handler.check_game_result(game) == GameResult.IN_PROCESS:
        handler.handle_player_move(game, Move.ROCK)

    # At this point, the game must be over
    assert RPS_GH.check_game_result(game) in {GameResult.WIN, GameResult.LOSE, GameResult.DRAW}
    # Note: We can't assert the exact status, because it depends on the opponent's random moves.

def test_rpsls_game_handler2():

    game = RpslsGame()
    handler = RPSLS_GH
    Move = RpslsMove

    # Test handling actions
    game.opponent_next_move = Move.SPOCK
    handler.handle_player_move(game, Move.LIZARD)

    assert game.score == {"player": 1, "opponent": 0}  # lizard beats spock
    assert game.round_result is GameResult.WIN
    assert game.result is GameResult.IN_PROCESS

def test_opponent_move_strategy():
    game = RpsGame(opponent_move_strategy="always_rock")
    Move = RpsMove

    assert game.opponent_next_move is Move.ROCK

    RPS_GH.handle_player_move(game, Move.PAPER)  # Player should win against rock
    assert game.score["player"] == 1
    assert game.score["opponent"] == 0

    RPS_GH.handle_player_move(game, Move.SCISSORS)  # Player should lose against rock
    assert game.score["player"] == 1
    assert game.score["opponent"] == 1


def test_change_of_opponent_strategy():
    game = RpsGame(opponent_move_strategy="always_rock",
                   opponent_revise_move_strategy="always_paper")
    Move = RpsMove

    assert game.opponent_next_move is Move.ROCK

    # First round with the initial strategy
    RPS_GH.handle_player_move(game, Move.PAPER)
    assert game.history[0] == (Move.PAPER, Move.PAPER, GameResult.DRAW)
    assert game.score["player"] == 0
    assert game.score["opponent"] == 0


def test_invalid_opponent_next_move_strategy():
    with pytest.raises((KeyError, ValueError)):
        game = RpsGame(opponent_move_strategy="non_existent_strategy")
