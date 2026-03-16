from __future__ import annotations

from uuid import UUID

from tangl.mechanics.games import HasGame
from tangl.mechanics.games.rps_game import RpsGame, RpsGameHandler
from tangl.story import Block


class TavernRpsGame(RpsGame):
    """Deterministic tavern RPS configuration for the demo world."""

    scoring_n: int = 2
    scoring_strategy: str = "first_to_n"
    opponent_strategy: str = "rps_random"
    opponent_revision_strategy: str = "rps_throw"


class RpsBlock(HasGame, Block):
    """Story block that hosts the tavern Rock-Paper-Scissors game."""

    _game_class = TavernRpsGame
    _game_handler_class = RpsGameHandler


RpsBlock.model_rebuild(_types_namespace={"UUID": UUID})
