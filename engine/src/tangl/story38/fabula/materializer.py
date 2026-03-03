from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import UUID

from tangl.core38 import GraphItem, Selector, TemplateRegistry
from tangl.vm38 import (
    Dependency,
    ProvisionPolicy,
    Requirement,
    Resolver,
    TraversableNode,
    assert_traversal_contracts,
    do_get_template_scope_groups,
)

from ..concepts import Actor, Location, Role, Setting
from ..episode import Action, Block, Scene
from ..story_graph import StoryGraph38
from .compiler import StoryTemplateBundle
from .script_manager38 import ScriptManager38
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
    graph: StoryGraph38
    bundle: StoryTemplateBundle
    report: InitReport
    template_to_entity: dict[UUID, GraphItem] = field(default_factory=dict)
    id_to_entity: dict[str, GraphItem] = field(default_factory=dict)
    wired_node_ids: set[UUID] = field(default_factory=set)


@dataclass(slots=True)
class _PrelinkCtx:
    graph: StoryGraph38
    template_registry: TemplateRegistry
    cursor_id: UUID | None = None
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

    # Backwards-compatible alias retained during v38 migration.
    def get_registries(self) -> list[object]:
        return self.get_authorities()

    def get_inline_behaviors(self):
        return []

    def get_meta(self) -> Mapping[str, Any]:
        return dict(self.meta or {})

    def get_story_locals(self) -> Mapping[str, Any]:
        return self.graph.get_story_locals()

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
        if hasattr(cursor, "ancestors"):
            for ancestor in cursor.ancestors:
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

    # Legacy aliases retained for compatibility with old resolver contexts.
    def get_entity_groups(self):
        return self.get_location_entity_groups()

    def get_template_groups(self):
        return self.get_template_scope_groups()


