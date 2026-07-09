"""Assembly-backed credential packet components."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from tangl.core import Singleton, Token
from tangl.mechanics.assembly import ComponentManager, Slot
from tangl.type_hints import UnstructuredData

from .domain import (
    ContrabandItem,
    CredentialStatus,
    CredentialToken,
    Indication,
    Region,
)

CREDENTIAL_ID_SLOT = "id"
CREDENTIAL_PACKET_SLOT = "credentials"


class CredentialDefinition(Singleton):
    """Credential document definition used by graph-local credential tokens."""

    indication: Indication
    document_kind: str = "document"
    requires_id: bool = False
    status: CredentialStatus = Field(
        default=CredentialStatus.VALID,
        json_schema_extra={"instance_var": True},
    )
    holder_matches: bool = Field(
        default=True,
        json_schema_extra={"instance_var": True},
    )


class CredentialComponentToken(Token):
    """Graph credential token that projects to the legacy packet value shape."""

    def get_label(self) -> str:
        return self.token_from or self.label

    def to_credential_token(self) -> CredentialToken:
        """Return the compatibility value read by disposition derivation."""

        return CredentialToken(
            indication=self.indication,
            status=self.status,
            requires_id=self.requires_id,
            holder_matches=self.holder_matches,
        )


CredentialComponent = CredentialComponentToken._create_wrapper_cls(
    CredentialDefinition,
    "CredentialComponent",
)


def _is_id_document(component: CredentialComponentToken) -> bool:
    return component.document_kind == "id"


def _is_packet_document(component: CredentialComponentToken) -> bool:
    return component.document_kind != "id"


class CredentialPacketManager(ComponentManager[CredentialComponent]):
    """Owner-bound packet manager over credential graph components."""

    slots: ClassVar[dict[str, Slot]] = {
        CREDENTIAL_ID_SLOT: Slot.for_predicate(
            CREDENTIAL_ID_SLOT,
            _is_id_document,
            max_count=1,
        ),
        CREDENTIAL_PACKET_SLOT: Slot.for_predicate(
            CREDENTIAL_PACKET_SLOT,
            _is_packet_document,
            max_count=100,
        ),
    }

    region: Region = Region.LOCAL
    purpose: Indication = Indication.TRAVEL
    possessions: list[ContrabandItem] = Field(default_factory=list)

    def get_region(self) -> Region:
        return self.region

    def get_purpose(self) -> Indication:
        return self.purpose

    def id_status(self) -> CredentialStatus | None:
        id_card = self._id_component()
        return id_card.status if id_card is not None else None

    def credential_for(self, indication: Indication) -> CredentialToken | None:
        for credential in self.get_slot(CREDENTIAL_PACKET_SLOT):
            token = credential.to_credential_token()
            if token.indication is indication:
                return token
        return None

    def get_contraband(self) -> list[ContrabandItem]:
        return list(self.possessions)

    def all_credentials(self) -> list[CredentialToken]:
        credentials = [
            credential.to_credential_token()
            for credential in self.get_slot(CREDENTIAL_PACKET_SLOT)
        ]
        id_card = self._id_component()
        if id_card is None:
            return credentials
        return [id_card.to_credential_token(), *credentials]

    def _id_component(self) -> CredentialComponent | None:
        components = self.get_slot(CREDENTIAL_ID_SLOT)
        return components[0] if components else None

    def unstructure(self) -> UnstructuredData:
        data = super().unstructure()
        if self.region is not Region.LOCAL:
            data["region"] = self.region.value
        if self.purpose is not Indication.TRAVEL:
            data["purpose"] = self.purpose.value
        if self.possessions:
            data["possessions"] = [
                possession.model_dump(mode="json", exclude_defaults=True)
                for possession in self.possessions
            ]
        return data


__all__ = [
    "CREDENTIAL_ID_SLOT",
    "CREDENTIAL_PACKET_SLOT",
    "CredentialComponent",
    "CredentialComponentToken",
    "CredentialDefinition",
    "CredentialPacketManager",
]
