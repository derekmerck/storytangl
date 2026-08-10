"""Text-presentation handlers owned by the Presence mechanic."""

from __future__ import annotations

from tangl.story.dispatch import on_render_text
from tangl.vm.ctx import VmPhaseCtx

from .look import HasLook, HasSimpleLook, Look
from .ornaments import Ornamentation
from .outfit import OutfitManager


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


__all__ = [
    "render_bundle_presence_text",
    "render_look_text",
    "render_ornament_text",
    "render_outfit_text",
    "render_simple_presence_text",
]
