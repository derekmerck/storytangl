"""World singleton coordinating managers for story construction.

Examples
--------
Create worlds through the service registry in normal runtime flows:

.. code-block:: python

    from tangl.service.world_registry import WorldRegistry

    registry = WorldRegistry()
    world = registry.get_world("my_world")

Tests can compile directly from bundles when bypassing discovery:

.. code-block:: python

    from pathlib import Path

    from tangl.loaders import WorldBundle, WorldCompiler

    bundle = WorldBundle.load(Path("tests/worlds/my_world"))
    compiler = WorldCompiler()
    world = compiler.compile(bundle)
"""

from __future__ import annotations
import logging
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, Iterator
from uuid import UUID

from pydantic import ConfigDict, Field

from tangl.type_hints import UniqueLabel
from tangl.utils.sanitize_str import sanitize_path
from tangl.core.graph.graph import Graph, GraphItem
from tangl.core.graph.node import Node
from tangl.core.graph.subgraph import Subgraph
from tangl.core.singleton import Singleton
from tangl.vm import ProvisioningPolicy
from tangl.vm.provision.open_edge import Dependency
from tangl.vm.provision.requirement import Requirement
from tangl.ir.core_ir import BaseScriptItem
from tangl.ir.story_ir.scene_script_models import BlockScript

# Integrated Story Domains
from .domain_manager import DomainManager  # behaviors and classes
from .script_manager import ScriptManager  # concept templates
from .asset_manager import AssetManager    # platonic objects
# from tangl.discourse.voice_manager import VoiceManager   # narrative and character styles

logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARNING)


if TYPE_CHECKING:  # pragma: no cover - hinting only
    from tangl.media.media_resource.resource_manager import ResourceManager
    from tangl.story.episode.scene import Scene
    from tangl.story.story_graph import StoryGraph
    from tangl.loaders import WorldBundle
else:  # pragma: no cover - runtime alias
    StoryGraph = Graph


