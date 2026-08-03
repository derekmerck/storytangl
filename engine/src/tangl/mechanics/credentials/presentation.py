"""Text presentation defaults for graph-backed credential documents."""

from __future__ import annotations

from typing import Literal, TypeAlias
from uuid import UUID

from pydantic import ConfigDict

from tangl.core.bases import BaseModelPlus
from tangl.story.dispatch import on_render_text
from tangl.vm.ctx import VmPhaseCtx

from .assembly import CredentialComponent, CredentialPacketManager


class CredentialAttestationObservation(BaseModelPlus):
    """One neutral, visible issuer-attestation observation on a document."""

    model_config = ConfigDict(frozen=True)

    part_id: Literal["issuer_attestation"] = "issuer_attestation"
    content: str


class CredentialValidityObservation(BaseModelPlus):
    """One neutral, visible validity observation on a document."""

    model_config = ConfigDict(frozen=True)

    part_id: Literal["validity"] = "validity"
    content: str


CredentialVisibleObservation: TypeAlias = (
    CredentialAttestationObservation | CredentialValidityObservation
)


class CredentialCardProjection(BaseModelPlus):
    """Projection data for future credential-card renderers.

    Why:
        Keep presentation data separate from credential evaluation and mutation.

    Key Features:
        Preserve canonical IDs, scenario labels, and ordered visible observations.

    API:
        ``CredentialsGameHandler.credential_card_projections()`` produces this
        value from the canonical ID document render.

    Notes:
        This model excludes validity, defect, policy, and outcome state.

    See also:
        ``CredentialVisibleObservation`` for the ordered visible document parts.
    """

    model_config = ConfigDict(frozen=True)

    component_id: UUID
    subject_id: UUID
    document_kind: str
    document_label: str
    bearer_label: str
    visible_parts: tuple[CredentialVisibleObservation, ...]


@on_render_text(wants_caller_kind=CredentialPacketManager, wants_exact_kind=False)
def render_packet_text(
    *,
    caller: CredentialPacketManager,
    aspect: str,
    ctx: VmPhaseCtx,
) -> str | None:
    """Compose one packet through its ordered document descriptions."""
    _ = caller, ctx
    if aspect != "inspection_description":
        return None
    return (
        "{% set presented = subject.document_components() %}"
        "{% set replacements = document_replacements | default({}) %}"
        "{% set bases = document_bases | default({}) %}"
        "{% set observations = document_observations | default({}) %}"
        "{% if presented %}"
        "{% for document in presented %}"
        "{{ render_as(document, 'document_description', "
        "content=replacements.get(document.uid), bindings={'packet': subject, "
        "'base_description': bases.get(document.uid), "
        "'visible_observations': observations.get(document.uid, ())}) }}"
        "{% if not loop.last %}; {% endif %}"
        "{% endfor %}"
        "{% else %}No documents.{% endif %}"
    )


@on_render_text(wants_caller_kind=CredentialComponent, wants_exact_kind=False)
def render_document_text(
    *,
    caller: CredentialComponent,
    aspect: str,
    ctx: VmPhaseCtx,
) -> str | None:
    """Provide a neutral document description for one credential component."""
    _ = ctx
    if aspect != "document_description":
        return None
    if caller.document_kind == "id":
        return (
            "{% set base = base_description | default(subject.name or 'identity document', true) %}"
            "{{ base }}, bearing a portrait of "
            "{{ render_as(packet.resolve_subject(subject.subject_id), "
            "'presence_description') }}"
            "{% for observation in visible_observations | default(()) %}; "
            "{{ render_as(observation, 'part_description') }}{% endfor %}"
        )
    return (
        "{% set base = base_description | default(subject.name or "
        "(subject.indication | replace('_', ' ') ~ ' document'), true) %}"
        "{{ base }}{% for observation in visible_observations | default(()) %}; "
        "{{ render_as(observation, 'part_description') }}{% endfor %}"
    )


@on_render_text(wants_caller_kind=CredentialAttestationObservation, wants_exact_kind=False)
def render_attestation_text(
    *,
    caller: CredentialAttestationObservation,
    aspect: str,
    ctx: VmPhaseCtx,
) -> str | None:
    """Render the authored visible wording for one issuer attestation."""

    _ = ctx
    return caller.content if aspect == "part_description" else None


@on_render_text(wants_caller_kind=CredentialValidityObservation, wants_exact_kind=False)
def render_validity_text(
    *,
    caller: CredentialValidityObservation,
    aspect: str,
    ctx: VmPhaseCtx,
) -> str | None:
    """Render the authored visible wording for one document validity line."""

    _ = ctx
    return caller.content if aspect == "part_description" else None


__all__ = [
    "CredentialAttestationObservation",
    "CredentialCardProjection",
    "CredentialValidityObservation",
    "CredentialVisibleObservation",
    "render_attestation_text",
    "render_document_text",
    "render_packet_text",
    "render_validity_text",
]
