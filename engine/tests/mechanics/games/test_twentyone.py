import pytest

from tangl.mechanics.game.enums import GameResult
from tangl.mechanics.game.card_games.twentyone_game import TwentyOneGame, TwentyOneGameHandler, PlayingCard

TwentyOneMove = TwentyOneGameHandler.TwentyOneMove

def test_twentyone():
    # Example Usage

    # Create a new game
    game = TwentyOneGame()

    # Display initial hands
    print(f"Player's hand: {[str(card) for card in game.player_hand]}")
    print(f"Dealer's hand: {str(game.opponent_hand[0])} (hidden)")

    # Player makes a move
    result = game.handle_player_move(TwentyOneMove.HIT)
    print(f"Player's hand after hit: {[str(card) for card in game.player_hand]}")

    # Continue making moves until the player decides to stand
    while result == GameResult.IN_PROCESS:
        # For example, let's hit again
        result = game.handle_player_move(TwentyOneMove.HIT)
        print(f"Player's hand: {[str(card) for card in game.player_hand]}")
        if PlayingCard.sum(game.player_hand) >= 21:
            break

    # Finally, the player decides to stand
    result = game.handle_player_move(TwentyOneMove.STAND)

    # Display final result
    print(f"Final result: {result}")
    print(f"Player's hand: {[str(card) for card in game.player_hand]} (score: {PlayingCard.sum(game.player_hand)})")
    print(f"Dealer's hand: {[str(card) for card in game.opponent_hand]} (score: {PlayingCard.sum(game.opponent_hand)})")
