from __future__ import annotations

from uuid import UUID

from tangl.mechanics.games import HasGame
from tangl.mechanics.games.blackjack_game import BlackjackGame, BlackjackGameHandler
from tangl.story import Block


class ParlourBlackjackGame(BlackjackGame):
    """Deterministic blackjack configuration for the demo world."""

    shuffle_seed: int = 1
    deal_bias: str = "player_advantage"
    reveal_policy: str = "upcard"
    dealer_stand_at: int = 17


class BlackjackBlock(HasGame, Block):
    """Story block that hosts the parlour blackjack hand."""

    _game_class = ParlourBlackjackGame
    _game_handler_class = BlackjackGameHandler


BlackjackBlock.model_rebuild(_types_namespace={"UUID": UUID})
