"""Story-info projection seam for projected runtime state."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from tangl.vm.runtime.ledger import Ledger

from .response import (
    KvListValue,
    KvRow,
    ProjectedSection,
    ProjectedState,
    StoryInfoRequest,
)


@runtime_checkable
class StoryInfoProjector(Protocol):
    """Protocol for world-authored story-info projectors."""

    def project(self, *, ledger: Ledger) -> ProjectedState: ...


class DefaultStoryInfoProjector:
    """Default projector that emits one minimal generic session section."""

    def project(self, *, ledger: Ledger) -> ProjectedState:
        items: list[KvRow] = []

        cursor_label = _resolve_cursor_label(ledger)
        if isinstance(cursor_label, str) and cursor_label.strip():
            items.append(KvRow(key="Cursor", value=cursor_label))

        _append_kv_item(items, key="Step", value=getattr(ledger, "step", None))
        _append_kv_item(items, key="Turn", value=getattr(ledger, "turn", None))

        journal_size = len(ledger.get_journal())
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


def filter_projected_state(
    state: ProjectedState,
    *,
    request: StoryInfoRequest,
) -> ProjectedState:
    """Filter projected sections by requested kind, preserving section order."""
    requested = request.requested_kinds()
    if not requested:
        return state
    return ProjectedState(
        sections=[
            section
            for section in state.sections
            if _section_matches_request(section, requested)
        ]
    )


def _append_kv_item(
    items: list[KvRow],
    *,
    key: str,
    value: Any,
) -> None:
    if value is None or not isinstance(value, (str, int, float, bool)):
        return
    items.append(KvRow(key=key, value=value))


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


def _section_matches_request(
    section: ProjectedSection,
    requested: list[str],
) -> bool:
    labels = {section.section_id}
    if section.kind is not None:
        labels.add(section.kind)
    return any(label in requested for label in labels)


__all__ = [
    "DEFAULT_STORY_INFO_PROJECTOR",
    "DefaultStoryInfoProjector",
    "StoryInfoProjector",
    "filter_projected_state",
    "resolve_story_info_projector",
]
