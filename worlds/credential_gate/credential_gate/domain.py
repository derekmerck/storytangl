from __future__ import annotations

from uuid import UUID

from tangl.mechanics.games import HasGame
from tangl.mechanics.games.credentials_game import (
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
)
from tangl.story import Block


class GateCredentialsGame(CredentialsGame):
    """Deterministic credentials setup for the demo world."""

    correct_disposition: CredentialDisposition = CredentialDisposition.DENY


class CredentialGateBlock(HasGame, Block):
    """Story block hosting the staged credentials proof."""

    _game_class = GateCredentialsGame
    _game_handler_class = CredentialsGameHandler


CredentialGateBlock.model_rebuild(_types_namespace={"UUID": UUID})
