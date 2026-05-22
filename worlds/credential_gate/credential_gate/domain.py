from __future__ import annotations

from uuid import UUID

from pydantic import Field

from tangl.mechanics.games import HasGame
from tangl.mechanics.games.credentials_game import (
    CredentialCase,
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
)
from tangl.story import Block


def _gate_roster() -> list[CredentialCase]:
    """A three-candidate shift spanning each disposition.

    One clean traveler (pass), one whose seal is wrong (deny), and one whose
    packet is fabricated (arrest). The correct answers are authored per case;
    Phase A will later derive them from a restriction map.
    """

    return [
        CredentialCase(
            candidate_name="Tomas Vey",
            presented_documents={
                "passport": "A crisp passport, its seal sharp and current.",
                "travel permit": "A permit stamped for this very week.",
            },
            hidden_facts={},
            packet_hidden_facts={},
            correct_disposition=CredentialDisposition.PASS,
        ),
        CredentialCase(
            candidate_name="Edda Marrow",
            presented_documents={
                "passport": "A worn passport with a blurred seal.",
                "travel permit": "A permit stamped for this week.",
                "baggage": "A lacquered case with a stubborn clasp.",
            },
            hidden_facts={
                "passport": "The seal impression is wrong for this border.",
            },
            packet_hidden_facts={
                "packet consistency": "The documents do not satisfy this checkpoint's rules.",
            },
            correct_disposition=CredentialDisposition.DENY,
        ),
        CredentialCase(
            candidate_name="Goran Siv",
            presented_documents={
                "passport": "A passport whose photograph sits oddly on the page.",
                "travel permit": "A permit from an issuing office that closed years ago.",
            },
            hidden_facts={
                "passport": "The lamination has been lifted and re-set; the photo is swapped.",
                "travel permit": "The issuing seal belongs to a defunct authority -- a forgery.",
            },
            packet_hidden_facts={
                "packet consistency": "Two forged documents in one packet: this is fabricated.",
            },
            correct_disposition=CredentialDisposition.ARREST,
        ),
    ]


class GateCredentialsGame(CredentialsGame):
    """Authored checkpoint shift for the demo world."""

    roster: list[CredentialCase] = Field(default_factory=_gate_roster)


class CredentialGateBlock(HasGame, Block):
    """Story block hosting the staged credential shift."""

    _game_class = GateCredentialsGame
    _game_handler_class = CredentialsGameHandler


CredentialGateBlock.model_rebuild(_types_namespace={"UUID": UUID})
