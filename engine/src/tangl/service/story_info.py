"""Story-info projection seam for projected runtime state."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from tangl.vm.runtime.ledger import Ledger

from .response import KvListValue, ProjectedKVItem, ProjectedSection, ProjectedState


@runtime_checkable
class StoryInfoProjector(Protocol):
    """Protocol for world-authored story-info projectors."""

    def project(self, *, ledger: Ledger) -> ProjectedState: ...


class DefaultStoryInfoProjector:
    """Default projector that emits one minimal generic session section."""

    def project(self, *, ledger: Ledger) -> ProjectedState:
        items: list[ProjectedKVItem] = []

        cursor_label = _resolve_cursor_label(ledger)
        if isinstance(cursor_label, str) and cursor_label.strip():
            items.append(ProjectedKVItem(key="Cursor", value=cursor_label))

        _append_kv_item(items, key="Step", value=getattr(ledger, "step", None))
        _append_kv_item(items, key="Turn", value=getattr(ledger, "turn", None))

        try:
            journal_size = len(ledger.get_journal())
        except Exception:  # pragma: no cover - defensive fallback
            journal_size = None
        _append_kv_item(items, key="Journal size", value=journal_size)

        return ProjectedState(
            sections=[
                ProjectedSection(
                    section_id="session",
                    title="Session",
                    kind="stats",
                    value=KvListValue(items=items),
                )
            ]
        )


DEFAULT_STORY_INFO_PROJECTOR = DefaultStoryInfoProjector()


def resolve_story_info_projector(ledger: Ledger) -> StoryInfoProjector:
    """Resolve the projector for ``ledger`` using world/domain fallback semantics."""

    world = getattr(getattr(ledger, "graph", None), "world", None)
    if world is None:
        return DEFAULT_STORY_INFO_PROJECTOR

    get_projector = getattr(world, "get_story_info_projector", None)
    if not callable(get_projector):
        return DEFAULT_STORY_INFO_PROJECTOR

    projector = get_projector()
    if projector is None:
        return DEFAULT_STORY_INFO_PROJECTOR

    project = getattr(projector, "project", None)
    if callable(project):
        return projector

    raise TypeError(
        "Story info projector must define project(*, ledger=...) -> ProjectedState"
    )


def _append_kv_item(
    items: list[ProjectedKVItem],
    *,
    key: str,
    value: Any,
) -> None:
    if value is None or not isinstance(value, (str, int, float, bool)):
        return
    items.append(ProjectedKVItem(key=key, value=value))


def _resolve_cursor_label(ledger: Ledger) -> str | None:
    graph = getattr(ledger, "graph", None)
    cursor_id = getattr(ledger, "cursor_id", None)
    if graph is None or cursor_id is None:
        return None

    get_node = getattr(graph, "get", None)
    if not callable(get_node):
        return None

    cursor_node = get_node(cursor_id)
    label = getattr(cursor_node, "label", None)
    return str(label) if label is not None else None


__all__ = [
    "DEFAULT_STORY_INFO_PROJECTOR",
    "DefaultStoryInfoProjector",
    "StoryInfoProjector",
    "resolve_story_info_projector",
]
