import pytest
from tangl.mechanics.game.enums import GameResult
from tangl.mechanics.game.trivial_game import TrivialGame, TrivialGameHandler as TGH


@pytest.fixture
def game():
    return TrivialGame()

@pytest.mark.xfail(raises=AssertionError, reason="Fails after 2->3 update")
def test_trivial_game_handler1(game):
    Move = TGH.WinLoseMove

    # Test initial game state
    assert game.score == {"player": 0, "opponent": 0}
    assert game.round == 1

    # Test get_possible_actions method
    assert set(game.get_possible_moves()) == {Move.WIN, Move.LOSE, Move.DRAW}

    # Test a round where the user wins
    game.opponent_next_move = Move.LOSE
    game.handle_player_move(Move.WIN)
    assert game.score == {"player": 2, "opponent": 0}
    assert game.round == 2

    # Test a round where the user loses
    game.opponent_next_move = Move.WIN
    game.handle_player_move(Move.LOSE)
    assert game.score == {"player": 2, "opponent": 2}
    assert game.round == 3

    # Test a round where it's a draw
    game.opponent_revise_move_strategy = "always_agree"
    game.handle_player_move(Move.DRAW)
    assert game.score == {"player": 3, "opponent": 3}
    assert game.round == 4

    # Test game over condition (assuming 'most_wins')
    assert game.result is GameResult.DRAW

    game.scoring_strategy = "points_after_n"
    assert game.result is GameResult.LOSE


def test_trivial_game_handler2():
    game = TrivialGame(scoring_strategy="first_to_n",
                       opponent_move_strategy="always_lose",
                       scoring_n=5)
    Move = TGH.WinLoseMove

    game.handle_player_move(Move.WIN)
    assert game.round_result == GameResult.WIN
    assert game.result == GameResult.IN_PROCESS

    game.handle_player_move(Move.WIN)
    assert game.round_result == GameResult.WIN
    assert game.result == GameResult.IN_PROCESS

    game.opponent_next_move = Move.WIN
    game.handle_player_move(Move.LOSE)
    assert game.round_result == GameResult.LOSE
    assert game.result == GameResult.IN_PROCESS

    game.handle_player_move(Move.WIN)
    assert game.round_result == GameResult.WIN, f"Not enough points {game.score}"
    assert game.result == GameResult.WIN


def test_trivial_game_handler_let_win():
    game = TrivialGame(opponent_move_strategy="always_lose",
                       scoring_strategy="best_of_n")
    Move = TGH.WinLoseMove

    assert game.result == GameResult.IN_PROCESS

    # Round 1
    game.handle_player_move(Move.WIN)
    assert game.result == GameResult.IN_PROCESS, f"Game is over {game.round}, {game.score}"
    assert game.score["player"] == 2
    assert game.score["opponent"] == 0

    # Round 2
    game.handle_player_move(Move.LOSE)
    assert game.result == GameResult.IN_PROCESS
    assert game.score["player"] == 3
    assert game.score["opponent"] == 1

    # Round 3
    game.handle_player_move(Move.WIN)
    assert game.result == GameResult.WIN
    assert game.score["player"] == 5
    assert game.score["opponent"] == 1


def test_trivial_game_handler_force_draw():
    game = TrivialGame(scoring_strategy="best_of_n")
    Move = TGH.WinLoseMove

    assert game.result == GameResult.IN_PROCESS

    # Round 1
    game.opponent_next_move = Move.DRAW
    game.handle_player_move(Move.DRAW)
    assert game.result == GameResult.IN_PROCESS
    assert game.score["player"] == 1
    assert game.score["opponent"] == 1

    # Round 2
    game.opponent_next_move = Move.DRAW
    game.handle_player_move(Move.DRAW)
    assert game.result == GameResult.IN_PROCESS
    assert game.score["player"] == 2
    assert game.score["opponent"] == 2

    # Round 3
    game.opponent_next_move = Move.DRAW
    game.handle_player_move(Move.DRAW)
    assert game.result == GameResult.DRAW
    assert game.score["player"] == 3
    assert game.score["opponent"] == 3

@pytest.mark.skip(reason="not sure")
def test_player_advantage():
    game = TrivialGame(difficulty=3)
    assert game.player_advantage == 0.2

    game.difficulty = 10
    assert game.player_advantage == 0

@pytest.mark.skip(reason="not sure")
def test_story_context_interaction(monkeypatch):
    game = TrivialGame()

    # Mock the player inventory
    class MockPlayer:
        inv = {"lucky_charm"}

    class MockGraph:
        player = MockPlayer()

    game.graph = MockGraph()

    # Mock random.random to always return 0 (ensuring player advantage is used)
    monkeypatch.setattr('random.random', lambda: 0)

    game.handle_player_move(TGH.WinLoseMove.WIN)
    assert game.opponent_move_strategy == "always_lose"