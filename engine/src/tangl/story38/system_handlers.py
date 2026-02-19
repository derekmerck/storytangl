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


def _dependency_blocker(dep: Dependency) -> dict[str, Any]:
    """Serialize one dependency blocker with standardized resolver diagnostics."""
    requirement = dep.requirement
    return {
        "type": "dependency",
        "dependency_id": str(dep.uid),
        "label": dep.get_label(),
        "hard_requirement": requirement.hard_requirement,
        "resolution_reason": requirement.resolution_reason,
        "resolution_meta": requirement.resolution_meta,
    }


def _choice_blockers(*, edge: Action, ctx) -> list[dict[str, Any]]:
    """Return structured blocker diagnostics for an unavailable choice edge."""
    if edge.successor is None:
        return [{"type": "edge", "reason": "missing_successor"}]

    successor = edge.successor
    blockers = [
        _dependency_blocker(dep)
        for dep in successor.edges_out(Selector(has_kind=Dependency, satisfied=False))
    ]
    if blockers:
        return blockers

    if not edge.available(ctx=ctx):
        return [{"type": "edge", "reason": "guard_failed_or_unavailable"}]

    return []


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
        blockers = [] if available else _choice_blockers(edge=edge, ctx=ctx)
        fragments.append(
            ChoiceFragment(
                edge_id=edge.uid,
                text=edge.text or edge.get_label(),
                available=available,
                unavailable_reason=(
                    None if available else _choice_unavailable_reason(edge=edge, ctx=ctx)
                ),
                blockers=blockers or None,
                accepts=(dict(edge.accepts) if isinstance(edge.accepts, dict) else None),
                ui_hints=(dict(edge.ui_hints) if isinstance(edge.ui_hints, dict) else None),
            )
        )

    return fragments or None
