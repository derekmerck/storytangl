from __future__ import annotations

from typing import Any

from tangl.core38 import Selector
from tangl.vm38 import Dependency

from .dispatch import on_journal
from .episode import Action, Block
from .fragments import ChoiceFragment, ContentFragment, MediaFragment


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive fallback
        return "{" + key + "}"


def _render_block_content(block: Block, *, ctx) -> str:
    """Best-effort templating for block content against the gathered namespace."""
    content = block.content or ""
    if not content:
        return ""
    if ctx is None or not hasattr(ctx, "get_ns"):
        return content
    try:
        ns = dict(ctx.get_ns(block))
        return content.format_map(_SafeFormatDict(ns))
    except Exception:
        return content


def _choice_unavailable_reason(*, edge: Action, ctx) -> str | None:
    """Return a coarse reason for unavailable choices."""
    if edge.successor is None:
        return "missing_successor"

    if edge.available(ctx=ctx):
        return None

    successor = edge.successor
    deps = successor.edges_out(Selector(has_kind=Dependency, satisfied=False))
    if next(deps, None) is not None:
        return "missing_dependency"

    return "guard_failed_or_unavailable"


@on_journal
def render_block(*, caller, ctx, **_kw):
    """Render block content and available choices into story38 fragments."""
    if not isinstance(caller, Block):
        return None

    fragments: list[Any] = []
    rendered_content = _render_block_content(caller, ctx=ctx)
    if rendered_content:
        fragments.append(ContentFragment(content=rendered_content, source_id=caller.uid))

    for media_item in caller.media:
        payload = media_item if isinstance(media_item, dict) else {"value": media_item}
        fragments.append(MediaFragment(source_id=caller.uid, payload=payload))

    for edge in caller.edges_out(Selector(has_kind=Action, trigger_phase=None)):
        available = edge.available(ctx=ctx)
        fragments.append(
            ChoiceFragment(
                edge_id=edge.uid,
                text=edge.text or edge.get_label(),
                available=available,
                unavailable_reason=(
                    None if available else _choice_unavailable_reason(edge=edge, ctx=ctx)
                ),
            )
        )

    return fragments or None
