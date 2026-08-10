"""Text presentation selection over the story dispatch chain."""

from __future__ import annotations

from collections.abc import Mapping

from tangl.prose import TextRenderSession
from tangl.vm.ctx import VmPhaseCtx

from .dispatch import do_render_text


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

__all__ = ["render_text_as"]
