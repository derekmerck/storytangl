from pydantic import ConfigDict

from tangl.mechanics.game.game_handler import GameHandler, Game
from .playing_card import PlayingCard, Suit

CardGroup = list[PlayingCard]

class CardGameHandler(GameHandler):
    """
    Poker, 21/22, Uno, Gwent?  Is Gwent just rock paper scissors?
    """
    # todo: card game framework

    @classmethod
    def _resolve_round(cls, game: Game, player_move, opponent_move):
        ...

    @classmethod
    def get_possible_moves(cls, game: Game):
        ...

class CardGame(Game):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    card_deck: CardGroup = None
    player_hand: CardGroup = None
    opponent_hand: CardGroup = None
    field_cards: CardGroup = None
    discards: CardGroup = None
