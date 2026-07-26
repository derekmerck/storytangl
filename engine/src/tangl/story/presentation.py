"""Text presentation selection over the story dispatch chain."""

from __future__ import annotations

from collections.abc import Mapping

from tangl.mechanics.presence.look import HasLook, HasSimpleLook, Look
from tangl.mechanics.presence.ornaments import Ornamentation
from tangl.mechanics.presence.outfit import OutfitManager
from tangl.prose import TextRenderSession
from tangl.vm.ctx import VmPhaseCtx

from .dispatch import do_render_text, on_render_text


def render_text_as(
    target: object,
    aspect: str,
    *,
    ctx: VmPhaseCtx,
    session: TextRenderSession | None = None,
    content: str | None = None,
    bindings: Mapping[str, object] | None = None,
) -> str:
    """Render one named textual aspect through story dispatch.

    Explicit ``content`` is a complete authored replacement. Otherwise the
    selected source is the last non-``None`` result from the active authority
    chain, with the shipped mechanic handler as the application-level default.
    """
    session = session or TextRenderSession(ctx=ctx, text_resolver=render_text_as)
    if session.text_resolver is None:
        session.text_resolver = render_text_as

    source = content if content is not None else do_render_text(target, aspect=aspect, ctx=ctx)
    if source is None:
        raise LookupError(
            f"No text presentation adapter for {type(target).__name__}.{aspect}",
        )
    return session.render(
        source,
        source=ctx.cursor,
        subject=target,
        bindings=dict(bindings or {}),
    )


@on_render_text(wants_caller_kind=Look, wants_exact_kind=False)
def render_look_text(*, caller: Look, aspect: str, ctx: VmPhaseCtx) -> str | None:
    """Provide the default body-description leaf."""
    _ = ctx
    return caller.describe() if aspect == "body_description" else None


@on_render_text(wants_caller_kind=OutfitManager, wants_exact_kind=False)
def render_outfit_text(
    *,
    caller: OutfitManager,
    aspect: str,
    ctx: VmPhaseCtx,
) -> str | None:
    """Provide the default outfit-description leaf."""
    _ = ctx
    return caller.describe() if aspect == "outfit_description" else None


@on_render_text(wants_caller_kind=Ornamentation, wants_exact_kind=False)
def render_ornament_text(
    *,
    caller: Ornamentation,
    aspect: str,
    ctx: VmPhaseCtx,
) -> str | None:
    """Provide the default ornament-description leaf."""
    _ = ctx
    return caller.describe_summary() if aspect == "ornament_description" else None


@on_render_text(wants_caller_kind=HasSimpleLook, wants_exact_kind=False)
def render_simple_presence_text(
    *,
    caller: HasSimpleLook,
    aspect: str,
    ctx: VmPhaseCtx,
) -> str | None:
    """Render direct presence by delegating to the body-description leaf."""
    _ = caller, ctx
    if aspect != "presence_description":
        return None
    return "{{ render_as(subject.look, 'body_description') }}"


@on_render_text(wants_caller_kind=HasLook, wants_exact_kind=False)
def render_bundle_presence_text(
    *,
    caller: HasLook,
    aspect: str,
    ctx: VmPhaseCtx,
) -> str | None:
    """Compose a bundled look through the body, outfit, and ornament adapters."""
    _ = caller, ctx
    if aspect != "presence_description":
        return None
    return (
        "{% set body = render_as(subject.look, 'body_description') %}"
        "{% set outfit = render_as(subject.outfit, 'outfit_description') %}"
        "{% set ornaments = render_as(subject.ornamentation, 'ornament_description') %}"
        "{{ body }}{% if outfit %}, wearing {{ outfit }}{% endif %}"
        "{% if ornaments %}, marked by {{ ornaments }}{% endif %}"
    )


__all__ = ["render_text_as"]