class World(Singleton):
    """World(label: UniqueLabel, script_manager: ScriptManager, ...)

    Singleton container that aggregates the managers required to instantiate a
    story from a compiled script.

    Why
    ---
    Worlds provide the configuration nexus for running stories. They bundle the
    script source, domain-specific class registry, asset definitions, and media
    references so new stories can be materialized deterministically.

    Key Features
    ------------
    * **Four-manager architecture** – requires explicit script, domain, asset,
      and resource managers (resource manager may be ``None`` when media is
      absent).
    * **Metadata capture** – caches script metadata for quick access (e.g.
      world name).
    * **Story factory hook** – :meth:`create_story` entry point for generating
      :class:`StoryGraph` instances (full implementation arrives in Phase 2).

    API
    ---
    - :attr:`script_manager`
    - :attr:`domain_manager`
    - :attr:`asset_manager`
    - :attr:`resource_manager`
    - :meth:`create_story`
    """

    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True, extra="allow")

    metadata: dict[str, Any] = Field(default_factory=dict)
    name: str = Field(default="")

    def __init__(
        self,
        *,
        label: UniqueLabel,
        script_manager: ScriptManager,
        domain_manager: DomainManager,
        asset_manager: AssetManager,
        resource_manager: "ResourceManager | None",
        metadata: dict[str, Any],
    ) -> None:
        super().__init__(label=label)
        self.script_manager = script_manager
        self.domain_manager = domain_manager
        self.asset_manager = asset_manager
        self.resource_manager = resource_manager
        self.metadata = metadata
        self.name = metadata.get("title", label)

        self._bundle: WorldBundle | None = None
        self._block_scripts: dict[UUID, BlockScript] = {}

    def create_story(self, story_label: str, mode: str = "full") -> StoryGraph:
        """Create a new story instance from the world script."""

        if mode == "full":
            return self._create_story_full(story_label)
        if mode == "lazy":
            return self._create_story_lazy(story_label)
        if mode == "hybrid":
            return self._create_story_hybrid(story_label)
        raise NotImplementedError(f"Mode {mode} not yet implemented")

    def find_templates(self, *args, **criteria) -> Iterator[BaseScriptItem]:
        """Return a template by ``label`` if it has been registered."""
        return self.script_manager.find_templates(*args, **criteria)

    def find_template(self, *args, **criteria) -> BaseScriptItem | None:
        """Return a template by ``label`` if it has been registered."""
        return self.script_manager.find_template(*args, **criteria)

    def _materialize_from_template(
        self,
        template: BaseScriptItem,
        graph: StoryGraph,
    ) -> Node:
        """Materialize a template for dispatch-driven customization."""

        from tangl.core.factory import TemplateFactory
        from tangl.story.fabula.address_resolver import ensure_instance

        address = self._normalize_template_address(template)
        factory = TemplateFactory(label="world_materialize")
        factory.add(template)
        return ensure_instance(
            graph,
            address,
            factory,
            world=self,
            allow_archetypes=True,
        )

    def _create_story_lazy(self, story_label: str) -> StoryGraph:
        """Create story with only the seed block materialized."""

        from tangl.story.fabula.address_resolver import ensure_instance
        from tangl.story.story_graph import StoryGraph

        graph = StoryGraph(label=story_label, world=self)
        graph.factory = self.script_manager.template_factory

        globals_ns = self.script_manager.get_story_globals() or {}
        if globals_ns:
            graph.locals.update(globals_ns)
        from tangl.story.concepts.item import Flag, Item

        graph.locals.setdefault("Item", Item)
        graph.locals.setdefault("Flag", Flag)

        start_address = self._get_start_address()
        start_node = ensure_instance(
            graph,
            start_address,
            self.script_manager.template_factory,
            world=self,
        )

        graph.initial_cursor_id = start_node.uid
        return graph

    def ensure_scope(self, parent_label: str | None, graph: StoryGraph) -> Subgraph | None:
        """Ensure that a container described by ``parent_label`` exists in ``graph``.

        Deprecated: prefer :func:`tangl.story.fabula.address_resolver.ensure_namespace`
        or :func:`tangl.story.fabula.address_resolver.ensure_instance`.
        """

        import warnings

        warnings.warn(
            "World.ensure_scope is deprecated. Use ensure_namespace or ensure_instance.",
            DeprecationWarning,
            stacklevel=2,
        )

        if parent_label is None:
            return None

        from tangl.story.fabula.address_resolver import ensure_namespace

        return ensure_namespace(graph, parent_label)

    def _attach_action_requirements(
        self,
        graph: StoryGraph,
        node: Node,
        action_scripts: list[dict[str, Any]],
    ) -> None:
        """Create action edges with requirements for successor blocks."""

        for action_data in action_scripts:
            if hasattr(action_data, "model_dump"):
                payload_get = lambda key: getattr(action_data, key, None)  # noqa: E731
            elif isinstance(action_data, Mapping):
                payload_get = action_data.get
            else:
                continue

            successor_ref = payload_get("successor")
            if not successor_ref:
                continue

            successor_identifier = self._normalize_successor_address(
                successor_ref=str(successor_ref),
                source_node=node,
            )

            action_cls = self.domain_manager.resolve_class(
                payload_get("obj_cls") or "tangl.story.episode.action.Action"
            ) or Node

            trigger_phase = self._map_activation_to_phase(
                payload_get("activation") or payload_get("trigger")
            )

            label = payload_get("label") or payload_get("text")

            entry_effects = payload_get("entry_effects") or []
            final_effects = (
                payload_get("final_effects")
                or payload_get("effects")
                or []
            )

            destination = graph.find_one(path=successor_identifier)
            destination_id = destination.uid if destination is not None else None

            action = action_cls(
                graph=graph,
                source=node,
                destination_id=destination_id,
                destination=destination,
                label=label,
                content=payload_get("text"),
                conditions=payload_get("conditions") or [],
                entry_effects=entry_effects,
                final_effects=final_effects,
                trigger_phase=trigger_phase,
            )

            graph.add(action)

            from tangl.vm.provision import Requirement, ProvisioningPolicy
            from tangl.vm.provision.open_edge import Dependency

            req = Requirement(
                graph=graph,
                identifier=successor_identifier,
                template_ref=successor_identifier,
                policy=ProvisioningPolicy.CREATE_TEMPLATE,
                hard_requirement=True,
            )

            dependency = Dependency(
                graph=graph,
                source=action,
                requirement=req,
                label="destination",
            )

            if destination is not None:
                dependency.destination = destination
                req.provider = destination

            graph.add(dependency)

    def _normalize_successor_address(self, *, successor_ref: str, source_node: Node) -> str:
        """Normalize successor references into address-based identifiers."""

        successor_ref = sanitize_path(successor_ref)
        if "." in successor_ref:
            return successor_ref
        source_path = getattr(source_node, "path", "")
        if "." in source_path:
            parent_path = source_path.rsplit(".", 1)[0]
            return f"{parent_path}.{successor_ref}"
        return successor_ref

    def _create_story_full(self, story_label: str) -> StoryGraph:
        """Materialize a fully-instantiated :class:`StoryGraph`."""

        from tangl.story.fabula.address_resolver import ensure_instance
        from tangl.story.story_graph import StoryGraph

        globals_ns = self.script_manager.get_story_globals() or {}
        graph = StoryGraph(label=story_label, world=self, locals=globals_ns)
        graph.factory = self.script_manager.template_factory
        from tangl.story.concepts.item import Flag, Item

        graph.locals.setdefault("Item", Item)
        graph.locals.setdefault("Flag", Flag)

        self._build_items(graph)
        self._build_flags(graph)

        declared_templates = self._get_declared_templates()
        script_label = getattr(self.script_manager.master_script, "label", None)

        def _normalize_address(template: BaseScriptItem) -> str:
            address = getattr(template, "path", "")
            if script_label and address.startswith(f"{script_label}."):
                return address[len(script_label) + 1:]
            return address

        declared_templates.sort(key=lambda template: len(_normalize_address(template).split(".")))

        for template in declared_templates:
            try:
                address = _normalize_address(template)
                ensure_instance(
                    graph,
                    address,
                    self.script_manager.template_factory,
                    world=self,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to materialize '%s': %s",
                    getattr(template, "path", None),
                    exc,
                    exc_info=True,
                )

        actor_map, location_map = self._build_dependency_maps(graph)
        self._resolve_open_dependencies(
            graph=graph,
            actor_map=actor_map,
            location_map=location_map,
        )

        start_address = self._get_start_address()
        start_node = graph.find_one(path=start_address)
        if start_node is None:
            raise ValueError(f"Start node not found at '{start_address}'")

        graph.initial_cursor_id = start_node.uid
        return graph

    def _get_declared_templates(self) -> list[BaseScriptItem]:
        """Return templates that declare instances."""

        return list(
            self.script_manager.template_factory.find_all(declares_instance=True)
        )

    def _get_start_address(self) -> str:
        """Return the address for the starting node."""

        metadata = self.script_manager.get_story_metadata()
        start_at = metadata.get("start_at")
        if not start_at:
            raise ValueError("No start_at specified in metadata")
        script_label = getattr(self.script_manager.master_script, "label", None)
        if script_label and start_at.startswith(f"{script_label}."):
            return start_at[len(script_label) + 1:]
        return start_at

    def _build_dependency_maps(
        self,
        graph: StoryGraph,
    ) -> tuple[dict[str, UUID], dict[str, UUID]]:
        """Collect actor and location identifiers for dependency resolution."""

        from tangl.story.concepts.actor import Actor
        from tangl.story.concepts.location import Location

        actor_map = self._index_nodes_by_identifier(graph, Actor)
        location_map = self._index_nodes_by_identifier(graph, Location)
        return actor_map, location_map

    def _index_nodes_by_identifier(
        self,
        graph: StoryGraph,
        node_cls: type[Node],
    ) -> dict[str, UUID]:
        """Return a map of labels and paths for nodes of a given class."""

        index: dict[str, UUID] = {}
        for node in graph.find_nodes(is_instance=node_cls):
            if node.label:
                index.setdefault(node.label, node.uid)
            path = getattr(node, "path", None)
            if path:
                index.setdefault(path, node.uid)
        return index

    def _build_items(self, graph: StoryGraph) -> dict[str, UUID]:
        """Instantiate items defined in the script into ``graph``."""

        item_map: dict[str, UUID] = {}
        for item_data in self.script_manager.get_unstructured("items") or ():
            payload = dict(item_data)
            label = payload.get("label")
            if not label:
                continue
            cls = self.domain_manager.resolve_class(payload.get("obj_cls"))
            item = cls.structure(self._prepare_payload(cls, payload, graph))
            item_map[label] = item.uid
        return item_map

    def _build_flags(self, graph: StoryGraph) -> dict[str, UUID]:
        """Instantiate flags defined in the script into ``graph``."""

        flag_map: dict[str, UUID] = {}
        for flag_data in self.script_manager.get_unstructured("flags") or ():
            payload = dict(flag_data)
            label = payload.get("label")
            if not label:
                continue
            cls = self.domain_manager.resolve_class(payload.get("obj_cls"))
            flag = cls.structure(self._prepare_payload(cls, payload, graph))
            flag_map[label] = flag.uid
        return flag_map

    def _resolve_open_dependencies(
        self,
        *,
        graph: StoryGraph,
        actor_map: dict[str, UUID],
        location_map: dict[str, UUID],
    ) -> None:
        """Resolve role and setting requirements against existing nodes."""

        from tangl.story.concepts.actor.role import Role
        from tangl.story.concepts.location.setting import Setting

        for dependency in list(graph.find_edges(is_instance=Dependency)):
            requirement = getattr(dependency, "requirement", None)
            if requirement is None or requirement.satisfied:
                continue

            if isinstance(dependency, Role):
                provider = self._resolve_role_provider(
                    requirement=requirement,
                    actor_map=actor_map,
                    graph=graph,
                )
            elif isinstance(dependency, Setting):
                provider = self._resolve_setting_provider(
                    requirement=requirement,
                    location_map=location_map,
                    graph=graph,
                )
            else:
                provider = self._resolve_dependency_provider(
                    requirement=requirement,
                    graph=graph,
                    actor_map=actor_map,
                    location_map=location_map,
                )

            if provider is not None:
                requirement.provider = provider

    def _resolve_dependency_provider(
        self,
        *,
        requirement: Requirement,
        graph: StoryGraph,
        actor_map: dict[str, UUID],
        location_map: dict[str, UUID],
    ) -> Node | None:
        keys = [str(req_key) for req_key in (requirement.identifier,) if req_key]
        if requirement.template_ref:
            keys.append(str(requirement.template_ref))

        if requirement.policy is not ProvisioningPolicy.CREATE_TEMPLATE:
            for key in keys:
                uid = actor_map.get(key)
                if uid:
                    provider = graph.get(uid)
                    if provider is not None:
                        return provider
                uid = location_map.get(key)
                if uid:
                    provider = graph.get(uid)
                    if provider is not None:
                        return provider

        if not (requirement.policy & ProvisioningPolicy.CREATE_TEMPLATE):
            return None
        if not requirement.template_ref:
            return None

        criteria = dict(requirement.criteria or {})
        template = self.script_manager.find_template(
            identifier=str(requirement.template_ref),
            **criteria,
        )
        if template is None:
            return None

        provider = self._materialize_requirement_template(
            template=template,
            graph=graph,
            allow_existing=requirement.policy is not ProvisioningPolicy.CREATE_TEMPLATE,
        )
        if provider is None:
            return None

        target_map = self._select_dependency_map(
            template=template,
            actor_map=actor_map,
            location_map=location_map,
        )
        if target_map is not None:
            self._index_dependency_provider(target_map, provider, keys)

        return provider

    def _materialize_requirement_template(
        self,
        *,
        template: BaseScriptItem,
        graph: StoryGraph,
        allow_existing: bool = True,
    ) -> Node | None:
        from tangl.core.factory import TemplateFactory
        from tangl.story.fabula.address_resolver import ensure_instance, ensure_namespace, _materialize_at_address

        address = self._normalize_template_address(template)
        if not allow_existing:
            parent = None
            if "." in address:
                parent = ensure_namespace(graph, address.rsplit(".", 1)[0])
            return _materialize_at_address(
                template=template,
                address=address,
                parent=parent,
                graph=graph,
                domain_manager=self.domain_manager,
            )

        factory = TemplateFactory(label="dependency_template")
        factory.add(template)
        return ensure_instance(
            graph,
            address,
            factory,
            world=self,
            allow_archetypes=True,
        )

    def _normalize_template_address(self, template: BaseScriptItem) -> str:
        address = getattr(template, "path", None)
        if not address:
            label = getattr(template, "label", None)
            if label:
                return label
            raise ValueError("Template does not define a path or label.")
        script_label = getattr(self.script_manager.master_script, "label", None)
        if script_label and address.startswith(f"{script_label}."):
            return address[len(script_label) + 1:]
        return address

    @staticmethod
    def _index_dependency_provider(
        index: dict[str, UUID],
        provider: Node,
        keys: Iterable[str],
    ) -> None:
        for key in keys:
            index.setdefault(key, provider.uid)
        if provider.label:
            index.setdefault(provider.label, provider.uid)
        provider_path = getattr(provider, "path", None)
        if provider_path:
            index.setdefault(provider_path, provider.uid)

    def _select_dependency_map(
        self,
        *,
        template: BaseScriptItem,
        actor_map: dict[str, UUID],
        location_map: dict[str, UUID],
    ) -> dict[str, UUID] | None:
        from tangl.story.concepts.actor import Actor
        from tangl.story.concepts.location import Location

        obj_cls = template.obj_cls or template.get_default_obj_cls()
        if isinstance(obj_cls, str):
            obj_cls = self.domain_manager.resolve_class(obj_cls)

        if obj_cls is None:
            return None

        try:
            if issubclass(obj_cls, Actor):
                return actor_map
            if issubclass(obj_cls, Location):
                return location_map
        except TypeError:
            return None
        return None

    def _resolve_role_provider(
        self,
        *,
        requirement: Requirement,
        actor_map: dict[str, UUID],
        graph: StoryGraph,
    ) -> Node | None:
        keys = [str(req_key) for req_key in (requirement.identifier,) if req_key]
        if requirement.template_ref:
            keys.append(str(requirement.template_ref))

        if requirement.policy is not ProvisioningPolicy.CREATE_TEMPLATE:
            for key in keys:
                uid = actor_map.get(key)
                if uid:
                    existing = graph.get(uid)
                    if existing is not None:
                        return existing

        if requirement.policy & ProvisioningPolicy.CREATE_TEMPLATE and requirement.template_ref:
            from tangl.story.concepts.actor import Actor

            template = self.script_manager.find_template(
                identifier=str(requirement.template_ref),
                is_instance=Actor,
            )
            if template is None:
                return None

            provider = self._materialize_requirement_template(
                template=template,
                graph=graph,
                allow_existing=requirement.policy is not ProvisioningPolicy.CREATE_TEMPLATE,
            )
            if provider is not None:
                self._index_dependency_provider(actor_map, provider, keys)
            return provider

        return None

    def _resolve_setting_provider(
        self,
        *,
        requirement: Requirement,
        location_map: dict[str, UUID],
        graph: StoryGraph,
    ) -> Node | None:
        keys = [str(req_key) for req_key in (requirement.identifier,) if req_key]
        if requirement.template_ref:
            keys.append(str(requirement.template_ref))

        if requirement.policy is not ProvisioningPolicy.CREATE_TEMPLATE:
            for key in keys:
                uid = location_map.get(key)
                if uid:
                    existing = graph.get(uid)
                    if existing is not None:
                        return existing

        if requirement.policy & ProvisioningPolicy.CREATE_TEMPLATE and requirement.template_ref:
            from tangl.story.concepts.location import Location

            template = self.script_manager.find_template(
                identifier=str(requirement.template_ref),
                is_instance=Location,
            )
            if template is None:
                return None

            provider = self._materialize_requirement_template(
                template=template,
                graph=graph,
                allow_existing=requirement.policy is not ProvisioningPolicy.CREATE_TEMPLATE,
            )
            if provider is not None:
                self._index_dependency_provider(location_map, provider, keys)
            return provider

        return None

    def _prepare_payload(
        self,
        cls: type[Any],
        data: dict[str, Any],
        graph: StoryGraph,
        *,
        drop_keys: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Filter script data to the fields accepted by ``cls``."""

        payload = {key: value for key, value in data.items() if key not in drop_keys}
        payload.pop("obj_cls", None)
        payload.pop("block_cls", None)
        payload.pop("activation", None)
        payload.pop("trigger", None)

        if self._is_graph_item(cls):
            payload["graph"] = graph
        else:
            payload.pop("graph", None)

        model_fields = getattr(cls, "model_fields", {})
        model_config = getattr(cls, "model_config", {}) or {}
        allow_extra = (
            isinstance(model_config, dict)
            and model_config.get("extra") == "allow"
        )

        if model_fields and not allow_extra:
            allowed = set(model_fields.keys())
            aliases = {
                field.alias
                for field in model_fields.values()
                if getattr(field, "alias", None)
            }
            if self._is_graph_item(cls):
                allowed.add("graph")

            filtered: dict[str, Any] = {}
            for key, value in payload.items():
                if key in allowed or key in aliases:
                    filtered[key] = value
            payload = filtered
        return payload

    @staticmethod
    def _map_activation_to_phase(value: str | None) -> "ResolutionPhase | None":
        if value is None:
            return None

        try:
            activation = value.lower()
        except AttributeError:  # pragma: no cover - defensive guard
            return None

        from tangl.vm import ResolutionPhase as P

        if activation in {"first", "redirect"}:
            return P.PREREQS
        if activation in {"last", "continue"}:
            return P.POSTREQS
        return None

    @staticmethod
    def _is_graph_item(cls: type[Any]) -> bool:
        try:
            return issubclass(cls, GraphItem)
        except TypeError:  # pragma: no cover - defensive fallback
            return False
