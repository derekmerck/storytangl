from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from pydantic import Field, PrivateAttr, model_validator

from tangl.core import EntityTemplate, Selector, TemplateRegistry
from tangl.vm import TraversableGraph

from .dispatch import story_dispatch

logger = logging.getLogger(__name__)


def _runtime_wiring_symbols():
    """Return runtime wiring types required by ``StoryGraph``."""
    from tangl.media.media_resource import MediaDep
    from tangl.vm import Fanout, TraversableNode

    from .concepts import Role, Setting
    from .episode import Action

    return TraversableNode, (Action, Role, Setting, MediaDep, Fanout)


class StoryGraph(TraversableGraph):
    """StoryGraph()

    Runtime graph specialization for story-layer execution state.

    Why
    ----
    Story execution needs more than generic graph topology. ``StoryGraph`` adds
    story locals, runtime lineage state, and a compatibility world alias over
    the bound graph factory so story handlers can resolve scoped data without
    reaching back into compile-time structures directly.

    Key Features
    ------------
    * Tracks one or more initial cursor ids for entry into the runtime graph.
    * Carries story locals and a compatibility script-manager pointer outside
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

    initial_cursor_ids: list[UUID] = Field(default_factory=list)
    frozen_shape: bool = False
    locals: dict[str, Any] = Field(default_factory=dict)
    world_ref: Any | None = Field(default=None, exclude=True, validation_alias="world")
    story_id: UUID | None = Field(default=None, exclude=True)
    story_resources: Any | None = Field(default=None, exclude=True)
    template_by_entity_id: dict[UUID, UUID] = Field(default_factory=dict, exclude=True)
    template_lineage_by_entity_id: dict[UUID, list[UUID]] = Field(default_factory=dict, exclude=True)
    wired_node_ids: set[UUID] = Field(default_factory=set, exclude=True)

    _world_override: Any = PrivateAttr(default=None)
    _script_manager_override: Any = PrivateAttr(default=None)
    _story_materialize_override: Any = PrivateAttr(default=None)
    _story_post_materialize_override: Any = PrivateAttr(default=None)
    _story_preview_requirement_override: Any = PrivateAttr(default=None)

    @property
    def world(self) -> Any | None:
        if self._world_override is not None:
            return self._world_override
        from .fabula.world import World

        if isinstance(self.factory, World):
            return self.factory
        return None

    @world.setter
    def world(self, value: Any | None) -> None:
        from .fabula.world import World

        if isinstance(value, World):
            self.bind_factory(value)
            self._world_override = None
            return
        self._world_override = value

    @property
    def script_manager(self) -> Any | None:
        if self._script_manager_override is not None:
            return self._script_manager_override
        world = self.world
        if world is None:
            return None
        return getattr(world, "script_manager", None)

    @script_manager.setter
    def script_manager(self, value: Any | None) -> None:
        self._script_manager_override = value

    @property
    def story_materialize(self) -> Any | None:
        if self._story_materialize_override is not None:
            return self._story_materialize_override
        world = self.world
        if world is None:
            return None
        return getattr(world, "story_materialize_template", None)

    @story_materialize.setter
    def story_materialize(self, value: Any | None) -> None:
        self._story_materialize_override = value

    @property
    def story_post_materialize(self) -> Any | None:
        if self._story_post_materialize_override is not None:
            return self._story_post_materialize_override
        world = self.world
        if world is None:
            return None
        return getattr(world, "story_post_materialize", None)

    @story_post_materialize.setter
    def story_post_materialize(self, value: Any | None) -> None:
        self._story_post_materialize_override = value

    @property
    def story_preview_requirement(self) -> Any | None:
        if self._story_preview_requirement_override is not None:
            return self._story_preview_requirement_override
        world = self.world
        if world is None:
            return None
        return getattr(world, "preview_requirement_contract", None)

    @story_preview_requirement.setter
    def story_preview_requirement(self, value: Any | None) -> None:
        self._story_preview_requirement_override = value

    @model_validator(mode="after")
    def _restore_runtime_refs(self) -> StoryGraph:
        """Restore lightweight runtime pointers derived from the bound world."""
        if self.world_ref is not None and self._world_override is None:
            self._world_override = self.world_ref
        if self.story_id is None:
            self.story_id = self.uid
        if not self.template_by_entity_id and not self.template_lineage_by_entity_id:
            self.rebuild_template_lineage()
        return self

    def get_story_locals(self) -> dict[str, Any]:
        """Return story-level locals exposed to runtime render/provision paths."""
        return dict(self.locals)

    def _template_registry(self) -> TemplateRegistry | None:
        factory = getattr(self, "factory", None)
        if isinstance(factory, TemplateRegistry):
            return factory

        templates = getattr(factory, "templates", None)
        if isinstance(templates, TemplateRegistry):
            return templates

        script_manager = getattr(self, "script_manager", None)
        registry = getattr(script_manager, "template_registry", None)
        if isinstance(registry, TemplateRegistry):
            return registry
        return None

    @property
    def template_registry(self) -> TemplateRegistry | None:
        """Return the template registry authoritative for this story graph."""
        return self._template_registry()

    def get_authorities(self) -> list[object]:
        """Return story + application/world authority registries when available."""
        registries: list[object] = [story_dispatch]
        for registry in super().get_authorities():
            if registry not in registries:
                registries.append(registry)

        world = self.world
        if world is not None and world is not self.factory:
            get_world_authorities = getattr(world, "get_authorities", None)
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

        registry = self._template_registry()
        if registry is None:
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
            template = registry.get(template_id)
            if template is None:
                continue
            values: list[object] = [template]
            if hasattr(template, "members"):
                values.extend(list(template.members()))
            add_group(values)

        add_group(registry.values())
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

    def rebuild_template_lineage(self, registry: TemplateRegistry | None = None) -> None:
        """Rebuild runtime template lineage from templ_hash provenance."""
        registry = registry or self._template_registry()
        if registry is None:
            return

        template_by_hash: dict[bytes, EntityTemplate] = {}
        for template in registry.values():
            if isinstance(template, EntityTemplate):
                template_by_hash[template.content_hash()] = template

        self.template_by_entity_id.clear()
        self.template_lineage_by_entity_id.clear()
        for entity in self.values():
            templ_hash = getattr(entity, "templ_hash", None)
            if not isinstance(templ_hash, bytes):
                continue
            template = template_by_hash.get(templ_hash)
            if template is None:
                continue
            self.record_runtime_template(entity, template)

    def is_runtime_wired_node(self, node: Any) -> bool:
        """Return whether runtime topology has already been wired for ``node``."""
        node_uid = getattr(node, "uid", None)
        if isinstance(node_uid, UUID) and node_uid in self.wired_node_ids:
            return True

        _traversable_node, edge_kinds = _runtime_wiring_symbols()

        edges_out = getattr(node, "edges_out", None)
        if callable(edges_out):
            for edge_kind in edge_kinds:
                if next(edges_out(Selector(has_kind=edge_kind)), None) is not None:
                    return True
        return False

    def rebuild_runtime_materialization_state(self) -> None:
        """Reconstruct runtime-only wiring markers from the current graph."""
        traversable_node_kind, _edge_kinds = _runtime_wiring_symbols()

        rebuilt: set[UUID] = set()
        for node in Selector(has_kind=traversable_node_kind).filter(self.values()):
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
                except (AttributeError, KeyError) as exc:
                    logger.warning(
                        "Skipping runtime wiring rebuild for node_id=%s due to malformed membership state: %s",
                        getattr(node, "uid", None),
                        exc,
                    )
        self.wired_node_ids = rebuilt

    @classmethod
    def structure(cls, data, _ctx=None):
        graph = super().structure(data, _ctx=_ctx)
        return graph._restore_runtime_refs()
