from __future__ import annotations

import logging
from typing import Any

from tangl.core38 import Priority, Record, Selector
from tangl.vm38 import Dependency, Resolver

from .dispatch import on_journal
from .episode import Action, Block
from .fragments import ChoiceFragment, ContentFragment, MediaFragment

logger = logging.getLogger(__name__)


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


def _hard_unresolved_dependencies(*, edge: Action) -> list[Dependency]:
    """Return unresolved hard dependencies on an action successor."""
    successor = edge.successor
    if successor is None:
        return []

    unresolved = successor.edges_out(Selector(has_kind=Dependency, satisfied=False))
    return [
        dep
        for dep in unresolved
        if bool(getattr(dep.requirement, "hard_requirement", False))
    ]


def _destination_dependency(*, edge: Action) -> Dependency | None:
    """Return destination dependency edge when successor is unresolved."""
    graph = getattr(edge, "graph", None)
    if graph is None:
        return None
    deps = list(graph.find_edges(Selector(has_kind=Dependency, predecessor=edge)))
    for dep in deps:
        if dep.get_label() == "destination":
            return dep
    return deps[0] if deps else None


def _preview_destination_viability(*, edge: Action, ctx):
    dep = _destination_dependency(edge=edge)
    if dep is None or dep.requirement.satisfied:
        return None
    try:
        resolver = Resolver.from_ctx(ctx)
    except (TypeError, ValueError, LookupError) as exc:
        logger.debug("Resolver preview unavailable for edge=%s", edge, exc_info=exc)
        return None
    return resolver.preview_requirement(dep.requirement, _ctx=ctx)


def _preview_blockers(preview) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for blocker in getattr(preview, "blockers", []) or []:
        blockers.append(
            {
                "type": "provision",
                "reason": blocker.reason,
                "context": dict(blocker.context or {}),
            }
        )
    return blockers


def _choice_unavailable_reason(*, edge: Action, ctx) -> str | None:
    """Return a coarse reason for unavailable choices."""
    if edge.successor is None:
        preview = _preview_destination_viability(edge=edge, ctx=ctx)
        if preview is not None and preview.viable:
            return None
        return "missing_successor"

    # Hard unresolved dependencies block choice availability regardless of guard predicates.
    if _hard_unresolved_dependencies(edge=edge):
        return "missing_dependency"

    if not edge.available(ctx=ctx):
        return "guard_failed_or_unavailable"

    return None


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
        preview = _preview_destination_viability(edge=edge, ctx=ctx)
        if preview is not None:
            if preview.viable:
                return []
            preview_blockers = _preview_blockers(preview)
            if preview_blockers:
                return preview_blockers
        return [{"type": "edge", "reason": "missing_successor"}]

    blockers = [_dependency_blocker(dep) for dep in _hard_unresolved_dependencies(edge=edge)]
    if blockers:
        return blockers

    if not edge.available(ctx=ctx):
        return [{"type": "edge", "reason": "guard_failed_or_unavailable"}]

    return []


def _merge_fragment_batches(*batches: Any) -> list[Record]:
    merged: list[Record] = []
    for batch in batches:
        if batch is None:
            continue
        if isinstance(batch, Record):
            merged.append(batch)
            continue
        if isinstance(batch, list):
            merged.extend(batch)
            continue
        merged.extend(list(batch))
    return merged


@on_journal(priority=Priority.EARLY)
def render_block_content(*, caller, ctx, **_kw):
    """Render block narrative text into content fragments."""
    if not isinstance(caller, Block):
        return None

    rendered_content = _render_block_content(caller, ctx=ctx)
    if rendered_content:
        return ContentFragment(content=rendered_content, source_id=caller.uid)
    return None


@on_journal(priority=Priority.NORMAL)
def render_block_media(*, caller, ctx, **_kw):
    """Render block media payloads into media fragments."""
    if not isinstance(caller, Block):
        return None

    fragments: list[MediaFragment] = []
    for media_item in caller.media:
        payload = media_item if isinstance(media_item, dict) else {"value": media_item}
        fragments.append(MediaFragment(source_id=caller.uid, payload=payload))

    return fragments or None


@on_journal(priority=Priority.LATE)
def render_block_choices(*, caller, ctx, **_kw):
    """Render block outbound actions into choice fragments."""
    if not isinstance(caller, Block):
        return None

    fragments: list[ChoiceFragment] = []

    for edge in caller.edges_out(Selector(has_kind=Action, trigger_phase=None)):
        reason = _choice_unavailable_reason(edge=edge, ctx=ctx)
        available = reason is None
        blockers = [] if available else _choice_blockers(edge=edge, ctx=ctx)
        fragments.append(
            ChoiceFragment(
                edge_id=edge.uid,
                text=edge.text or edge.get_label(),
                available=available,
                unavailable_reason=(None if available else reason),
                blockers=blockers or None,
                accepts=(dict(edge.accepts) if isinstance(edge.accepts, dict) else None),
                ui_hints=(dict(edge.ui_hints) if isinstance(edge.ui_hints, dict) else None),
            )
        )

    return fragments or None


def render_block(*, caller, ctx, **_kw):
    """Compatibility facade for block journal rendering.

    This wrapper preserves direct-call behavior while journal rendering is split
    into composable handlers (`render_block_content`, `render_block_media`,
    `render_block_choices`) registered through dispatch.
    """
    if not isinstance(caller, Block):
        return None

    fragments = _merge_fragment_batches(
        render_block_content(caller=caller, ctx=ctx),
        render_block_media(caller=caller, ctx=ctx),
        render_block_choices(caller=caller, ctx=ctx),
    )
    return fragments or None
