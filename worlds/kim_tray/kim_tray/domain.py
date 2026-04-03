from __future__ import annotations

from uuid import UUID

from tangl.mechanics.games import HasGame
from tangl.mechanics.games.kim_game import KimGame, KimGameHandler
from tangl.story import Block


class TrayKimGame(KimGame):
    """Deterministic Kim's Game setup for the demo world."""

    missing_item: str = "silver thimble"


class KimTrayBlock(HasGame, Block):
    """Story block hosting the Kim tray proof."""

    _game_class = TrayKimGame
    _game_handler_class = KimGameHandler


KimTrayBlock.model_rebuild(_types_namespace={"UUID": UUID})
