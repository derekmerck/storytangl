from __future__ import annotations

from uuid import UUID

from pydantic import Field

from tangl.mechanics.games import HasGame
from tangl.mechanics.games.credentials_enums import (
    CredentialStatus,
    CredentialToken,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
)
from tangl.mechanics.games.credentials_game import (
    CredentialCase,
    CredentialsGame,
    CredentialsGameHandler,
)
from tangl.story import Block


# The day's rules for this checkpoint. Travel needs a valid id; work needs a
# permit (which also needs id). The candidates' dispositions are *derived* from
# these rules and each packet's structured truth -- not authored.
GATE_RULES = {
    Region.LOCAL: {
        Indication.TRAVEL: RestrictionLevel.WITH_ID,
        Indication.WORK: RestrictionLevel.WITH_PERMIT,
        Indication.EMIGRATE: RestrictionLevel.WITH_PERMIT,
        Indication.WEAPON: RestrictionLevel.WITH_PERMIT,
        Indication.DRUGS: RestrictionLevel.FORBIDDEN,
        Indication.SECRETS: RestrictionLevel.FORBIDDEN,
    },
}


def _gate_roster() -> list[CredentialCase]:
    """Three candidates whose dispositions derive to pass / deny / arrest.

    The narrative strings drive the inspect loop; the structured truth (region,
    purpose, id_card, packet) is what ``derive_disposition`` reads against
    ``GATE_RULES``.
    """

    return [
        # Tomas: travelling with a valid id -> derives PASS.
        CredentialCase(
            candidate_name="Tomas Vey",
            presented_documents={
                "passport": "A crisp passport, its seal sharp and current.",
            },
            hidden_facts={},
            packet_hidden_facts={},
            region=Region.LOCAL,
            purpose=Indication.TRAVEL,
            id_card=CredentialToken(
                indication=Indication.TRAVEL, status=CredentialStatus.VALID
            ),
        ),
        # Edda: here to work, valid id, but the work permit's seal is missing
        # (a mitigatable infraction) -> derives DENY.
        CredentialCase(
            candidate_name="Edda Marrow",
            presented_documents={
                "passport": "A worn passport with a current seal.",
                "work permit": "A work permit -- but where is the issuing seal?",
                "baggage": "A lacquered case with a stubborn clasp.",
            },
            hidden_facts={
                "work permit": "The work permit was never sealed by the issuer.",
            },
            packet_hidden_facts={
                "packet consistency": "An unsealed permit does not satisfy the work rule.",
            },
            region=Region.LOCAL,
            purpose=Indication.WORK,
            id_card=CredentialToken(
                indication=Indication.WORK, status=CredentialStatus.VALID
            ),
            packet=[
                CredentialToken(
                    indication=Indication.WORK,
                    status=CredentialStatus.MISSING_SEAL,
                    requires_id=True,
                ),
            ],
        ),
        # Goran: here to work with a forged work permit -> derives ARREST.
        CredentialCase(
            candidate_name="Goran Siv",
            presented_documents={
                "passport": "A passport whose photograph sits oddly on the page.",
                "work permit": "A work permit with an over-bright, wrong-toned seal.",
            },
            hidden_facts={
                "work permit": "The seal is a forgery -- the impression is fake.",
            },
            packet_hidden_facts={
                "packet consistency": "A forged permit is fabrication, not a clerical slip.",
            },
            region=Region.LOCAL,
            purpose=Indication.WORK,
            id_card=CredentialToken(
                indication=Indication.WORK, status=CredentialStatus.VALID
            ),
            packet=[
                CredentialToken(
                    indication=Indication.WORK,
                    status=CredentialStatus.FORGED,
                    requires_id=True,
                ),
            ],
        ),
    ]


class GateCredentialsGame(CredentialsGame):
    """Authored checkpoint shift for the demo world (dispositions derived)."""

    roster: list[CredentialCase] = Field(default_factory=_gate_roster)
    restriction_map: Restrictions = Field(
        default_factory=lambda: Restrictions.from_map(GATE_RULES)
    )


class CredentialGateBlock(HasGame, Block):
    """Story block hosting the staged credential shift."""

    _game_class = GateCredentialsGame
    _game_handler_class = CredentialsGameHandler


CredentialGateBlock.model_rebuild(_types_namespace={"UUID": UUID})
