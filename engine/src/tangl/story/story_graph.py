from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from tangl.core import Graph, TemplateRegistry

from .dispatch import story_dispatch


class StoryGraph(Graph):
    """Story graph specialization for runtime state."""

    initial_cursor_id: UUID | None = None
    initial_cursor_ids: list[UUID] = Field(default_factory=list)
    locals: dict[str, Any] = Field(default_factory=dict)
    factory: TemplateRegistry | None = Field(default=None, exclude=True)
    script_manager: Any | None = Field(default=None, exclude=True)
    world: Any | None = Field(default=None, exclude=True)
    template_by_entity_id: dict[UUID, UUID] = Field(default_factory=dict, exclude=True)
    template_lineage_by_entity_id: dict[UUID, list[UUID]] = Field(default_factory=dict, exclude=True)

    def get_story_locals(self) -> dict[str, Any]:
        """Return story-level locals exposed to runtime render/provision paths."""
        return dict(self.locals)

    def get_authorities(self) -> list[object]:
        """Return application/world authority registries when available."""
        registries: list[object] = [story_dispatch]
        get_world_authorities = getattr(self.world, "get_authorities", None)
        if callable(get_world_authorities):
            for registry in get_world_authorities() or ():
                if registry not in registries:
                    registries.append(registry)
        return registries

    def get_template_scope_groups(self, caller) -> list[list[object]]:
        """Return template groups ordered from closest template scope outward."""
        caller_uid = getattr(caller, "uid", None)
        lineage = self.template_lineage_by_entity_id.get(caller_uid, [])

        get_groups = getattr(self.script_manager, "get_template_scope_groups", None)
        if callable(get_groups):
            groups = get_groups(caller=caller, graph=self, lineage_ids=lineage)
            if groups:
                return [list(group) for group in groups]

        if self.factory is None:
            return []

        groups: list[list[object]] = []
        seen_ids: set[UUID] = set()

        def add_group(values) -> None:
            bucket: list[object] = []
            for value in values:
                uid = getattr(value, "uid", None)
                if uid is None or uid in seen_ids:
                    continue
                seen_ids.add(uid)
                bucket.append(value)
            if bucket:
                groups.append(bucket)

        for template_id in lineage:
            template = self.factory.get(template_id)
            if template is None:
                continue
            values: list[object] = [template]
            if hasattr(template, "members"):
                values.extend(list(template.members()))
            add_group(values)

        add_group(self.factory.values())
        return groups


# Backwards-compatible alias retained during naming cutover.
StoryGraph38 = StoryGraph
