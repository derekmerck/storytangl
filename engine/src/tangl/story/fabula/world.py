from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from tangl.core import EntityTemplate, Selector, Singleton, TemplateRegistry, TokenCatalog
from tangl.media import get_system_resource_manager
from tangl.media.media_resource import MediaInventory
from tangl.media.story_media import get_story_resource_manager
from tangl.vm import TraversableGraphFactory, TraversableNode
from tangl.vm.ctx import VmPhaseCtx

from ..story_graph import StoryGraph
from .compiler import StoryCompiler
from .materializer import StoryMaterializer
from .types import InitMode, StoryInitResult


def _copy_bundle_value(value: Any) -> Any:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return value


def _template_depth(templ: Any) -> tuple[int, int, str]:
    depth = 0
    current = getattr(templ, "parent", None)
    while current is not None:
        depth += 1
        current = getattr(current, "parent", None)
    seq = getattr(templ, "seq", 0)
    label = templ.get_label() if hasattr(templ, "get_label") else ""
    return depth, seq, label


def _registry_from_values(values: Iterable[Any]) -> TemplateRegistry | None:
    found: TemplateRegistry | None = None
    for item in values:
        registry = getattr(item, "registry", None)
        if not isinstance(registry, TemplateRegistry):
            continue
        if found is None:
            found = registry
            continue
        if found is not registry:
            return None
    return found


def _coerce_template_registry_item(value: Any) -> TemplateRegistry | None:
    if isinstance(value, TemplateRegistry):
        return value
    nested = getattr(value, "template_registry", None)
    if isinstance(nested, TemplateRegistry):
        return nested
    if isinstance(value, (str, bytes, dict)) or not isinstance(value, Iterable):
        return None
    return _registry_from_values(value)


def _coerce_template_registries(value: Any) -> list[TemplateRegistry]:
    if value is None:
        return []
    get_scope_groups = getattr(value, "get_template_scope_groups", None)
    raw = get_scope_groups(caller=None, graph=None) if callable(get_scope_groups) else value
    if raw is None:
        return []
    if isinstance(raw, TemplateRegistry):
        values = [raw]
    elif isinstance(raw, (str, bytes, dict)) or not isinstance(raw, Iterable):
        values = [raw]
    else:
        values = list(raw)

    registries: list[TemplateRegistry] = []
    seen_ids: set[int] = set()
    for item in values:
        registry = _coerce_template_registry_item(item)
        if registry is None:
            continue
        registry_id = id(registry)
        if registry_id in seen_ids:
            continue
        seen_ids.add(registry_id)
        registries.append(registry)
    return registries


def _coerce_token_catalogs(
    provider: Any,
    *,
    caller: Any,
    requirement: Any = None,
    graph: Any = None,
) -> list[TokenCatalog]:
    if provider is None:
        return []
    get_catalogs = getattr(provider, "get_token_catalogs", None)
    if callable(get_catalogs):
        raw = get_catalogs(caller=caller, requirement=requirement, graph=graph)
    else:
        get_tokenizable = getattr(provider, "get_tokenizable", None)
        raw = get_tokenizable() if callable(get_tokenizable) else None
    if raw is None or isinstance(raw, (str, bytes, dict)):
        return []

    values = list(raw) if isinstance(raw, Iterable) else [raw]
    catalogs: list[TokenCatalog] = []
    seen_ids: set[int] = set()
    for item in values:
        catalog: TokenCatalog | None
        if isinstance(item, TokenCatalog):
            catalog = item
        elif isinstance(item, type) and issubclass(item, Singleton):
            catalog = TokenCatalog(wst=item)
        else:
            catalog = None
        if catalog is None:
            continue
        catalog_id = id(catalog)
        if catalog_id in seen_ids:
            continue
        seen_ids.add(catalog_id)
        catalogs.append(catalog)
    return catalogs


