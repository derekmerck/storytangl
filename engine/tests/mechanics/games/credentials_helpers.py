"""Manager-backed credential case constructors for game tests."""

from __future__ import annotations

from collections.abc import Sequence

from tangl.mechanics.credentials import (
    ContrabandItem,
    CredentialToken,
    Indication,
    IndicationId,
    OriginId,
    Region,
    materialize_packet,
)
from tangl.mechanics.games.credentials_game import CredentialCase


def make_credential_case(
    *,
    region: OriginId = Region.LOCAL,
    purpose: IndicationId = Indication.TRAVEL,
    id_card: CredentialToken | None = None,
    packet: Sequence[CredentialToken] = (),
    possessions: Sequence[ContrabandItem] = (),
    **case_fields: object,
) -> CredentialCase:
    """Construct a test case with one unhosted assembly packet manager."""

    candidate_name = str(case_fields.get("candidate_name", "Traveler"))
    packet_manager = case_fields.pop("packet_manager", None)
    return CredentialCase(
        packet_manager=packet_manager
        or materialize_packet(
            owner=object(),
            region=region,
            purpose=purpose,
            id_card=id_card,
            credentials=list(packet),
            possessions=list(possessions),
            label_prefix=candidate_name,
        ),
        **case_fields,
    )
