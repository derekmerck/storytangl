"""Presentation-safe media requests for one credential ID card."""

from __future__ import annotations

from tangl.media import CompositionInputRef, CompositionSpec, PrintableTextSpec
from tangl.media.media_creators.portrait_spec import PortraitSpec
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.mechanics.presence.look import HasSimpleLook, portrait_spec_from_look

from .presentation import CredentialCardProjection


def credential_card_portrait_spec(
    projection: CredentialCardProjection,
    subject: HasSimpleLook,
) -> PortraitSpec:
    """Build the recorded document subject's renderer-neutral portrait request."""
    if subject.uid != projection.subject_id:
        raise ValueError("Credential-card portrait subject does not match projection")
    payload = subject.adapt_look_media_spec(media_role="id_photo")
    return portrait_spec_from_look(payload, identity_key=str(projection.subject_id))


def credential_card_text_spec(projection: CredentialCardProjection) -> PrintableTextSpec:
    """Build the card's ordered, presentation-safe printed wording."""
    return PrintableTextSpec(
        label="credential_card_text",
        lines=(
            projection.document_label,
            projection.bearer_label,
            *(part.content for part in projection.visible_parts),
        ),
    )


def credential_card_composition_spec(
    *,
    portrait_rit: MediaRIT,
    text_rit: MediaRIT,
) -> CompositionSpec:
    """Compose resolved portrait and printable-text resources into one ID card."""
    portrait_hash = portrait_rit.get_content_hash()
    text_hash = text_rit.get_content_hash()
    if portrait_hash is None or text_hash is None:
        raise ValueError("Credential-card composition requires resolved child content")
    return CompositionSpec(
        label="credential_card",
        inputs=[
            CompositionInputRef(
                role="portrait",
                rit_id=portrait_rit.uid,
                content_hash=portrait_hash,
                offset=(16, 32),
            ),
            CompositionInputRef(
                role="printable_text",
                rit_id=text_rit.uid,
                content_hash=text_hash,
                offset=(176, 16),
            ),
        ],
        canvas_size=(512, 192),
        background="white",
        treatment="credential_id_card",
    )
