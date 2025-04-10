from enum import Enum

from pydantic import Field

from tangl.mechanics.games.game_handler import GameHandler, Game, GameResult
from .playing_card import PlayingCard
from .card_game import CardGame, CardGroup


class TwentyOneGameHandler(GameHandler):
    """
    Handler for a simplified version of Blackjack (21).

    Get as close as possible to a target score given a randomly dealt hand.

    It is essentially a _solo_ card game since dealer/opponent moves are
    deterministic under the default 'casino' strategy.
    """
    # todo: implement force_win and force_lose opponent 'strategies' that affect outcome

    class TwentyOneMove(Enum):
        NO_MOVE = 0
        STAND = 1
        HIT = 2

    @classmethod
    def get_possible_moves(cls, game: Game) -> list[TwentyOneMove]:
        return [cls.TwentyOneMove.HIT, cls.TwentyOneMove.STAND]

    @classmethod
    def _resolve_round(cls, game: Game, player_move: TwentyOneMove, opponent_move: TwentyOneMove = None) -> GameResult:
        player_score = PlayingCard.sum(game.player_hand)
        opponent_score = PlayingCard.sum(game.opponent_hand)

        if player_score > 21:
            return GameResult.LOSE
        elif player_score == 21:
            return GameResult.WIN

        if player_move == cls.TwentyOneMove.STAND:
            while opponent_score < 17 or (opponent_score < player_score and opponent_score < 21):
                game.opponent_hand.append(game.card_deck.pop())
                opponent_score = PlayingCard.sum(game.opponent_hand)

            if opponent_score > 21:
                return GameResult.WIN
            elif player_score > opponent_score:
                return GameResult.WIN
            elif player_score < opponent_score:
                return GameResult.LOSE
            else:
                return GameResult.DRAW

        return GameResult.IN_PROCESS

    @classmethod
    def handle_player_move(cls, game: Game, player_move: TwentyOneMove) -> GameResult:
        if player_move == cls.TwentyOneMove.HIT:
            game.player_hand.append(game.card_deck.pop())
            return cls._resolve_round(game, player_move)
        elif player_move == cls.TwentyOneMove.STAND:
            return cls._resolve_round(game, player_move)

    @classmethod
    def setup_game(cls, game: Game):
        super().setup_game(game)
        game.player_hand = [game.card_deck.pop(), game.card_deck.pop()]
        game.opponent_hand = [game.card_deck.pop(), game.card_deck.pop()]


class TwentyOneGame(CardGame):
    game_handler_cls = TwentyOneGameHandler
    card_deck: CardGroup = Field(default_factory=PlayingCard.fresh_deck, json_schema_extra={'reset_field': True})
    player_hand: CardGroup = Field(default_factory=list, json_schema_extra={'reset_field': True})
    opponent_hand: CardGroup = Field(default_factory=list, json_schema_extra={'reset_field': True})