def _extend_media_inventories(
    inventories: list[MediaInventory],
    *,
    provider: Any,
    caller: Any,
    requirement: Any = None,
    graph: Any = None,
    scope: str | None = None,
    seen_registry_ids: set[int],
) -> None:
    if provider is None:
        return
    get_inventories = getattr(provider, "get_media_inventories", None)
    raw = get_inventories(caller=caller, requirement=requirement, graph=graph) if callable(get_inventories) else provider
    if raw is None:
        return
    if isinstance(raw, (str, bytes, dict)) or not isinstance(raw, Iterable):
        values = [raw]
    else:
        values = list(raw)
    for value in values:
        inventory = MediaInventory.from_provider(value, scope=scope)
        if inventory is None:
            continue
        registry_id = id(inventory.registry)
        if registry_id in seen_registry_ids:
            continue
        seen_registry_ids.add(registry_id)
        inventories.append(inventory)


class _TemplateSubset:
    """Read-only filtered template view for VM lazy seed materialization."""

    def __init__(self, registry: TemplateRegistry, selected_ids: set[UUID]) -> None:
        self.registry = registry
        self._selected_ids = selected_ids
        self.label = f"{registry.label}.seed"

    def _values(self) -> list[Any]:
        return [
            value
            for value in self.registry.values()
            if getattr(value, "uid", None) in self._selected_ids
        ]

    def values(self) -> list[Any]:
        return self._values()

    def find_all(
        self,
        selector: Selector | None = None,
        *,
        sort_key=None,
    ) -> list[Any]:
        values = self._values()
        if selector is not None:
            values = list(selector.filter(values))
        if sort_key is not None:
            values = sorted(values, key=sort_key)
        return values

    def find_one(
        self,
        selector: Selector | None = None,
        *,
        sort_key=None,
    ) -> Any | None:
        matches = self.find_all(selector, sort_key=sort_key)
        return matches[0] if matches else None


