from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import UUID

from tangl.core import EntityTemplate, GraphFactory, GraphItem, Selector, TemplateRegistry
from tangl.core.ctx import CoreCtx
from tangl.media.media_creators.media_spec import MediaSpec
from tangl.media.media_resource import MediaDep
from tangl.vm.dispatch import do_gather_ns
from tangl.vm.ctx import VmRequirementStampCtx
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm import (
    Affordance,
    Blocker,
    Dependency,
    Fanout,
    ProvisionOffer,
    ProvisionPolicy,
    Requirement,
    Resolver,
    TraversableNode,
    assert_traversal_contracts,
    do_get_template_scope_groups,
)
from tangl.vm.provision import MaterializeRole, attach_child, materialize_template_entity
from tangl.vm.provision.provisioner import _next_provision_uid

from ..concepts import Actor, Location, Role, Setting
from ..episode import Action, Block, MenuBlock, Scene
from ..story_graph import StoryGraph
from .compiler import StoryTemplateBundle
from .types import (
    GraphInitializationError,
    InitMode,
    InitReport,
    ResolutionError,
    ResolutionFailureReason,
    StoryInitResult,
    UnresolvedDependency,
)


@dataclass(slots=True)
class _MaterializationState:
    graph: StoryGraph
    template_registry: TemplateRegistry
    report: InitReport
    entry_template_ids: list[str] = field(default_factory=list)
    source_map: dict[str, Any] = field(default_factory=dict)
    codec_state: dict[str, Any] = field(default_factory=dict)
    codec_id: str | None = None
    bundle_id: str | None = None
    id_to_entity: dict[str, GraphItem] = field(default_factory=dict)


@dataclass(slots=True)
class _PrelinkCtx:
    graph: StoryGraph
    template_registry: TemplateRegistry
    cursor_id: UUID | None = None
    step: int | None = None
    correlation_id: UUID | str | None = None
    logger: Any | None = None
    meta: Mapping[str, Any] | None = field(default_factory=dict)

    @property
    def cursor(self):
        if self.cursor_id is None:
            return None
        return self.graph.get(self.cursor_id)

    def get_authorities(self) -> list[object]:
        getter = getattr(self.graph, "get_authorities", None)
        if callable(getter):
            return list(getter() or [])
        return []

    def get_inline_behaviors(self):
        return []

    def get_meta(self) -> Mapping[str, Any]:
        return dict(self.meta or {})

    def get_story_locals(self) -> Mapping[str, Any]:
        return self.graph.get_story_locals()

    def get_ns(self, node: Any = None) -> Mapping[str, Any]:
        target = node or self.cursor
        if target is None:
            return self.graph.get_story_locals()
        return do_gather_ns(target, ctx=self)

    def get_location_entity_groups(self):
        cursor = self.cursor
        if cursor is None:
            return [self.graph.values()]

        groups: list[list[Any]] = []
        seen_ids: set[UUID] = set()

        def add_group(values):
            bucket: list[Any] = []
            for value in values:
                uid = getattr(value, "uid", None)
                if uid is None or uid in seen_ids:
                    continue
                seen_ids.add(uid)
                bucket.append(value)
            if bucket:
                groups.append(bucket)

        add_group([cursor])
        ancestors = getattr(cursor, "ancestors", None)
        if callable(ancestors):
            ancestors = ancestors()
        if ancestors is not None:
            for ancestor in ancestors:
                if hasattr(ancestor, "children"):
                    add_group(ancestor.children())
        add_group(self.graph.values())
        return groups or [list(self.graph.values())]

    def get_template_scope_groups(self):
        cursor = self.cursor
        if cursor is not None:
            registries = do_get_template_scope_groups(cursor, ctx=self)
            if registries:
                return registries
        return [self.template_registry]

    def derive(
        self,
        *,
        cursor_id: UUID | None = None,
        graph: StoryGraph | None = None,
        meta_overrides: Mapping[str, Any] | None = None,
        **field_overrides: Any,
    ) -> PhaseCtx:
        meta = dict(self.meta or {})
        if meta_overrides:
            meta.update(meta_overrides)

        kwargs: dict[str, Any] = {
            "graph": self.graph if graph is None else graph,
            "cursor_id": self.cursor_id if cursor_id is None else cursor_id,
            "step": 0 if self.step is None else self.step,
            "correlation_id": self.correlation_id,
            "logger": self.logger,
            "meta": meta,
        }
        kwargs.update(field_overrides)
        return PhaseCtx(**kwargs)


