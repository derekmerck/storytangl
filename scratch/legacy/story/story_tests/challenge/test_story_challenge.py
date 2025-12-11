import pytest
from tangl.story.scene.challenge_block import Challenge
from tangl.games.game_handler import GameStatus
from tangl.games.trivial_game import TrivialGameHandler
from tangl.games.rps_game import RPSGameHandler

def test_trivial_challenge():
    game_handler = TrivialGameHandler()
    challenge = Challenge(game_handler=game_handler, text="You are playing a trivial game. Will you win or lose?")

    # Test the text of the challenge
    assert challenge.text == "You are playing a trivial game. Will you win or lose?"

    # Test the possible actions
    assert set(challenge.get_possible_choices()) == set(list(TrivialGameHandler.Choice))

    # Test handling an action
    challenge.handle_choice(TrivialGameHandler.Choice.WIN)
    assert game_handler.score == {"user": 1, "opponent": 0}

    # Test that the game handler's state has been updated
    assert game_handler.round == 1

    # Continue the game until its end and check the final state
    challenge.handle_choice(TrivialGameHandler.Choice.WIN)
    challenge.handle_choice(TrivialGameHandler.Choice.WIN)
    assert game_handler.score == {"user": 3, "opponent": 0}
    assert game_handler.game_status is GameStatus.WON

def test_rps_challenge_always_win():
    game_handler = RPSGameHandler(opponent_strategy=RPSGameHandler.always_lose_strategy)
    challenge = Challenge(game_handler=game_handler, text="You are playing a game of Rock-Paper-Scissors.")

    # Test the text of the challenge
    assert challenge.text == "You are playing a game of Rock-Paper-Scissors."

    # Test the possible actions
    assert set(challenge.get_possible_choices()) == set(list(RPSGameHandler.Choice))

    # Test handling an action
    challenge.handle_choice(RPSGameHandler.Choice.ROCK)
    assert game_handler.score == {"user": 1, "opponent": 0}

    # Test that the game handler's state has been updated
    assert game_handler.round == 1

    # Continue the game until its end and check the final state
    challenge.handle_choice(RPSGameHandler.Choice.ROCK)
    challenge.handle_choice(RPSGameHandler.Choice.ROCK)
    assert game_handler.score == {"user": 3, "opponent": 0}
    assert game_handler.game_status is GameStatus.WON

def test_rps_challenge_always_lose():
    game_handler = RPSGameHandler(opponent_strategy=RPSGameHandler.always_win_strategy)
    challenge = Challenge(game_handler=game_handler, text="You are playing a game of Rock-Paper-Scissors.")

    # Test handling an action
    challenge.handle_choice(RPSGameHandler.Choice.ROCK)
    assert game_handler.score == {"user": 0, "opponent": 1}

    # Test that the game handler's state has been updated
    assert game_handler.round == 1

    # Continue the game until its end and check the final state
    challenge.handle_choice(RPSGameHandler.Choice.ROCK)
    challenge.handle_choice(RPSGameHandler.Choice.ROCK)
    assert game_handler.score == {"user": 0, "opponent": 3}
    assert game_handler.game_status is GameStatus.LOST

from tangl.core.utils.cattrs_converter import NodeConverter

def test_challenge_deserializes():
    from tangl.story.scene import Block

    print( Block._subclass_map )
    assert 'Challenge' in Block._subclass_map

    challenge = Challenge(label="challenge1", text="Block Text")
    assert challenge.text == "Block Text"

    cc = NodeConverter()
    data = cc.unstructure(challenge)

    from pprint import pprint
    pprint( data )

    assert data['node_cls'] == "Challenge"
    restored_challenge = cc.structure( data, Block )
    assert challenge == restored_challenge
    assert isinstance(restored_challenge, Challenge)

