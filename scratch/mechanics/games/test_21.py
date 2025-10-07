
from tangl.mechanics.games.basic_game import BasicGame
from tangl.mechanics.games.basic_player import BasicMove
from tangl.mechanics.games.enums import Result

from tangl.mechanics.games.rps import RpsGame, RpsMove, Rps5Game
from tangl.mechanics.games.twentyone import TwentyOneGame, TwentyOneMove
from tangl.mechanics.games.twentytwo import TwentyTwoGame, MndCard

# import pytest

def test_21_game():

    game = TwentyOneGame()

    print( game.player )
    print( game.opponent )
    print( game.text() )
    assert game.game_status == Result.CONT

    game.advance( player_move=TwentyOneMove.HIT )  # hit me!
    print( game.text() )


def test_22_game():

    deck = MndCard.fresh_deck( [3, -3], [['a', 'b'], ['d', 'e']])
    print( deck, len( deck ) )

    # x3 x3 x2 x2 = 36
    assert len( deck ) == 36

    total = MndCard.sum( deck )
    print( total )

    # (1 + 2 + 3) * 3 * 2 * 2 = 72
    assert total == [72, -72]
    assert sum( total ) == 0  # b/c symmetric

# def test_seige():
#
#     R1 = BagRpsItem(move_typ=Move.ROCK)
#     S1 = BagRpsItem(move_typ=Move.SCISSORS)
#     P1 = BagRpsItem(move_typ=Move.PAPER)
#
#     print( BagRpsItem._instances )
#
#     b1 = BagRpsCollection( R1=2, S1=3 )
#
#     print( b1 )
#     print( b1.move_typ )
#
#     assert b1.move_typ == Move.SCISSORS
#
#     b2 = BagRpsCollection( S1=1, P1=3 )
#
#     brps = BagRpsGame()
#     brps.player1.reserve = b1
#     brps.player2.reserve = b2
#
#     brps.do_round()
#
#     print( brps )
