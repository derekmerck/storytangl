"""Assembly-backed credential packet components."""

from __future__ import annotations

from typing import ClassVar

from pydantic import ConfigDict, Field

from tangl.core import Selector, Singleton, Token, TokenCatalog
from tangl.mechanics.assembly import ComponentFacet, ComponentManager, Slot

from .domain import (
    ContrabandItem,
    CredentialStatus,
    CredentialToken,
    IndicationId,
    OriginId,
    Region,
    Indication,
)

CREDENTIAL_ID_SLOT = "id"
CREDENTIAL_PACKET_SLOT = "credentials"
_DEFAULT_DOCUMENT_KINDS = ("id", "document")


class CredentialDefinition(Singleton):
    """Credential document definition used by graph-local credential tokens."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    catalog_id: str | None = None
    name: str | None = None
    origin_ids: tuple[OriginId, ...] = ()
    valid_period: int | None = None
    issuer_group: str | None = None
    indication: IndicationId
    document_kind: str = "document"
    requires_id: bool = False
    facets: tuple[ComponentFacet, ...] = ()
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

    def component_facets(
        self,
        *,
        channel: str | None = None,
        facet_type: str | None = None,
        subject_id: str | None = None,
    ) -> list[ComponentFacet]:
        """Return copied definition facets with token and packet provenance."""

        return [
            facet.model_copy(
                deep=True,
                update={
                    "source_id": str(self.uid),
                    "subject_id": subject_id,
                },
            )
            for facet in self.facets
            if facet.matches(channel=channel, facet_type=facet_type)
        ]

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

    region: OriginId = Region.LOCAL
    purpose: IndicationId = Indication.TRAVEL
    possessions: list[ContrabandItem] = Field(
        default_factory=list,
        json_schema_extra={"include": True},
    )

    def get_region(self) -> OriginId:
        return self.region

    def get_purpose(self) -> IndicationId:
        return self.purpose

    def id_status(self) -> CredentialStatus | None:
        id_card = self.id_credential()
        return id_card.status if id_card is not None else None

    def id_credential(self) -> CredentialToken | None:
        """Project the bearer-id component to the game compatibility shape."""

        id_card = self._id_component()
        return id_card.to_credential_token() if id_card is not None else None

    def credential_for(self, indication: IndicationId) -> CredentialToken | None:
        for token in self.document_credentials():
            if token.indication == indication:
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
        id_card = self.id_credential()
        if id_card is None:
            return credentials
        return [id_card, *credentials]

    def _id_component(self) -> CredentialComponent | None:
        components = self.get_slot(CREDENTIAL_ID_SLOT)
        return components[0] if components else None


def _definition_for(
    token: CredentialToken,
    *,
    document_kind: str,
    catalog: TokenCatalog[CredentialDefinition] | None,
) -> CredentialDefinition:
    """Return the stable definition behind one materialized document token."""

    catalog = catalog or default_credential_catalog()
    selector = (
        Selector(catalog_id=token.definition_ref)
        if token.definition_ref is not None
        else Selector(
            document_kind=document_kind,
            indication=token.indication,
            requires_id=token.requires_id,
        )
    )
    definitions = list(catalog.find_all(selector))
    if len(definitions) != 1:
        target = token.definition_ref or (
            f"{document_kind}/{token.indication}/"
            f"{'requires-id' if token.requires_id else 'standalone'}"
        )
        raise ValueError(
            f"Credential catalog '{catalog.label or 'stock'}' has "
            f"{len(definitions)} definitions for {target}."
        )
    return definitions[0]


def _definition_label(
    *,
    document_kind: str,
    indication: IndicationId,
    requires_id: bool,
) -> str:
    return ":".join(
        (
            "credential",
            document_kind,
            indication,
            "requires-id" if requires_id else "standalone",
        )
    )


def _default_definition_facets(document_kind: str) -> tuple[ComponentFacet, ...]:
    if document_kind == "document":
        return (
            ComponentFacet(
                channel="choice",
                facet_type="giver",
                payload="request_document",
            ),
        )
    return ()


def ensure_default_credential_definitions() -> None:
    """Load the finite definition catalog used by generated credential packets."""

    for document_kind in _DEFAULT_DOCUMENT_KINDS:
        for indication in (
            "travel",
            "work",
            "emigrate",
            "weapon",
            "drugs",
            "secrets",
        ):
            for requires_id in (False, True):
                label = _definition_label(
                    document_kind=document_kind,
                    indication=indication,
                    requires_id=requires_id,
                )
                if CredentialDefinition.get_instance(label) is None:
                    CredentialDefinition(
                        label=label,
                        indication=indication,
                        document_kind=document_kind,
                        requires_id=requires_id,
                        facets=_default_definition_facets(document_kind),
                    )


def default_credential_catalog() -> TokenCatalog[CredentialDefinition]:
    """Return the bounded stock catalog used by unconfigured compatibility games."""

    ensure_default_credential_definitions()
    definitions = []
    for document_kind in _DEFAULT_DOCUMENT_KINDS:
        for indication in ("travel", "work", "emigrate", "weapon", "drugs", "secrets"):
            for requires_id in (False, True):
                label = _definition_label(
                    document_kind=document_kind,
                    indication=indication,
                    requires_id=requires_id,
                )
                definition = CredentialDefinition.get_instance(label)
                assert definition is not None
                definitions.append(definition)
    return TokenCatalog(
        wst=CredentialDefinition,
        members=tuple(definitions),
        label="stock",
    )


def materialize_packet(
    *,
    owner: object,
    region: OriginId,
    purpose: IndicationId,
    id_card: CredentialToken | None,
    credentials: list[CredentialToken],
    possessions: list[ContrabandItem],
    label_prefix: str,
    catalog: TokenCatalog[CredentialDefinition] | None = None,
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
        definition = _definition_for(
            token,
            document_kind=document_kind,
            catalog=catalog,
        )
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
    "ensure_default_credential_definitions",
    "materialize_packet",
]


ensure_default_credential_definitions()