class StoryMaterializer38:
    """Materialize story38 graphs from a compiled template bundle."""

    def create_story(
        self,
        *,
        bundle: StoryTemplateBundle,
        story_label: str,
        init_mode: InitMode,
        world: object | None = None,
    ) -> StoryInitResult:
        script_manager = getattr(world, "script_manager", None) if world is not None else None
        if script_manager is None:
            script_manager = ScriptManager38(template_registry=bundle.template_registry)

        graph = StoryGraph38(
            label=story_label,
            locals=dict(bundle.locals),
            factory=bundle.template_registry,
            script_manager=script_manager,
            world=world,
        )
        report = InitReport(mode=init_mode)
        state = _MaterializationState(graph=graph, bundle=bundle, report=report)

        entry_templates = self._resolve_entry_templates(bundle)
        if not entry_templates:
            raise ValueError("No entry templates resolved for story initialization")

        if init_mode is InitMode.LAZY:
            for templ in entry_templates:
                self._materialize_with_ancestors(templ=templ, state=state)
        elif init_mode is InitMode.EAGER:
            for templ in sorted(bundle.template_registry.values(), key=self._template_depth):
                self._materialize_with_ancestors(templ=templ, state=state)
        else:
            raise ValueError(f"Unsupported init mode: {init_mode}")

        self._finalize_scene_contracts(state=state)
        self._wire_materialized_nodes(state=state)

        if init_mode is InitMode.EAGER:
            self._prelink_all_dependencies(state=state)
            assert_traversal_contracts(state.graph)
            if state.report.unresolved_hard:
                raise GraphInitializationError(state.report)

        entry_nodes: list[TraversableNode] = []
        for templ in entry_templates:
            node = state.template_to_entity.get(templ.uid)
            if isinstance(node, TraversableNode):
                entry_nodes.append(node)

        if not entry_nodes:
            raise ValueError("Entry templates did not materialize traversable nodes")

        graph.initial_cursor_ids = [node.uid for node in entry_nodes]
        graph.initial_cursor_id = graph.initial_cursor_ids[0]

        return StoryInitResult(
            graph=graph,
            report=state.report,
            entry_ids=graph.initial_cursor_ids,
            source_map=dict(bundle.source_map),
            codec_state=dict(bundle.codec_state),
            codec_id=bundle.codec_id,
        )

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

    def _resolve_entry_templates(self, bundle: StoryTemplateBundle) -> list[Any]:
        templates = []
        for identifier in bundle.entry_template_ids:
            templ = bundle.template_registry.find_one(
                Selector(has_identifier=identifier),
            )
            if templ is None:
                templ = bundle.template_registry.find_one(Selector(label=identifier))
            if templ is not None:
                templates.append(templ)
        return templates

    def _materialize_with_ancestors(self, *, templ: Any, state: _MaterializationState) -> None:
        chain: list[Any] = []
        current = templ
        while current is not None:
            chain.append(current)
            current = getattr(current, "parent", None)
        chain.reverse()

        for item in chain:
            self._materialize_one(item, state=state)

    def _materialize_one(self, templ: Any, *, state: _MaterializationState) -> GraphItem | None:
        if templ.uid in state.template_to_entity:
            return state.template_to_entity[templ.uid]

        entity = Resolver._materialize_node(
            templ,
            _ctx=state,
            role="init",
        )
        if not isinstance(entity, GraphItem):
            return None

        state.graph.add(entity)
        state.template_to_entity[templ.uid] = entity
        state.graph.template_by_entity_id[entity.uid] = templ.uid
        state.graph.template_lineage_by_entity_id[entity.uid] = self._template_lineage_ids(templ)
        state.report.bump_materialized(entity.__class__.__name__)

        templ_label = templ.get_label() if hasattr(templ, "get_label") else None
        if templ_label:
            state.id_to_entity[templ_label] = entity

        for identifier in entity.get_identifiers():
            key = str(identifier)
            state.id_to_entity.setdefault(key, entity)

        parent_templ = getattr(templ, "parent", None)
        if parent_templ is not None:
            parent_entity = state.template_to_entity.get(parent_templ.uid)
            if isinstance(parent_entity, TraversableNode) and isinstance(entity, GraphItem):
                if hasattr(parent_entity, "add_child"):
                    self._attach_child(parent_entity, entity)

        return entity

    @staticmethod
    def _attach_child(parent: Any, child: Any) -> None:
        if parent is None or not hasattr(parent, "add_child"):
            return
        parent.add_child(child)
        finalize = getattr(parent, "finalize_container_contract", None)
        if callable(finalize):
            finalize()

    @staticmethod
    def _template_lineage_ids(templ: Any) -> list[UUID]:
        """Return template lineage from nearest scope outward."""
        lineage: list[UUID] = []
        current = templ
        while current is not None:
            uid = getattr(current, "uid", None)
            if isinstance(uid, UUID):
                lineage.append(uid)
            current = getattr(current, "parent", None)
        return lineage

    def _finalize_scene_contracts(self, *, state: _MaterializationState) -> None:
        for scene in Selector(has_kind=Scene).filter(state.graph.values()):
            scene.finalize_container_contract()

    def _wire_materialized_nodes(self, *, state: _MaterializationState) -> None:
        nodes = sorted(
            Selector(has_kind=TraversableNode).filter(state.graph.values()),
            key=self._order_key,
        )
        for node in nodes:
            if node.uid in state.wired_node_ids:
                continue
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
                self._wire_actions_for_block(node=node, specs=node.redirects, state=state)
                self._wire_actions_for_block(node=node, specs=node.continues, state=state)
                self._wire_actions_for_block(node=node, specs=node.actions, state=state)

            state.wired_node_ids.add(node.uid)

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
                    spec.get("successor") or spec.get("target_ref") or spec.get("target_node")
                )
            if not successor_ref:
                msg = (
                    f"Block '{node.get_label()}' action[{index}] is missing successor "
                    "(expected one of: successor, successor_ref, target_ref, target_node)"
                )
                raise ValueError(msg)
            activation = self._coerce_str(spec.get("trigger") or spec.get("activation"))
            trigger_phase = Action.trigger_phase_from_activation(activation)

            action = Action(
                registry=state.graph,
                label=spec.get("label") or f"action_{node.label}_{index}",
                predecessor_id=node.uid,
                text=self._coerce_str(spec.get("text")) or "",
                successor_ref=successor_ref,
                activation=activation,
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

    def _wire_dependencies_for_specs(
        self,
        *,
        source: TraversableNode,
        specs: list[dict[str, Any]],
        dependency_kind: type[Dependency],
        provider_kind: type[TraversableNode],
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

    def _prelink_all_dependencies(self, *, state: _MaterializationState) -> None:
        dependencies = sorted(
            Selector(has_kind=Dependency).filter(state.graph.values()),
            key=self._order_key,
        )

        for dep in dependencies:
            ctx = _PrelinkCtx(
                graph=state.graph,
                template_registry=state.bundle.template_registry,
                cursor_id=dep.predecessor_id,
            )
            resolver = Resolver.from_ctx(ctx)
            was_satisfied = dep.satisfied
            resolved = resolver.resolve_dependency(dep, allow_stubs=False)

            if resolved and dep.satisfied:
                if not was_satisfied:
                    state.report.bump_prelinked("resolved")
                predecessor = dep.predecessor
                if isinstance(predecessor, Action) and isinstance(dep.successor, TraversableNode):
                    predecessor.set_successor(dep.successor)
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
        return (0 if has_seq else 1, int(seq) if has_seq else 0, item.__class__.__name__, str(label), str(item.uid))

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
            template_registry=state.bundle.template_registry,
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
    def _unique_template_candidates(offers: list[Any]) -> list[Any]:
        candidates: list[Any] = []
        seen: set[UUID] = set()
        for offer in offers:
            candidate = getattr(offer, "candidate", None)
            candidate_uid = getattr(candidate, "uid", None)
            if not isinstance(candidate_uid, UUID):
                continue
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
        label = getattr(state.bundle.template_registry, "label", None)
        if isinstance(label, str) and label:
            return label
        return None

    @staticmethod
    def _qualify_successor_ref(*, successor_ref: str | None, source: TraversableNode) -> str | None:
        # Legacy helper retained while other non-action callers migrate.
        # Compiler canonicalization is authoritative for action destinations.
        if not successor_ref:
            return None
        if StoryMaterializer38._is_qualified_path(successor_ref):
            return successor_ref

        parent = source.parent
        parent_label = getattr(parent, "label", None)
        if parent_label:
            return f"{parent_label}.{successor_ref}"
        return successor_ref

    @staticmethod
    def _is_qualified_path(path: str | None) -> bool:
        return isinstance(path, str) and "." in path
