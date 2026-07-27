"""Text presentation defaults for graph-backed credential documents."""

from __future__ import annotations

from tangl.story.dispatch import on_render_text
from tangl.vm.ctx import VmPhaseCtx

from .assembly import (
    CREDENTIAL_ID_SLOT,
    CREDENTIAL_PACKET_SLOT,
    CredentialComponent,
    CredentialPacketManager,
)


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
        f"{{% set identity = subject.get_slot('{CREDENTIAL_ID_SLOT}') %}}"
        f"{{% set documents = subject.get_slot('{CREDENTIAL_PACKET_SLOT}') %}}"
        "{% set presented = identity + documents %}"
        "{% if presented %}"
        "{% for document in presented %}"
        "{{ render_as(document, 'document_description', bindings={'packet': subject}) }}"
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
            "{{ subject.name or 'identity document' }}, bearing a portrait of "
            "{{ render_as(packet.resolve_subject(subject.subject_id), "
            "'presence_description') }}"
        )
    return "{{ subject.name or (subject.indication | replace('_', ' ') ~ ' document') }}"


__all__ = ["render_document_text", "render_packet_text"]
