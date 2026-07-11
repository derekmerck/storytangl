"""Assembly-backed credential packet components."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from tangl.core import Singleton, Token
from tangl.mechanics.assembly import ComponentManager, Slot

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
    possessions: list[ContrabandItem] = Field(
        default_factory=list,
        json_schema_extra={"include": True},
    )

    def get_region(self) -> Region:
        return self.region

    def get_purpose(self) -> Indication:
        return self.purpose

    def id_status(self) -> CredentialStatus | None:
        id_card = self.id_credential()
        return id_card.status if id_card is not None else None

    def id_credential(self) -> CredentialToken | None:
        """Project the bearer-id component to the game compatibility shape."""

        id_card = self._id_component()
        return id_card.to_credential_token() if id_card is not None else None

    def credential_for(self, indication: Indication) -> CredentialToken | None:
        for token in self.document_credentials():
            if token.indication is indication:
                return token
        return None

    def document_credentials(self) -> list[CredentialToken]:
        """Project non-id credential components to the game compatibility shape."""

        return [
            credential.to_credential_token()
            for credential in self.get_slot(CREDENTIAL_PACKET_SLOT)
        ]

    def get_contraband(self) -> list[ContrabandItem]:
        return list(self.possessions)

    def all_credentials(self) -> list[CredentialToken]:
        credentials = self.document_credentials()
        id_card = self._id_component()
        if id_card is None:
            return credentials
        return [id_card.to_credential_token(), *credentials]

    def _id_component(self) -> CredentialComponent | None:
        components = self.get_slot(CREDENTIAL_ID_SLOT)
        return components[0] if components else None


def _definition_for(
    token: CredentialToken,
    *,
    document_kind: str,
) -> CredentialDefinition:
    """Return the stable definition behind one materialized document token."""

    label = ":".join(
        (
            "credential",
            document_kind,
            token.indication.value,
            "requires-id" if token.requires_id else "standalone",
        )
    )
    existing = CredentialDefinition.get_instance(label)
    if existing is not None:
        return existing
    return CredentialDefinition(
        label=label,
        indication=token.indication,
        document_kind=document_kind,
        requires_id=token.requires_id,
    )


def materialize_packet(
    *,
    owner: object,
    region: Region,
    purpose: Indication,
    id_card: CredentialToken | None,
    credentials: list[CredentialToken],
    possessions: list[ContrabandItem],
    label_prefix: str,
) -> CredentialPacketManager:
    """Create an owner-bound graph packet from a factory's value-shaped output."""

    manager = CredentialPacketManager(
        region=region,
        purpose=purpose,
        possessions=list(possessions),
    ).bind_owner(owner)

    def add_component(
        token: CredentialToken,
        *,
        document_kind: str,
        slot: str,
        index: int,
    ) -> None:
        definition = _definition_for(token, document_kind=document_kind)
        manager.assign(
            slot,
            CredentialComponent(
                label=f"{label_prefix}:{document_kind}:{index}",
                token_from=definition.label,
                status=token.status,
                holder_matches=token.holder_matches,
            ),
        )

    if id_card is not None:
        add_component(
            id_card,
            document_kind="id",
            slot=CREDENTIAL_ID_SLOT,
            index=0,
        )
    for index, credential in enumerate(credentials):
        add_component(
            credential,
            document_kind="document",
            slot=CREDENTIAL_PACKET_SLOT,
            index=index,
        )
    return manager


__all__ = [
    "CREDENTIAL_ID_SLOT",
    "CREDENTIAL_PACKET_SLOT",
    "CredentialComponent",
    "CredentialComponentToken",
    "CredentialDefinition",
    "CredentialPacketManager",
    "materialize_packet",
]
