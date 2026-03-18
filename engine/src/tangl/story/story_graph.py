from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from tangl.core import Graph, Selector, TemplateRegistry

from .dispatch import story_dispatch


class StoryGraph(Graph):
    """StoryGraph()

    Runtime graph specialization for story-layer execution state.

    Why
    ----
    Story execution needs more than generic graph topology. ``StoryGraph`` adds
    story locals, template lineage, and world references so runtime handlers and
    provisioning can resolve scoped data without reaching back into compile-time
    structures directly.

    Key Features
    ------------
    * Tracks one or more initial cursor ids for entry into the runtime graph.
    * Carries story locals and world/script-manager references outside
      serialized graph payloads.
    * Records template lineage for each materialized entity so provisioning can
      recover template scope.

    API
    ---
    - :meth:`get_story_locals` returns the story-level namespace payload.
    - :meth:`get_authorities` returns dispatch registries available to runtime
      handlers.
    - :meth:`get_template_scope_groups` returns template groups ordered from the
      closest scope outward.
    """

    initial_cursor_id: UUID | None = None
    initial_cursor_ids: list[UUID] = Field(default_factory=list)
    frozen_shape: bool = False
    locals: dict[str, Any] = Field(default_factory=dict)
    factory: TemplateRegistry | None = Field(default=None, exclude=True)
    script_manager: Any | None = Field(default=None, exclude=True)
    world: Any | None = Field(default=None, exclude=True)
    story_id: UUID | None = Field(default=None, exclude=True)
    story_resources: Any | None = Field(default=None, exclude=True)
    story_materialize: Any | None = Field(default=None, exclude=True)
    story_post_materialize: Any | None = Field(default=None, exclude=True)
    story_preview_requirement: Any | None = Field(default=None, exclude=True)
    template_by_entity_id: dict[UUID, UUID] = Field(default_factory=dict, exclude=True)
    template_lineage_by_entity_id: dict[UUID, list[UUID]] = Field(default_factory=dict, exclude=True)
    wired_node_ids: set[UUID] = Field(default_factory=set, exclude=True)

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

    @staticmethod
    def template_lineage_ids_for_template(template: Any) -> list[UUID]:
        """Return template lineage from nearest scope outward."""
        lineage: list[UUID] = []
        current = template
        while current is not None:
            uid = getattr(current, "uid", None)
            if isinstance(uid, UUID):
                lineage.append(uid)
            current = getattr(current, "parent", None)
        return lineage

    def record_runtime_template(self, entity: Any, template: Any) -> None:
        """Stamp template provenance for a runtime-created entity when possible."""
        entity_uid = getattr(entity, "uid", None)
        template_uid = getattr(template, "uid", None)
        if not isinstance(entity_uid, UUID) or not isinstance(template_uid, UUID):
            return

        self.template_by_entity_id[entity_uid] = template_uid
        self.template_lineage_by_entity_id[entity_uid] = self.template_lineage_ids_for_template(
            template
        )

    def is_runtime_wired_node(self, node: Any) -> bool:
        """Return whether runtime topology has already been wired for ``node``."""
        node_uid = getattr(node, "uid", None)
        if isinstance(node_uid, UUID) and node_uid in self.wired_node_ids:
            return True

        try:
            from tangl.media.media_resource import MediaDep
            from tangl.vm import Fanout, TraversableNode

            from .concepts import Role, Setting
            from .episode import Action
        except ImportError:
            return False

        edges_out = getattr(node, "edges_out", None)
        if callable(edges_out):
            for edge_kind in (Action, Role, Setting, MediaDep, Fanout):
                if next(edges_out(Selector(has_kind=edge_kind)), None) is not None:
                    return True
        return False

    def rebuild_runtime_materialization_state(self) -> None:
        """Reconstruct runtime-only wiring markers from the current graph."""
        try:
            from tangl.vm import TraversableNode
        except ImportError:
            self.wired_node_ids = set()
            return

        rebuilt: set[UUID] = set()
        for node in Selector(has_kind=TraversableNode).filter(self.values()):
            if self.is_runtime_wired_node(node):
                rebuilt.add(node.uid)
                continue

            source = getattr(node, "source", None)
            sink = getattr(node, "sink", None)
            has_member = getattr(node, "has_member", None)
            if callable(has_member) and source is not None and sink is not None:
                try:
                    if has_member(source) and has_member(sink):
                        rebuilt.add(node.uid)
                except Exception:
                    continue
        self.wired_node_ids = rebuilt