class StoryMaterializer:
    """StoryMaterializer()

    Story-policy helper for runtime graph wiring and compatibility delegation.

    Why
    ----
    ``World.create_story(...)`` now owns graph creation directly by layering over
    :class:`~tangl.vm.TraversableGraphFactory`. ``StoryMaterializer`` remains as
    the focused helper that applies story-specific topology, eager prelink
    policy, and runtime materialization hooks on top of that lower-layer graph
    creation.

    Key Features
    ------------
    * Wires story-specific topology onto an already-materialized graph.
    * Supports eager prelink/report passes once generic graph creation
      completes.
    * Preserves template-to-entity lineage for runtime scope lookup.
    * Finalizes scene contracts and wires node destinations after instantiation.
    * Uses vm resolver semantics instead of reimplementing provisioning logic.

    API
    ---
    - :meth:`create_story` delegates to a bound world for compatibility.
    - :meth:`make_state` builds story wiring state from direct runtime
      authorities.
    """

    def story_materialize_template(
        self,
        template: EntityTemplate,
        _ctx: Any = None,
    ) -> GraphItem:
        """Materialize one story template payload with resolver-stable uid rules."""
        return template.materialize(uid=_next_provision_uid(_ctx=_ctx))

    def story_post_materialize(
        self,
        *,
        template: EntityTemplate | None,
        entity: Any,
        role: MaterializeRole | str = MaterializeRole.PROVISION_LEAF,
        _ctx: Any = None,
    ) -> None:
        """Finalize runtime story contracts for one newly attached entity."""
        if isinstance(role, str):
            role = MaterializeRole(role)

        graph = getattr(entity, "graph", None) or getattr(_ctx, "graph", None)
        if not isinstance(graph, StoryGraph):
            return

        if isinstance(template, EntityTemplate) and isinstance(entity, GraphItem):
            graph.record_runtime_template(entity, template)

        if not isinstance(entity, TraversableNode):
            return

        if graph.is_runtime_wired_node(entity):
            graph.wired_node_ids.add(entity.uid)
            return

        if isinstance(template, EntityTemplate) and self._template_is_container(template):
            self._ensure_runtime_container_entry(
                graph=graph,
                template=template,
                container=entity,
                _ctx=_ctx,
            )

        state = self._runtime_state(graph=graph)
        self._run_runtime_topology_passes(nodes=[entity], state=state)

    def preview_requirement_contract(
        self,
        *,
        requirement: Requirement,
        offer: ProvisionOffer,
        graph: Any,
        _ctx: Any = None,
    ) -> list[Blocker]:
        """Return story-level selected-path blockers for one preview offer."""
        if not isinstance(graph, StoryGraph):
            return []

        template = offer.candidate
        target_ctx = offer.target_ctx
        if not isinstance(template, EntityTemplate) or not isinstance(target_ctx, str) or not target_ctx:
            return []

        blockers: list[Blocker] = []
        build_segments = list(offer.build_plan or ())
        parent_paths = self._parent_prefix_paths(target_ctx)
        missing_paths = parent_paths[-len(build_segments) :] if build_segments else []

        for segment_path in missing_paths:
            segment_template = self._find_template_for_path(graph=graph, reference=segment_path)
            if not isinstance(segment_template, EntityTemplate):
                continue
            blockers.extend(
                self._preview_immediate_hard_dependencies(
                    graph=graph,
                    template=segment_template,
                    request_ctx_path=segment_path,
                    _ctx=_ctx,
                )
            )
            if blockers:
                return blockers

        blockers.extend(
            self._preview_immediate_hard_dependencies(
                graph=graph,
                template=template,
                request_ctx_path=target_ctx,
                _ctx=_ctx,
            )
        )
        return blockers

    def create_story(
        self,
        *,
        bundle: StoryTemplateBundle,
        story_label: str,
        init_mode: InitMode,
        freeze_shape: bool = False,
        world: object | None = None,
    ) -> StoryInitResult:
        if world is not None:
            create_story = getattr(world, "create_story", None)
            if callable(create_story):
                return create_story(
                    story_label,
                    init_mode=init_mode,
                    freeze_shape=freeze_shape,
                )
        msg = "StoryMaterializer.create_story now requires a World authority"
        raise ValueError(msg)

    def make_state(
        self,
        *,
        graph: StoryGraph,
        mode: InitMode,
        template_registry: TemplateRegistry | None = None,
        entry_template_ids: list[str] | None = None,
        source_map: dict[str, Any] | None = None,
        codec_state: dict[str, Any] | None = None,
        codec_id: str | None = None,
        bundle_id: str | None = None,
    ) -> _MaterializationState:
        """Build a story wiring/prelink state from direct runtime authority."""
        resolved_registry = template_registry or self._template_registry_for_graph(graph)
        if bundle_id is None:
            bundle_id = getattr(resolved_registry, "label", None)
        state = _MaterializationState(
            graph=graph,
            template_registry=resolved_registry,
            report=InitReport(mode=mode),
            entry_template_ids=list(entry_template_ids or []),
            source_map=dict(source_map or {}),
            codec_state=dict(codec_state or {}),
            codec_id=codec_id,
            bundle_id=bundle_id,
        )
        self._index_graph_entities(state=state)
        return state

    def _run_topology_passes(self, *, state: _MaterializationState) -> None:
        nodes = self._unwired_traversable_nodes(state=state)
        self._finalize_scene_contracts(state=state)
        self._wire_role_and_setting_dependencies(nodes=nodes, state=state)
        self._wire_menu_fanouts(nodes=nodes, state=state)
        self._wire_block_actions(nodes=nodes, state=state)
        self._wire_media_dependencies(nodes=nodes, state=state)
        self._mark_nodes_wired(nodes=nodes, state=state)

    @staticmethod
    def _recount_materialized(*, state: _MaterializationState) -> None:
        state.report.materialized_counts.clear()
        for entity in state.graph.values():
            if isinstance(entity, GraphItem):
                state.report.bump_materialized(entity.__class__.__name__)

    def _run_prelink_passes(self, *, state: _MaterializationState) -> None:
        if state.report.mode is not InitMode.EAGER:
            return
        dependencies = self._sorted_dependencies(state=state)
        self._prelink_dependencies(dependencies=dependencies, state=state)
        self._project_action_successors_from_dependencies(dependencies=dependencies)
        if state.graph.frozen_shape:
            fanouts = self._sorted_fanouts(state=state)
            self._prelink_fanouts(fanouts=fanouts, state=state)
            self._project_prelinked_menu_actions_for_menus(
                menus=self._sorted_menu_blocks(state=state),
                state=state,
            )
        self._verify_prelinked_story_graph(state=state)
        self._raise_on_unresolved_hard_dependencies(state=state)

    @staticmethod
    def _build_story_init_result(*, state: _MaterializationState) -> StoryInitResult:
        graph = state.graph
        return StoryInitResult(
            graph=graph,
            report=state.report,
            entry_ids=graph.initial_cursor_ids,
            source_map=dict(state.source_map),
            codec_state=dict(state.codec_state),
            codec_id=state.codec_id,
        )

    @staticmethod
    def _template_registry_for_graph(graph: StoryGraph) -> TemplateRegistry:
        registry = getattr(graph, "factory", None)
        if isinstance(registry, TemplateRegistry):
            return registry
        if isinstance(registry, GraphFactory) and isinstance(registry.templates, TemplateRegistry):
            return registry.templates

        script_manager = getattr(graph, "script_manager", None)
        registry = getattr(script_manager, "template_registry", None)
        if isinstance(registry, TemplateRegistry):
            return registry
        return TemplateRegistry(label="story_runtime_templates")

    def _runtime_state(self, *, graph: StoryGraph, mode: InitMode = InitMode.LAZY) -> _MaterializationState:
        world = getattr(graph, "world", None)
        return self.make_state(
            graph=graph,
            mode=mode,
            template_registry=self._template_registry_for_graph(graph),
            entry_template_ids=list(getattr(world, "entry_template_ids", []) or []),
            source_map=dict(getattr(world, "source_map", {}) or {}),
            codec_state=dict(getattr(world, "codec_state", {}) or {}),
            codec_id=getattr(world, "codec_id", None),
            bundle_id=getattr(self._template_registry_for_graph(graph), "label", None),
        )

    def _index_graph_entities(self, *, state: _MaterializationState) -> None:
        for entity in state.graph.values():
            if isinstance(entity, GraphItem):
                self._index_entity(state=state, entity=entity)

    def _index_entity(
        self,
        *,
        state: _MaterializationState,
        entity: GraphItem,
        template: EntityTemplate | None = None,
    ) -> None:
        template_label = template.get_label() if isinstance(template, EntityTemplate) else None
        if template_label:
            state.id_to_entity[template_label] = entity

        entity_label = entity.get_label() if hasattr(entity, "get_label") else None
        if isinstance(entity_label, str) and entity_label:
            state.id_to_entity.setdefault(entity_label, entity)

        for identifier in entity.get_identifiers():
            key = str(identifier)
            state.id_to_entity.setdefault(key, entity)

    def _run_runtime_topology_passes(
        self,
        *,
        nodes: list[TraversableNode],
        state: _MaterializationState,
    ) -> None:
        unwired: list[TraversableNode] = []
        for node in nodes:
            if state.graph.is_runtime_wired_node(node):
                state.graph.wired_node_ids.add(node.uid)
                continue
            unwired.append(node)
        if not unwired:
            return

        self._wire_role_and_setting_dependencies(nodes=unwired, state=state)
        self._wire_menu_fanouts(nodes=unwired, state=state)
        self._wire_block_actions(nodes=unwired, state=state)
        self._wire_media_dependencies(nodes=unwired, state=state)
        self._mark_nodes_wired(nodes=unwired, state=state)

    def _template_child_templates(self, template: EntityTemplate) -> list[EntityTemplate]:
        members = getattr(template, "members", None)
        if not callable(members):
            return []

        children = [
            member
            for member in members()
            if isinstance(member, EntityTemplate)
            and getattr(member, "parent", None) is template
            and member.has_payload_kind(TraversableNode)
        ]
        return sorted(children, key=self._template_depth)

    def _template_is_container(self, template: EntityTemplate) -> bool:
        return bool(self._template_child_templates(template))

    def _entry_template_for_container(self, template: EntityTemplate) -> EntityTemplate | None:
        children = self._template_child_templates(template)
        if not children:
            return None

        for tag_name in ("start", "entry"):
            for child in children:
                if child.has_tags({tag_name}):
                    return child

        for child in children:
            payload = getattr(child, "payload", None)
            child_locals = getattr(payload, "locals", None) or {}
            if isinstance(child_locals, dict) and (
                child_locals.get("is_start") or child_locals.get("start_at")
            ):
                return child

        for child in children:
            label = child.get_label()
            short_label = label.rsplit(".", 1)[-1] if "." in label else label
            if short_label.lower() == "start":
                return child

        return children[0]

    @staticmethod
    def _parent_prefix_paths(path: str) -> list[str]:
        parts = [segment for segment in path.split(".") if segment]
        return [".".join(parts[: idx + 1]) for idx in range(len(parts) - 1)]

    def _find_template_for_path(
        self,
        *,
        graph: StoryGraph,
        reference: str,
    ) -> EntityTemplate | None:
        script_manager = getattr(graph, "script_manager", None)
        finder = getattr(script_manager, "find_template", None)
        if callable(finder):
            found = finder(reference)
            if isinstance(found, EntityTemplate):
                return found

        registry = self._template_registry_for_graph(graph)
        found = registry.find_one(Selector(has_identifier=reference))
        if isinstance(found, EntityTemplate):
            return found
        found = registry.find_one(Selector(label=reference))
        if isinstance(found, EntityTemplate):
            return found
        return None

    def _find_existing_child_for_template(
        self,
        *,
        graph: StoryGraph,
        container: TraversableNode,
        template: EntityTemplate,
    ) -> TraversableNode | None:
        children = getattr(container, "children", None)
        if not callable(children):
            return None

        for child in children():
            if not isinstance(child, TraversableNode):
                continue
            template_uid = graph.template_by_entity_id.get(child.uid)
            if template_uid == getattr(template, "uid", None):
                return child
            path = getattr(child, "path", None)
            if isinstance(path, str) and path == template.get_label():
                return child
        return None

    def _ensure_runtime_container_entry(
        self,
        *,
        graph: StoryGraph,
        template: EntityTemplate,
        container: TraversableNode,
        _ctx: Any = None,
    ) -> TraversableNode | None:
        entry_template = self._entry_template_for_container(template)
        if entry_template is None:
            return None

        entry_node = self._find_existing_child_for_template(
            graph=graph,
            container=container,
            template=entry_template,
        )
        if entry_node is None:
            story_materialize = getattr(graph, "story_materialize", None)
            entry_node = materialize_template_entity(
                entry_template,
                _ctx=_ctx,
                role=MaterializeRole.PROVISION_LEAF,
                story_materialize=story_materialize if callable(story_materialize) else None,
            )
            if not isinstance(entry_node, TraversableNode):
                return None
            graph.add(entry_node, _ctx=_ctx)
            attach_child(container, entry_node)
            graph.record_runtime_template(entry_node, entry_template)

        container.finalize_container_contract()
        self.story_post_materialize(
            template=entry_template,
            entity=entry_node,
            role=MaterializeRole.PROVISION_LEAF,
            _ctx=_ctx,
        )
        return entry_node

    def _make_preview_requirement_ctx(
        self,
        *,
        graph: StoryGraph,
        request_ctx_path: str,
        _ctx: Any = None,
    ) -> _PrelinkCtx:
        correlation_id = None
        logger = None
        step = None
        meta: dict[str, Any] = {}
        if isinstance(_ctx, CoreCtx):
            correlation_id = _ctx.correlation_id
            logger = _ctx.logger
            meta.update(_ctx.get_meta())
        if isinstance(_ctx, VmRequirementStampCtx):
            step = _ctx.step
        meta["request_ctx_path"] = request_ctx_path
        return _PrelinkCtx(
            graph=graph,
            template_registry=self._template_registry_for_graph(graph),
            cursor_id=None,
            step=step,
            correlation_id=correlation_id,
            logger=logger,
            meta=meta,
        )

    def _preview_immediate_hard_dependencies(
        self,
        *,
        graph: StoryGraph,
        template: EntityTemplate,
        request_ctx_path: str,
        _ctx: Any = None,
    ) -> list[Blocker]:
        payload = getattr(template, "payload", None)
        if not isinstance(payload, TraversableNode):
            return []

        ctx = self._make_preview_requirement_ctx(
            graph=graph,
            request_ctx_path=request_ctx_path,
            _ctx=_ctx,
        )
        resolver = Resolver.from_ctx(ctx)
        blockers: list[Blocker] = []
        for label, dep_requirement in self._iter_immediate_hard_requirements(payload):
            preview = resolver.preview_requirement(dep_requirement, _ctx=ctx)
            if preview.viable:
                continue
            blockers.append(
                Blocker(
                    reason="immediate_dependency_unresolvable",
                    context={
                        "target_ctx": request_ctx_path,
                        "template": template.get_label(),
                        "dependency_label": label,
                        "dependency": self._serialize_selector(dep_requirement),
                        "blockers": [
                            {"reason": blocker.reason, "context": dict(blocker.context or {})}
                            for blocker in preview.blockers
                        ],
                    },
                )
            )
        return blockers

    def _iter_immediate_hard_requirements(
        self,
        node: TraversableNode,
    ) -> list[tuple[str, Requirement]]:
        requirements: list[tuple[str, Requirement]] = []
        if isinstance(node, (Scene, Block)):
            requirements.extend(
                self._requirements_from_specs(
                    specs=node.roles,
                    provider_kind=Actor,
                    ref_key="actor_ref",
                    templ_ref_key="actor_template_ref",
                )
            )
            requirements.extend(
                self._requirements_from_specs(
                    specs=node.settings,
                    provider_kind=Location,
                    ref_key="location_ref",
                    templ_ref_key="location_template_ref",
                )
            )
        if isinstance(node, Block):
            requirements.extend(self._media_requirements_from_specs(node=node))
        return requirements

    def _requirements_from_specs(
        self,
        *,
        specs: list[dict[str, Any]],
        provider_kind: type[GraphItem],
        ref_key: str,
        templ_ref_key: str,
    ) -> list[tuple[str, Requirement]]:
        requirements: list[tuple[str, Requirement]] = []
        for index, spec in enumerate(specs):
            if not isinstance(spec, dict) or not bool(spec.get("hard", True)):
                continue

            label = self._coerce_str(spec.get("label")) or f"dep_{index}"
            identifier = self._coerce_str(spec.get(ref_key) or spec.get(templ_ref_key))
            requirement_kwargs: dict[str, Any] = {
                "has_kind": provider_kind,
                "provision_policy": self._resolve_policy(
                    spec.get("policy") or spec.get("requirement_policy")
                ),
                "hard_requirement": True,
            }
            if identifier is not None:
                requirement_kwargs["has_identifier"] = identifier
                requirement_kwargs["authored_path"] = identifier
                requirement_kwargs["is_qualified"] = self._is_qualified_path(identifier)

            requirements.append((label, Requirement(**requirement_kwargs)))
        return requirements

    def _media_requirements_from_specs(self, *, node: Block) -> list[tuple[str, Requirement]]:
        requirements: list[tuple[str, Requirement]] = []
        for index, spec in enumerate(node.media):
            if not isinstance(spec, dict) or not bool(spec.get("hard", False)):
                continue

            source_kind = self._media_source_kind(spec)
            label = self._coerce_str(spec.get("label")) or f"media_{node.get_label()}_{index}"
            payload: dict[str, Any] = {
                "label": label,
                "hard": True,
                "scope": self._coerce_str(spec.get("scope")),
                "media_role": self._coerce_str(spec.get("media_role")),
            }
            if source_kind == "inventory":
                payload["media_id"] = self._coerce_str(spec.get("name"))
            elif source_kind == "potential":
                payload["media_spec"] = spec.get("spec")
            else:
                continue

            requirement = MediaDep._pre_resolve(payload).get("requirement")
            if isinstance(requirement, Requirement):
                requirements.append((label, requirement))
        return requirements

    @staticmethod
    def _template_depth(templ: Any) -> tuple[int, int, str]:
        depth = 0
        current = getattr(templ, "parent", None)
        while current is not None:
            depth += 1
            current = getattr(current, "parent", None)
        seq = getattr(templ, "seq", 0)
        label = templ.get_label() if hasattr(templ, "get_label") else ""
        return depth, seq, label

    def _resolve_entry_templates(
        self,
        *,
        template_registry: TemplateRegistry,
        entry_template_ids: list[str],
    ) -> list[Any]:
        templates = []
        for identifier in entry_template_ids:
            templ = template_registry.find_one(
                Selector(has_identifier=identifier),
            )
            if templ is None:
                templ = template_registry.find_one(Selector(label=identifier))
            if templ is not None:
                templates.append(templ)
        return templates

    def _finalize_scene_contracts(self, *, state: _MaterializationState) -> None:
        for scene in Selector(has_kind=Scene).filter(state.graph.values()):
            scene.finalize_container_contract()

    def _unwired_traversable_nodes(self, *, state: _MaterializationState) -> list[TraversableNode]:
        nodes = sorted(
            Selector(has_kind=TraversableNode).filter(state.graph.values()),
            key=self._order_key,
        )
        return [node for node in nodes if node.uid not in state.graph.wired_node_ids]

    def _wire_role_and_setting_dependencies(
        self,
        *,
        nodes: list[TraversableNode],
        state: _MaterializationState,
    ) -> None:
        for node in nodes:
            if isinstance(node, Scene):
                self._wire_dependencies_for_specs(
                    source=node,
                    specs=node.roles,
                    dependency_kind=Role,
                    provider_kind=Actor,
                    ref_key="actor_ref",
                    templ_ref_key="actor_template_ref",
                    state=state,
                )
                self._wire_dependencies_for_specs(
                    source=node,
                    specs=node.settings,
                    dependency_kind=Setting,
                    provider_kind=Location,
                    ref_key="location_ref",
                    templ_ref_key="location_template_ref",
                    state=state,
                )
            if isinstance(node, Block):
                self._wire_dependencies_for_specs(
                    source=node,
                    specs=node.roles,
                    dependency_kind=Role,
                    provider_kind=Actor,
                    ref_key="actor_ref",
                    templ_ref_key="actor_template_ref",
                    state=state,
                )
                self._wire_dependencies_for_specs(
                    source=node,
                    specs=node.settings,
                    dependency_kind=Setting,
                    provider_kind=Location,
                    ref_key="location_ref",
                    templ_ref_key="location_template_ref",
                    state=state,
                )

    def _wire_menu_fanouts(
        self,
        *,
        nodes: list[TraversableNode],
        state: _MaterializationState,
    ) -> None:
        for node in nodes:
            if isinstance(node, MenuBlock):
                self._wire_menu_fanout_for_block(node=node, state=state)

    def _wire_block_actions(
        self,
        *,
        nodes: list[TraversableNode],
        state: _MaterializationState,
    ) -> None:
        for node in nodes:
            if isinstance(node, Block):
                self._wire_actions_for_block(node=node, specs=node.redirects, state=state)
                self._wire_actions_for_block(node=node, specs=node.continues, state=state)
                self._wire_actions_for_block(node=node, specs=node.actions, state=state)

    def _wire_media_dependencies(
        self,
        *,
        nodes: list[TraversableNode],
        state: _MaterializationState,
    ) -> None:
        for node in nodes:
            if isinstance(node, Block):
                self._wire_media_for_block(node=node, state=state)

    @staticmethod
    def _mark_nodes_wired(
        *,
        nodes: list[TraversableNode],
        state: _MaterializationState,
    ) -> None:
        for node in nodes:
            state.graph.wired_node_ids.add(node.uid)

    def _wire_media_for_block(
        self,
        *,
        node: Block,
        state: _MaterializationState,
    ) -> None:
        for index, spec in enumerate(node.media):
            if not isinstance(spec, dict):
                continue

            source_kind = self._media_source_kind(spec)
            spec.setdefault("source_kind", source_kind)

            if source_kind == "potential":
                raw_spec = spec.get("spec")
                spec.setdefault("script_spec", raw_spec)
                spec.setdefault("realized_spec", None)
                spec.setdefault("final_spec", None)
                spec.setdefault("fallback_text", self._coerce_str(spec.get("text")))
                try:
                    media_spec = MediaSpec.from_authoring(raw_spec)
                except (TypeError, ValueError) as exc:
                    spec["spec_error"] = str(exc)
                    state.report.warnings.append(
                        f"Skipped inline media spec on block {node.get_label()!r}: {exc}"
                    )
                    continue

                dep = MediaDep(
                    registry=state.graph,
                    label=self._coerce_str(spec.get("label")) or f"media_{node.get_label()}_{index}",
                    predecessor_id=node.uid,
                    media_spec=media_spec,
                    media_role=self._coerce_str(spec.get("media_role")),
                    caption=self._coerce_str(spec.get("text") or spec.get("caption")),
                    scope=self._coerce_str(spec.get("scope")) or "story",
                    hard=bool(spec.get("hard", False)),
                    script_spec=dict(raw_spec) if isinstance(raw_spec, dict) else None,
                )
                spec["dependency_id"] = dep.uid
                continue

            if source_kind != "inventory":
                continue

            media_id = self._coerce_str(spec.get("name"))
            if not media_id:
                continue

            dep = MediaDep(
                registry=state.graph,
                label=self._coerce_str(spec.get("label")) or f"media_{node.get_label()}_{index}",
                predecessor_id=node.uid,
                media_id=media_id,
                media_role=self._coerce_str(spec.get("media_role")),
                caption=self._coerce_str(spec.get("text") or spec.get("caption")),
                scope=self._coerce_str(spec.get("scope")),
                hard=bool(spec.get("hard", False)),
            )
            spec["dependency_id"] = dep.uid
            spec.setdefault("fallback_text", self._coerce_str(spec.get("text")))

    def _wire_actions_for_block(
        self,
        *,
        node: Block,
        specs: list[dict[str, Any]],
        state: _MaterializationState,
    ) -> None:
        for index, spec in enumerate(specs):
            authored_successor_ref = self._coerce_str(spec.get("authored_successor_ref"))
            successor_ref = self._coerce_str(spec.get("successor_ref"))
            successor_is_absolute = bool(spec.get("successor_is_absolute", False))
            if successor_ref is None:
                successor_ref = self._coerce_str(
                    spec.get("successor")
                    or spec.get("next")
                    or spec.get("target_ref")
                    or spec.get("target_node")
                )
            if not successor_ref:
                msg = (
                    f"Block '{node.get_label()}' action[{index}] is missing successor "
                    "(expected one of: successor, next, successor_ref, target_ref, target_node)"
                )
                raise ValueError(msg)
            activation = self._coerce_str(spec.get("trigger") or spec.get("activation"))
            trigger_phase = Action.trigger_phase_from_activation(activation)

            action = Action(
                registry=state.graph,
                label=spec.get("label") or f"action_{node.label}_{index}",
                predecessor_id=node.uid,
                text=self._coerce_str(spec.get("text") or spec.get("content") or spec.get("label"))
                or "",
                successor_ref=successor_ref,
                activation=activation,
                predicate=self._coerce_str(spec.get("predicate")),
                payload=spec.get("payload"),
                accepts=spec.get("accepts") or spec.get("payload_schema"),
                ui_hints=(
                    spec.get("ui_hints")
                    or spec.get("ui_hint")
                    or spec.get("hints")
                    or spec.get("presentation_hints")
                ),
                trigger_phase=trigger_phase,
            )

            target = state.id_to_entity.get(successor_ref)
            if isinstance(target, TraversableNode):
                action.set_successor(target)
                continue

            requirement = Requirement(
                has_kind=TraversableNode,
                has_identifier=successor_ref,
                authored_path=authored_successor_ref or successor_ref,
                is_qualified=self._is_qualified_path(authored_successor_ref or successor_ref),
                is_absolute=successor_is_absolute,
                provision_policy=ProvisionPolicy.ANY,
                hard_requirement=True,
            )
            if state.report.mode is InitMode.LAZY:
                self._validate_lazy_destination(
                    state=state,
                    source=node,
                    action=action,
                    authored_ref=authored_successor_ref or successor_ref,
                    canonical_ref=successor_ref,
                    requirement=requirement,
                )

            Dependency(
                registry=state.graph,
                label="destination",
                predecessor_id=action.uid,
                requirement=requirement,
            )
            if state.report.mode is InitMode.LAZY:
                state.report.warnings.append(
                    f"{state.report.mode.value.upper()} init left action destination unresolved; "
                    f"action={action.get_label()!r}, expected={successor_ref!r}"
                )

    def _wire_menu_fanout_for_block(
        self,
        *,
        node: MenuBlock,
        state: _MaterializationState,
    ) -> None:
        for index, selector_spec in enumerate(MenuBlock.normalize_menu_selectors(node.menu_items)):
            requirement_data = dict(selector_spec)
            requirement_data.setdefault("has_kind", TraversableNode)
            requirement = Requirement(
                hard_requirement=False,
                **requirement_data,
            )
            Fanout(
                registry=state.graph,
                label=f"fanout_{node.get_label()}_{index}",
                predecessor_id=node.uid,
                requirement=requirement,
                tags={"dynamic", "fanout", "menu"},
            )

    def _wire_dependencies_for_specs(
        self,
        *,
        source: TraversableNode,
        specs: list[dict[str, Any]],
        dependency_kind: type[Dependency],
        provider_kind: type[GraphItem],
        ref_key: str,
        templ_ref_key: str,
        state: _MaterializationState,
    ) -> None:
        for index, spec in enumerate(specs):
            label = self._coerce_str(spec.get("label")) or f"dep_{index}"
            identifier = self._coerce_str(spec.get(ref_key) or spec.get(templ_ref_key))
            policy = self._resolve_policy(spec.get("policy") or spec.get("requirement_policy"))
            hard = bool(spec.get("hard", True))

            requirement_kwargs: dict[str, Any] = {
                "has_kind": provider_kind,
                "provision_policy": policy,
                "hard_requirement": hard,
            }
            if identifier is not None:
                requirement_kwargs["has_identifier"] = identifier
                requirement_kwargs["authored_path"] = identifier
                requirement_kwargs["is_qualified"] = self._is_qualified_path(identifier)

            requirement = Requirement(**requirement_kwargs)
            dep = dependency_kind(
                registry=state.graph,
                label=label,
                predecessor_id=source.uid,
                requirement=requirement,
            )

            if identifier:
                candidate = state.id_to_entity.get(identifier)
                if isinstance(candidate, provider_kind):
                    dep.set_provider(candidate)

    @staticmethod
    def _media_source_kind(spec: Mapping[str, Any]) -> str:
        if spec.get("url") is not None:
            return "url"
        if spec.get("data") is not None:
            return "data"
        if spec.get("name"):
            return "inventory"
        if spec.get("spec") is not None:
            return "potential"
        return "legacy"

    def _prelink_dependencies(
        self,
        *,
        dependencies: list[Dependency],
        state: _MaterializationState,
    ) -> None:
        for dep in dependencies:
            ctx = self._make_prelink_ctx(state=state, cursor_id=dep.predecessor_id)
            resolver = Resolver.from_ctx(ctx)
            was_satisfied = dep.satisfied
            resolved = resolver.resolve_dependency(dep, allow_stubs=False, _ctx=ctx)

            if resolved and dep.satisfied:
                if not was_satisfied:
                    state.report.bump_prelinked("resolved")
            else:
                state.report.bump_prelinked("unresolved")
                unresolved = UnresolvedDependency(
                    dependency_id=dep.uid,
                    source_id=dep.predecessor_id,
                    label=dep.label,
                    identifier=self._requirement_identifier(dep.requirement),
                    hard_requirement=dep.requirement.hard_requirement,
                )
                if dep.requirement.hard_requirement:
                    state.report.unresolved_hard.append(unresolved)
                else:
                    state.report.unresolved_soft.append(unresolved)

    def _project_action_successors_from_dependencies(
        self,
        *,
        dependencies: list[Dependency],
    ) -> None:
        for dep in dependencies:
            predecessor = dep.predecessor
            if isinstance(predecessor, Action) and isinstance(dep.successor, TraversableNode):
                predecessor.set_successor(dep.successor)

    def _prelink_fanouts(
        self,
        *,
        fanouts: list[Fanout],
        state: _MaterializationState,
    ) -> None:
        for fanout in fanouts:
            ctx = self._make_prelink_ctx(state=state, cursor_id=fanout.predecessor_id)
            resolver = Resolver.from_ctx(ctx)
            resolver.resolve_fanout(fanout, _ctx=ctx)
            state.report.bump_prelinked("fanout_resolved")

    def _project_prelinked_menu_actions_for_menus(
        self,
        *,
        menus: list[MenuBlock],
        state: _MaterializationState,
    ) -> None:
        for menu in menus:
            self._project_prelinked_menu_actions(menu=menu, state=state)

    @staticmethod
    def _verify_prelinked_story_graph(*, state: _MaterializationState) -> None:
        assert_traversal_contracts(state.graph)

    @staticmethod
    def _raise_on_unresolved_hard_dependencies(*, state: _MaterializationState) -> None:
        if state.report.unresolved_hard:
            raise GraphInitializationError(state.report)

    def _sorted_dependencies(self, *, state: _MaterializationState) -> list[Dependency]:
        return sorted(
            Selector(has_kind=Dependency).filter(state.graph.values()),
            key=self._order_key,
        )

    def _sorted_fanouts(self, *, state: _MaterializationState) -> list[Fanout]:
        return sorted(
            Selector(has_kind=Fanout).filter(state.graph.values()),
            key=self._order_key,
        )

    def _sorted_menu_blocks(self, *, state: _MaterializationState) -> list[MenuBlock]:
        return sorted(
            Selector(has_kind=MenuBlock).filter(state.graph.values()),
            key=self._order_key,
        )

    @staticmethod
    def _make_prelink_ctx(
        *,
        state: _MaterializationState,
        cursor_id: UUID | None,
    ) -> _PrelinkCtx:
        return _PrelinkCtx(
            graph=state.graph,
            template_registry=state.template_registry,
            cursor_id=cursor_id,
        )

    def _project_prelinked_menu_actions(
        self,
        *,
        menu: MenuBlock,
        state: _MaterializationState,
    ) -> None:
        graph = state.graph

        for edge in list(menu.edges_out(Selector(has_kind=Action, trigger_phase=None))):
            tags = getattr(edge, "tags", set()) or set()
            if {"dynamic", "fanout", "menu"}.issubset(tags):
                graph.remove(edge.uid)

        affordances = [
            affordance
            for affordance in menu.edges_out(Selector(has_kind=Affordance))
            if {"dynamic", "fanout"}.issubset(getattr(affordance, "tags", set()) or set())
        ]

        for index, affordance in enumerate(affordances):
            provider = affordance.successor or affordance.provider
            if provider is None:
                continue

            Action(
                registry=graph,
                label=f"menu_{menu.get_label()}_{index}",
                predecessor_id=menu.uid,
                successor_id=provider.uid,
                text=MenuBlock.action_text_for(provider),
                tags={"dynamic", "fanout", "menu"},
            )

    @staticmethod
    def _coerce_str(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _order_key(item: GraphItem) -> tuple[int, int, str, str, str]:
        """Return deterministic ordering key for graph items with optional seq."""
        seq = getattr(item, "seq", None)
        has_seq = isinstance(seq, int)
        label = item.get_label() if hasattr(item, "get_label") else ""
        return (
            0 if has_seq else 1,
            int(seq) if has_seq else 0,
            item.__class__.__name__,
            str(label),
            str(item.uid),
        )

    @staticmethod
    def _resolve_policy(value: Any) -> ProvisionPolicy:
        if isinstance(value, ProvisionPolicy):
            return value
        if isinstance(value, str):
            key = value.upper()
            if key in ProvisionPolicy.__members__:
                return ProvisionPolicy[key]
        return ProvisionPolicy.ANY

    @staticmethod
    def _requirement_identifier(requirement: Requirement) -> str | None:
        extra = requirement.__pydantic_extra__ or {}
        value = extra.get("has_identifier")
        return str(value) if value is not None else None

    def _validate_lazy_destination(
        self,
        *,
        state: _MaterializationState,
        source: TraversableNode,
        action: Action,
        authored_ref: str | None,
        canonical_ref: str,
        requirement: Requirement,
    ) -> None:
        ctx = _PrelinkCtx(
            graph=state.graph,
            template_registry=state.template_registry,
            cursor_id=source.uid,
        )
        resolver = Resolver.from_ctx(ctx)
        offers = resolver.inspect_template_dependency_offers(requirement, _ctx=ctx)
        candidates = self._unique_template_candidates(offers)
        if len(candidates) == 1:
            return

        reason = (
            ResolutionFailureReason.NO_TEMPLATE
            if len(candidates) == 0
            else ResolutionFailureReason.AMBIGUOUS_TEMPLATE
        )
        raise ResolutionError(
            source_node_id=source.uid,
            source_node_label=source.get_label(),
            action_id=action.uid,
            action_label=action.get_label(),
            authored_ref=authored_ref,
            canonical_ref=canonical_ref,
            reason=reason,
            selector=self._serialize_selector(requirement),
            world_id=self._world_id(state),
            bundle_id=self._bundle_id(state),
        )

    @staticmethod
    def _unique_template_candidates(offers: list[ProvisionOffer]) -> list[EntityTemplate]:
        candidates: list[EntityTemplate] = []
        seen: set[UUID] = set()
        for offer in offers:
            candidate = offer.candidate
            if not isinstance(candidate, EntityTemplate):
                continue
            candidate_uid = candidate.uid
            if candidate_uid in seen:
                continue
            seen.add(candidate_uid)
            candidates.append(candidate)
        return candidates

    @staticmethod
    def _serialize_selector(requirement: Requirement) -> dict[str, Any]:
        selector: dict[str, Any] = {}
        extra = requirement.__pydantic_extra__ or {}

        has_kind = extra.get("has_kind")
        if isinstance(has_kind, type):
            selector["has_kind"] = f"{has_kind.__module__}.{has_kind.__name__}"
        elif has_kind is not None:
            selector["has_kind"] = str(has_kind)

        has_identifier = extra.get("has_identifier")
        if has_identifier is not None:
            selector["has_identifier"] = str(has_identifier)

        has_tags = extra.get("has_tags")
        if isinstance(has_tags, (set, tuple, list)):
            selector["has_tags"] = [str(tag) for tag in has_tags]
        elif has_tags is not None:
            selector["has_tags"] = str(has_tags)

        selector["authored_path"] = requirement.authored_path
        selector["is_qualified"] = requirement.is_qualified
        selector["is_absolute"] = requirement.is_absolute
        selector["provision_policy"] = requirement.provision_policy.name
        return selector

    @staticmethod
    def _world_id(state: _MaterializationState) -> str | None:
        world = getattr(state.graph, "world", None)
        label = getattr(world, "label", None)
        if isinstance(label, str) and label:
            return label
        return None

    @staticmethod
    def _bundle_id(state: _MaterializationState) -> str | None:
        label = state.bundle_id
        if isinstance(label, str) and label:
            return label
        return None

    @staticmethod
    def _qualify_successor_ref(*, successor_ref: str | None, source: TraversableNode) -> str | None:
        # Legacy helper retained while other non-action callers migrate.
        # Compiler canonicalization is authoritative for action destinations.
        if not successor_ref:
            return None
        if StoryMaterializer._is_qualified_path(successor_ref):
            return successor_ref

        parent = source.parent
        parent_label = getattr(parent, "label", None)
        if parent_label:
            return f"{parent_label}.{successor_ref}"
        return successor_ref

    @staticmethod
    def _is_qualified_path(path: str | None) -> bool:
        return isinstance(path, str) and "." in path
