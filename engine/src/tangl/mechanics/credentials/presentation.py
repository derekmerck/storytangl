"""Text presentation defaults for graph-backed credential documents."""

from __future__ import annotations

from tangl.story.dispatch import on_render_text
from tangl.vm.ctx import VmPhaseCtx

from .assembly import CredentialComponent


@on_render_text(wants_caller_kind=CredentialComponent, wants_exact_kind=False)
def render_identity_document_text(
    *,
    caller: CredentialComponent,
    aspect: str,
    ctx: VmPhaseCtx,
) -> str | None:
    """Provide a neutral document description for one identity component."""
    _ = ctx
    if aspect != "document_description" or caller.document_kind != "id":
        return None
    return (
        "{{ subject.name or 'identity document' }}, bearing a portrait of "
        "{{ render_as(packet.resolve_subject(subject.subject_id), "
        "'presence_description') }}"
    )


__all__ = ["render_identity_document_text"]