class World(TraversableGraphFactory):
    """World(label: str)

    Unitary story authority over templates, runtime graph creation, and world
    adjunct providers.

    Why
    ----
    ``World`` is the canonical story-layer authority object. It owns the story
    template bundle, runtime behavior authorities, and compatible accessors for
    loader/service surfaces while delegating generic graph materialization to
    :class:`~tangl.vm.TraversableGraphFactory`.

    Key Features
    ------------
    * Acts as the singleton shape and behavior authority for
      :class:`~tangl.story.StoryGraph`.
    * Preserves bundle-derived metadata, locals, entries, and compile
      provenance directly on the world.
    * Keeps compatibility alias views for one phase of the world cutover.

    API
    ---
    - :meth:`create_story` is the public story initialization entry point.
    - :meth:`get_authorities` exposes world-owned dispatch registries.
    - :meth:`get_story_info_projector` returns the world-owned projector when
      present.
    - :meth:`find_template` and :meth:`find_templates` resolve directly against
      the world's template registry.
    """

    graph_type: type[StoryGraph] = StoryGraph

    bundle: Any | None = Field(default=None, exclude=True)
    metadata: dict[str, Any] = Field(default_factory=dict)
    locals: dict[str, Any] = Field(default_factory=dict)
    entry_template_ids: list[str] = Field(default_factory=list)
    source_map: dict[str, Any] = Field(default_factory=dict)
    codec_state: dict[str, Any] = Field(default_factory=dict)
    codec_id: str | None = None
    issues: list[Any] = Field(default_factory=list)

    extra_template_registries: list[TemplateRegistry] = Field(default_factory=list, exclude=True)
    assets: Any | None = None
    resources: Any | None = None
    class_registry: dict[str, Any] = Field(default_factory=dict)
    modules: list[Any] = Field(default_factory=list)
    extra_authorities: list[Any] = Field(default_factory=list)
    story_info_projector: Any | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_bundle_authority(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        extra_template_registries = list(payload.get("extra_template_registries") or [])
        bundle = payload.get("bundle")
        bundle_registry = getattr(bundle, "template_registry", None)
        if isinstance(bundle_registry, TemplateRegistry):
            templates = payload.get("templates")
            if templates is None:
                payload["templates"] = bundle_registry
            elif not isinstance(templates, TemplateRegistry):
                raise TypeError("World.templates must be a TemplateRegistry")

            bundle_defaults = {
                "metadata": getattr(bundle, "metadata", None),
                "locals": getattr(bundle, "locals", None),
                "entry_template_ids": getattr(bundle, "entry_template_ids", None),
                "source_map": getattr(bundle, "source_map", None),
                "codec_state": getattr(bundle, "codec_state", None),
                "codec_id": getattr(bundle, "codec_id", None),
                "issues": getattr(bundle, "issues", None),
            }
            for field_name, value in bundle_defaults.items():
                if field_name in payload:
                    continue
                if value is None:
                    continue
                payload[field_name] = _copy_bundle_value(value)

        if extra_template_registries:
            deduped: list[TemplateRegistry] = []
            seen_ids: set[int] = set()
            for registry in extra_template_registries:
                registry_id = id(registry)
                if registry_id in seen_ids:
                    continue
                seen_ids.add(registry_id)
                deduped.append(registry)
            payload["extra_template_registries"] = deduped

        return payload

    def get_authorities(self) -> list[object]:
        """Return world-owned behavior authorities with stable declaration order."""
        authorities: list[object] = []
        for authority in [self.dispatch, *self.extra_authorities]:
            if authority is None or authority in authorities:
                continue
            authorities.append(authority)
        return authorities

    def get_story_info_projector(self) -> Any | None:
        """Return the world-owned story-info projector when present."""
        return self.story_info_projector

    def get_entry_cursor(self, graph: StoryGraph) -> Any | None:
        """Return the default story entry, falling back to generic VM rules."""
        entry_templates = self._resolve_story_entry_templates()
        if entry_templates:
            entry_nodes = self._entry_nodes_for_templates(
                graph=graph,
                entry_templates=entry_templates,
            )
            if entry_nodes:
                return entry_nodes[0]
        return super().get_entry_cursor(graph)

    def get_template_scope_groups(
        self,
        *,
        caller: Any = None,
        graph: Any = None,
    ) -> list[TemplateRegistry]:
        """Return authoritative template registries for runtime scope discovery."""
        _ = caller, graph
        registries = [self.templates, *self.extra_template_registries]
        deduped: list[TemplateRegistry] = []
        seen_ids: set[int] = set()
        for registry in registries:
            registry_id = id(registry)
            if registry_id in seen_ids:
                continue
            seen_ids.add(registry_id)
            deduped.append(registry)
        return deduped

    def get_token_catalogs(
        self,
        *,
        caller: Any = None,
        requirement: Any = None,
        graph: Any = None,
    ) -> list[TokenCatalog]:
        catalogs = _coerce_token_catalogs(
            self.assets,
            caller=caller,
            requirement=requirement,
            graph=graph,
        )
        if catalogs:
            return catalogs
        return list(self._provide_token_catalogs())

    def get_media_inventories(
        self,
        *,
        caller: Any = None,
        requirement: Any = None,
        graph: Any = None,
    ) -> list[MediaInventory]:
        """Return optional world-authoritative media inventories."""
        story_manager = None
        if graph is not None:
            story_manager = getattr(graph, "story_resources", None)
            if story_manager is None and getattr(graph, "story_id", None) is not None:
                story_manager = get_story_resource_manager(graph.story_id, create=False)
                if story_manager is not None:
                    graph.story_resources = story_manager

        inventories: list[MediaInventory] = []
        seen_registry_ids: set[int] = set()
        _extend_media_inventories(
            inventories,
            provider=graph,
            caller=caller,
            requirement=requirement,
            graph=graph,
            scope="story",
            seen_registry_ids=seen_registry_ids,
        )
        _extend_media_inventories(
            inventories,
            provider=story_manager,
            caller=caller,
            requirement=requirement,
            graph=graph,
            scope="story",
            seen_registry_ids=seen_registry_ids,
        )
        _extend_media_inventories(
            inventories,
            provider=self.resources,
            caller=caller,
            requirement=requirement,
            graph=graph,
            scope="world",
            seen_registry_ids=seen_registry_ids,
        )
        _extend_media_inventories(
            inventories,
            provider=self.assets,
            caller=caller,
            requirement=requirement,
            graph=graph,
            scope="world",
            seen_registry_ids=seen_registry_ids,
        )
        _extend_media_inventories(
            inventories,
            provider=get_system_resource_manager(),
            caller=caller,
            requirement=requirement,
            graph=graph,
            scope="sys",
            seen_registry_ids=seen_registry_ids,
        )
        return inventories

    def find_template(self, reference: str) -> Any | None:
        """Find one template by selector, uid, identifier, or label."""
        if reference is None:
            return None
        if isinstance(reference, UUID):
            return self.templates.get(reference)

        key = str(reference)
        found = self.templates.find_one(Selector.from_identifier(key))
        if found is not None:
            return found
        return self.templates.find_one(Selector(label=key))

    def find_templates(self, selector: Selector | None = None) -> list[Any]:
        """Find all templates matching ``selector``."""
        if selector is None:
            return list(self.templates.values())
        return list(selector.filter(self.templates.values()))

    def story_materialize_template(
        self,
        template,
        _ctx: VmPhaseCtx | None = None,
    ):
        """Compatibility hook delegating story materialization to the helper."""
        return StoryMaterializer().story_materialize_template(template, _ctx=_ctx)

    def story_post_materialize(
        self,
        *,
        template,
        entity: Any,
        role,
        _ctx: VmPhaseCtx | None = None,
    ) -> None:
        """Compatibility hook delegating post-materialization policy to the helper."""
        StoryMaterializer().story_post_materialize(
            template=template,
            entity=entity,
            role=role,
            _ctx=_ctx,
        )

    def preview_requirement_contract(
        self,
        *,
        requirement,
        offer,
        graph,
        _ctx: VmPhaseCtx | None = None,
    ):
        """Compatibility hook delegating preview checks to the helper."""
        return StoryMaterializer().preview_requirement_contract(
            requirement=requirement,
            offer=offer,
            graph=graph,
            _ctx=_ctx,
        )

    @staticmethod
    def _story_entry_selector(default_entry_ref: str) -> Selector:
        return Selector.chain_or(
            Selector(has_identifier=default_entry_ref),
            Selector(has_tags={default_entry_ref}),
        )

    def _resolve_story_entry_templates(self) -> list[EntityTemplate]:
        materializer = StoryMaterializer()
        return [
            templ
            for templ in materializer._resolve_entry_templates(
                template_registry=self.templates,
                entry_template_ids=self.entry_template_ids,
            )
            if isinstance(templ, EntityTemplate)
        ]

    def _resolve_seed_entry_templates(self) -> list[EntityTemplate]:
        explicit = self._resolve_story_entry_templates()
        if explicit:
            return explicit
        return [
            templ
            for templ in self.templates.find_all(
                self._story_entry_selector(self.default_entry_ref),
                sort_key=_template_depth,
            )
            if isinstance(templ, EntityTemplate)
        ]

    def _seed_template_groups(
        self,
        entry_templates: list[EntityTemplate],
    ) -> list[_TemplateSubset]:
        selected_ids: set[UUID] = set()
        for template in entry_templates:
            current: Any | None = template
            while current is not None:
                uid = getattr(current, "uid", None)
                if isinstance(uid, UUID):
                    selected_ids.add(uid)
                current = getattr(current, "parent", None)
        return [_TemplateSubset(self.templates, selected_ids)]

    def _build_story_graph(
        self,
        *,
        story_label: str,
        init_mode: InitMode,
        freeze_shape: bool,
    ) -> StoryGraph:
        graph = StoryGraph(
            label=story_label,
            frozen_shape=(init_mode is InitMode.EAGER and freeze_shape),
            locals=dict(self.locals),
            factory=self,
        )
        graph.story_id = graph.uid
        graph.story_resources = get_story_resource_manager(graph.story_id, create=False)
        return graph

    @staticmethod
    def _entry_nodes_for_templates(
        *,
        graph: StoryGraph,
        entry_templates: list[EntityTemplate],
    ) -> list[TraversableNode]:
        nodes: list[TraversableNode] = []
        seen_ids: set[UUID] = set()
        for template in entry_templates:
            template_hash = template.content_hash()
            node = graph.find_one(
                Selector(has_kind=TraversableNode, templ_hash=template_hash),
            )
            if isinstance(node, TraversableNode) and node.uid not in seen_ids:
                seen_ids.add(node.uid)
                nodes.append(node)
        return nodes

    @staticmethod
    def _apply_story_entry_ids(
        *,
        graph: StoryGraph,
        entry_templates: list[EntityTemplate],
    ) -> None:
        entry_nodes = World._entry_nodes_for_templates(
            graph=graph,
            entry_templates=entry_templates,
        )
        graph.initial_cursor_ids = [node.uid for node in entry_nodes]
        if graph.initial_cursor_ids:
            graph.initial_cursor_id = graph.initial_cursor_ids[0]

    def create_story(
        self,
        story_label: str,
        *,
        init_mode: InitMode = InitMode.EAGER,
        freeze_shape: bool = False,
        namespace: dict[str, Any] | None = None,
    ) -> StoryInitResult:
        if freeze_shape and init_mode is not InitMode.EAGER:
            raise ValueError("freeze_shape requires InitMode.EAGER")

        materializer = StoryMaterializer()
        explicit_entry_templates = self._resolve_story_entry_templates()
        seed_entry_templates = self._resolve_seed_entry_templates()
        if init_mode is InitMode.LAZY and not seed_entry_templates:
            raise ValueError("No entry templates resolved for story initialization")

        graph = self._build_story_graph(
            story_label=story_label,
            init_mode=init_mode,
            freeze_shape=freeze_shape,
        )
        if init_mode is InitMode.EAGER:
            graph = super().materialize_graph(graph=graph)
        else:
            graph = super().materialize_seed_graph(
                graph=graph,
                template_groups=self._seed_template_groups(seed_entry_templates),
            )

        graph.rebuild_template_lineage(self.templates)
        state = materializer.make_state(
            graph=graph,
            mode=init_mode,
            template_registry=self.templates,
            entry_template_ids=list(self.entry_template_ids),
            source_map=dict(self.source_map),
            codec_state=dict(self.codec_state),
            codec_id=self.codec_id,
            bundle_id=getattr(self.templates, "label", None),
        )
        materializer._run_topology_passes(state=state)
        if init_mode is InitMode.EAGER:
            materializer._run_prelink_passes(state=state)
        materializer._recount_materialized(state=state)

        self._apply_story_entry_ids(
            graph=graph,
            entry_templates=explicit_entry_templates or seed_entry_templates,
        )
        result = materializer._build_story_init_result(state=state)

        if namespace is not None:
            override_uid = self._resolve_entry_override(result.graph, namespace)
            if override_uid is not None:
                result.graph.initial_cursor_id = override_uid
                result.graph.initial_cursor_ids[:] = [override_uid]

        return result

    def _resolve_entry_override(
        self,
        graph: Any,
        namespace: dict[str, Any],
    ) -> Any | None:
        """Return an optional init-time entry override for this world."""
        _ = graph, namespace
        return None

    @classmethod
    def from_script_data(
        cls,
        *,
        script_data: dict[str, Any],
        label: str | None = None,
        compiler: StoryCompiler | None = None,
        domain: Any | None = None,
        templates: Any | None = None,
        assets: Any | None = None,
        resources: Any | None = None,
        story_info_projector: Any | None = None,
    ) -> "World":
        from .builder import WorldBuilder

        compiler = compiler or StoryCompiler()
        bundle = compiler.compile(script_data)
        return WorldBuilder().build(
            label=label or script_data.get("label") or "story_world",
            bundle=bundle,
            assets=assets,
            resources=resources,
            extra_template_registries=_coerce_template_registries(templates),
            domain=domain,
            story_info_projector=story_info_projector,
        )
