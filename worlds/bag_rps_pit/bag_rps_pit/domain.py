from __future__ import annotations

from uuid import UUID

from tangl.mechanics.games import HasGame
from tangl.mechanics.games.bag_rps_game import BagRpsGame, BagRpsGameHandler
from tangl.story import Block


class PitBagRpsGame(BagRpsGame):
    """Deterministic Bag-RPS setup for the demo world."""

    player_opening_reserve: dict[str, int] = {"rock": 2}
    opponent_opening_reserve: dict[str, int] = {"paper": 1}
    max_commit_size: int = 2
    opponent_strategy: str = "aggregate_force_greedy"


class BagRpsPitBlock(HasGame, Block):
    """Story block hosting the aggregate-force pit proof."""

    _game_class = PitBagRpsGame
    _game_handler_class = BagRpsGameHandler


BagRpsPitBlock.model_rebuild(_types_namespace={"UUID": UUID})
