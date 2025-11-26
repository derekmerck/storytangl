"""World singleton coordinating managers for story construction."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tangl.core.graph.edge import Edge
from tangl.core.graph.graph import Graph, GraphItem
from tangl.core.registry import Registry
from tangl.core.singleton import Singleton
from tangl.ir.core_ir import BaseScriptItem
from tangl.ir.story_ir.actor_script_models import ActorScript
from tangl.ir.story_ir.location_script_models import LocationScript
from tangl.ir.story_ir.story_script_models import ScopeSelector
from tangl.story.concepts.actor.role import Role
from tangl.story.concepts.location.setting import Setting
from tangl.media.media_resource import MediaDep
from tangl.vm.planning import MediaRequirement
from tangl.vm import ProvisioningPolicy
from tangl.vm.provision.open_edge import Dependency

# Integrated Story Domains
from .domain_manager import DomainManager  # behaviors and classes
from .script_manager import ScriptManager  # concept templates
from .asset_manager import AssetManager    # platonic objects

# from tangl.discourse.voice_manager import VoiceManager   # narrative and character styles

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


if TYPE_CHECKING:  # pragma: no cover - hinting only
    from tangl.media.media_resource.resource_manager import ResourceManager
    from tangl.story.episode.scene import Scene
    from tangl.story.story_graph import StoryGraph
else:  # pragma: no cover - runtime alias
    StoryGraph = Graph


class World(Singleton):
    """World(label: str, script_manager: ScriptManager, ...)

    Singleton container that aggregates the managers required to instantiate a
    story from a compiled script.

    Why
    ---
    Worlds provide the configuration nexus for running stories. They bundle the
    script source, domain-specific class registry, asset definitions, and media
    references so new stories can be materialized deterministically.

    Key Features
    ------------
    * **Four-manager architecture** – exposes script, domain, asset, and
      resource managers as attributes.
    * **Metadata capture** – caches script metadata for quick access (e.g. world
      name).
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
        label: str,
        script_manager: ScriptManager,
        domain_manager: Optional[DomainManager] = None,
        asset_manager: Optional[AssetManager] = None,
        resource_manager: Optional["ResourceManager"] = None,
    ) -> None:
        super().__init__(label=label)
        self.script_manager = script_manager
        self.domain_manager = domain_manager or DomainManager()
        self.asset_manager = asset_manager or AssetManager()
        self.resource_manager = resource_manager or self._create_resource_manager()

        self.metadata = script_manager.get_story_metadata() or {}
        self.name = self.metadata.get("title", label)

        self.template_registry = Registry(label=f"{label}_templates")

        self._setup_default_assets()
        self._compile_templates()

    def _create_resource_manager(self) -> "ResourceManager | None":
        try:
            from tangl.media.media_resource.resource_manager import ResourceManager as RM
        except ModuleNotFoundError:  # pragma: no cover - optional dependency gap
            return None
        return RM(Path("."))

    def _setup_default_assets(self) -> None:
        """Register built-in asset classes if not already present."""
        if "countable" in self.asset_manager.countable_classes:
            return
        try:
            from tangl.story.concepts.asset import CountableAsset
        except ModuleNotFoundError:  # pragma: no cover - optional dependency gap
            return
        self.asset_manager.register_countable_class("countable", CountableAsset)

    def _compile_templates(self) -> None:
        """Traverse script hierarchy and populate ``template_registry``."""

        script = self.script_manager.master_script

        def _extract_label(default: str | None, item: Any) -> str | None:
            if isinstance(item, BaseScriptItem):
                return item.label or item.get_label()
            if isinstance(item, Mapping):
                label_value = item.get("label")
                if isinstance(label_value, str):
                    return label_value
            return default

        def _determine_script_cls(payload: Mapping[str, Any]) -> type[BaseScriptItem]:
            obj_cls = payload.get("obj_cls")
            if isinstance(obj_cls, type) and issubclass(obj_cls, BaseScriptItem):
                return obj_cls
            if isinstance(obj_cls, str):
                lowered = obj_cls.lower()
                if "location" in lowered:
                    return LocationScript
                if "actor" in lowered:
                    return ActorScript
            if obj_cls is None:
                return ActorScript
            return ActorScript

        def _parse_template(label: str, raw_data: Any, scope: ScopeSelector | None) -> BaseScriptItem | None:
            if isinstance(raw_data, BaseScriptItem):
                template_cls: type[BaseScriptItem] = raw_data.__class__
                fields_set = getattr(raw_data, "model_fields_set", set())
                scope_specified = "scope" in fields_set
                updates: dict[str, Any] = {}
                if not raw_data.label and label:
                    updates["label"] = label
                if (
                    scope is not None
                    and not scope_specified
                    and "scope" in template_cls.model_fields
                ):
                    updates["scope"] = scope
                if updates:
                    return raw_data.model_copy(update=updates)
                return raw_data
            elif isinstance(raw_data, Mapping):
                payload = dict(raw_data)
                scope_specified = "scope" in raw_data
            else:
                logger.warning("Skipping template %s with unsupported payload %r", label, raw_data)
                return None

            payload.setdefault("label", label)
            template_cls = _determine_script_cls(payload)
            if (
                scope is not None
                and not scope_specified
                and "scope" in template_cls.model_fields
            ):
                payload.setdefault("scope", scope.model_dump())

            try:
                template = template_cls.model_validate(payload)
            except ValidationError as exc:
                logger.warning("Skipping template %s due to validation error: %s", label, exc)
                return None
            return template

        def _add_templates(templates: Mapping[str, Any] | None, scope: ScopeSelector | None) -> None:
            if not templates:
                return
            if not isinstance(templates, Mapping):
                logger.warning("Expected mapping for templates but received %r", type(templates))
                return
            for template_label, template_data in templates.items():
                label_value = template_label
                if isinstance(template_label, str):
                    label_value = template_label
                else:
                    label_value = str(template_label)
                template = _parse_template(label_value, template_data, scope)
                if template is None:
                    continue
                if template.label is None:
                    logger.warning("Skipping template without label derived from %s", template_data)
                    continue
                existing = self.template_registry.find_one(label=template.label)
                if existing is not None:
                    logger.warning(
                        "Duplicate template label %s skipped", template.label,
                    )
                    continue
                try:
                    self.template_registry.add(template)
                except ValueError as exc:
                    logger.warning("Duplicate template %s skipped: %s", template.label, exc)

        world_templates = getattr(script, "templates", None)
        if isinstance(world_templates, Mapping):
            _add_templates(world_templates, scope=None)
        elif world_templates:
            logger.warning("World templates should be a mapping; received %r", type(world_templates))

        scenes = getattr(script, "scenes", None)
        scene_items: Iterable[Any]
        if isinstance(scenes, Mapping):
            scene_items = scenes.items()
        elif isinstance(scenes, Iterable):
            scene_items = ((getattr(scene, "label", None), scene) for scene in scenes)
        else:
            scene_items = ()

        for scene_key, scene_obj in scene_items:
            scene_label = _extract_label(scene_key if isinstance(scene_key, str) else None, scene_obj)
            if scene_label is None:
                continue
            scene_templates = getattr(scene_obj, "templates", None)
            if isinstance(scene_templates, Mapping):
                _add_templates(scene_templates, scope=ScopeSelector(parent_label=scene_label))
            elif scene_templates:
                logger.warning(
                    "Scene %s templates should be a mapping; received %r",
                    scene_label,
                    type(scene_templates),
                )

            blocks = getattr(scene_obj, "blocks", None)
            if isinstance(blocks, Mapping):
                block_items: Iterable[Any] = blocks.items()
            elif isinstance(blocks, Iterable):
                block_items = ((getattr(block, "label", None), block) for block in blocks)
            else:
                block_items = ()

            for block_key, block_obj in block_items:
                block_label = _extract_label(block_key if isinstance(block_key, str) else None, block_obj)
                if block_label is None:
                    continue
                block_templates = getattr(block_obj, "templates", None)
                if isinstance(block_templates, Mapping):
                    _add_templates(
                        block_templates,
                        scope=ScopeSelector(source_label=block_label),
                    )
                elif block_templates:
                    logger.warning(
                        "Block %s templates should be a mapping; received %r",
                        block_label,
                        type(block_templates),
                    )

    def create_story(self, story_label: str, mode: str = "full") -> StoryGraph:
        """Create a new story instance from the world script."""
        if mode == "full":
            return self._create_story_full(story_label)
        raise NotImplementedError(f"Mode {mode} not yet implemented")

    @property
    def actor_templates(self) -> list[ActorScript]:
        """Return all actor templates declared in this world."""

        return list(self.template_registry.find_all(is_instance=ActorScript))

    @property
    def location_templates(self) -> list[LocationScript]:
        """Return all location templates declared in this world."""

        return list(self.template_registry.find_all(is_instance=LocationScript))

    def find_template(self, label: str) -> BaseScriptItem | None:
        """Return a template by ``label`` if it has been registered."""

        return self.template_registry.find_one(label=label)

    def _create_story_full(self, story_label: str) -> StoryGraph:
        """Materialize a fully-instantiated :class:`StoryGraph`."""
        from tangl.story.concepts.item import Item, Flag
        from tangl.story.story_graph import StoryGraph
        graph = StoryGraph(label=story_label, world=self)
        globals_ns = self.script_manager.get_story_globals() or {}
        if globals_ns:
            graph.locals.update(globals_ns)

        graph.locals.setdefault("Item", Item)
        graph.locals.setdefault("Flag", Flag)

        node_map: dict[str, UUID] = {}

        actor_map = self._build_actors(graph)
        location_map = self._build_locations(graph)
        item_map = self._build_items(graph)
        flag_map = self._build_flags(graph)

        node_map.update(actor_map)
        node_map.update(location_map)
        node_map.update(item_map)
        node_map.update(flag_map)

        block_map, action_scripts = self._build_blocks(graph)
        node_map.update(block_map)

        scene_map = self._build_scenes(
            graph,
            block_map,
            actor_map=actor_map,
            location_map=location_map,
        )
        node_map.update(scene_map)

        self._build_action_edges(graph, block_map, action_scripts)

        start_scene, start_block = self._get_starting_cursor()
        start_label = f"{start_scene}.{start_block}"
        start_uid = block_map.get(start_label)
        if start_uid is None:
            raise ValueError(f"Start block '{start_label}' not found in story graph")

        graph.initial_cursor_id = start_uid
        return graph

    def _build_actors(self, graph: StoryGraph) -> dict[str, UUID]:
        """Instantiate actors described in the script into ``graph``."""
        actor_map: dict[str, UUID] = {}
        for actor_data in self.script_manager.get_unstructured("actors") or ():
            payload = dict(actor_data)
            label = payload.get("label")
            if not label:
                continue
            cls = self.domain_manager.resolve_class(payload.get("obj_cls"))
            actor = cls.structure(self._prepare_payload(cls, payload, graph))
            actor_map[label] = actor.uid
        return actor_map

    def _build_locations(self, graph: StoryGraph) -> dict[str, UUID]:
        """Instantiate locations described in the script into ``graph``."""
        location_map: dict[str, UUID] = {}
        for location_data in self.script_manager.get_unstructured("locations") or ():
            payload = dict(location_data)
            label = payload.get("label")
            if not label:
                continue
            cls = self.domain_manager.resolve_class(payload.get("obj_cls"))
            location = cls.structure(self._prepare_payload(cls, payload, graph))
            location_map[label] = location.uid
        return location_map

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

    def _build_blocks(
        self,
        graph: StoryGraph,
    ) -> tuple[dict[str, UUID], dict[str, dict[str, list[dict[str, Any]]]]]:
        """Instantiate block nodes and collect their scripted actions."""

        node_map: dict[str, UUID] = {}
        action_scripts: dict[str, dict[str, list[dict[str, Any]]]] = {}
        scenes = self._get_scenes_dict()

        for scene_label, scene_data in scenes.items():
            blocks = self._normalize_section(scene_data.get("blocks"))
            for block_label, block_data in blocks.items():
                block_data = block_data or {}
                qualified_label = f"{scene_label}.{block_label}"
                cls = self.domain_manager.resolve_class(
                    block_data.get("obj_cls") or block_data.get("block_cls")
                )

                scripts = {
                    key: [
                        self._normalize_action_entry(self._to_dict(entry))
                        for entry in (block_data.get(key) or [])
                    ]
                    for key in ("actions", "continues", "redirects")
                }
                action_scripts[qualified_label] = scripts

                payload = self._prepare_payload(
                    cls,
                    block_data,
                    graph,
                    drop_keys=("actions", "continues", "redirects"),
                )
                payload.setdefault("label", block_label)

                block = cls.structure(payload)
                node_map[qualified_label] = block.uid

                media_entries = block_data.get("media") or []
                for media_spec in media_entries:
                    media_data = self._to_dict(media_spec)
                    requirement = MediaRequirement(
                        graph=graph,
                        template={
                            "media_path": media_data.get("media_path"),
                            "media_role": media_data.get("media_role", "narrative_im"),
                            "world_id": str(self.uid),
                        },
                        policy=ProvisioningPolicy.ANY,
                    )
                    MediaDep(graph=graph, source_id=block.uid, requirement=requirement)

        return node_map, action_scripts

    def _build_scenes(
        self,
        graph: StoryGraph,
        block_map: dict[str, UUID],
        *,
        actor_map: dict[str, UUID],
        location_map: dict[str, UUID],
    ) -> dict[str, UUID]:
        """Instantiate scenes and associate their member blocks."""

        scene_map: dict[str, UUID] = {}
        scenes = self._get_scenes_dict()

        for scene_label, scene_data in scenes.items():
            cls = self.domain_manager.resolve_class(scene_data.get("obj_cls"))
            members = self._normalize_section(scene_data.get("blocks"))
            member_ids = [
                block_map[f"{scene_label}.{block_label}"]
                for block_label in members
                if f"{scene_label}.{block_label}" in block_map
            ]

            payload = self._prepare_payload(
                cls,
                scene_data,
                graph,
                drop_keys=("blocks", "roles", "settings", "assets"),
            )
            payload.setdefault("label", scene_label)

            if member_ids and "member_ids" in getattr(cls, "model_fields", {}):
                payload["member_ids"] = member_ids

            scene = cls.structure(payload)
            scene_map[scene_label] = scene.uid

            self._wire_roles(
                graph=graph,
                source_node=scene,
                roles_data=scene_data.get("roles"),
                actor_map=actor_map,
            )
            self._wire_settings(
                graph=graph,
                source_node=scene,
                settings_data=scene_data.get("settings"),
                location_map=location_map,
            )

            for block_label, block_data in members.items():
                qualified_label = f"{scene_label}.{block_label}"
                block_uid = block_map.get(qualified_label)
                if block_uid is None:
                    continue

                block = graph.get(block_uid)
                if block is None:
                    continue

                self._wire_roles(
                    graph=graph,
                    source_node=block,
                    roles_data=block_data.get("roles"),
                    actor_map=actor_map,
                )
                self._wire_settings(
                    graph=graph,
                    source_node=block,
                    settings_data=block_data.get("settings"),
                    location_map=location_map,
                )

        return scene_map

    def _resolve_dependency_class(
        self,
        obj_cls: Any,
        *,
        fallback: type[Dependency],
    ) -> type[Dependency]:
        """Resolve ``obj_cls`` to a :class:`Dependency` subclass."""

        candidate: type[Any] | None
        if isinstance(obj_cls, type):
            candidate = obj_cls
        elif obj_cls:
            candidate = self.domain_manager.resolve_class(obj_cls)
        else:
            candidate = fallback

        try:
            if issubclass(candidate, Dependency):  # type: ignore[arg-type]
                return candidate  # type: ignore[return-value]
        except TypeError:
            pass

        logger.warning(
            "Dependency class %r is not a Dependency; using %s", obj_cls, fallback.__name__
        )
        return fallback

    def _wire_roles(
        self,
        *,
        graph: StoryGraph,
        source_node: GraphItem,
        roles_data: Any,
        actor_map: dict[str, UUID],
    ) -> None:
        roles = self._normalize_section(roles_data)
        if not roles:
            return

        for role_label, role_spec in roles.items():
            role_cls = self._resolve_dependency_class(
                role_spec.get("obj_cls"),
                fallback=Role,
            )
            payload = self._prepare_payload(
                role_cls,
                role_spec,
                graph,
            )
            payload.setdefault("label", role_label)
            payload.setdefault("source_id", source_node.uid)
            payload.setdefault("requirement_policy", ProvisioningPolicy.ANY)
            role_cls.structure(payload)

    def _wire_settings(
        self,
        *,
        graph: StoryGraph,
        source_node: GraphItem,
        settings_data: Any,
        location_map: dict[str, UUID],
    ) -> None:
        settings = self._normalize_section(settings_data)
        if not settings:
            return

        for setting_label, setting_spec in settings.items():
            setting_cls = self._resolve_dependency_class(
                setting_spec.get("obj_cls"),
                fallback=Setting,
            )
            payload = self._prepare_payload(
                setting_cls,
                setting_spec,
                graph,
            )
            payload.setdefault("label", setting_label)
            payload.setdefault("source_id", source_node.uid)
            payload.setdefault("requirement_policy", ProvisioningPolicy.ANY)
            setting_cls.structure(payload)

    def _build_action_edges(
        self,
        graph: StoryGraph,
        block_map: dict[str, UUID],
        action_scripts: dict[str, dict[str, list[dict[str, Any]]]],
    ) -> None:
        """Create edges defined by block actions and redirects."""

        scenes = self._get_scenes_dict()
        for scene_label, scene_data in scenes.items():
            blocks = self._normalize_section(scene_data.get("blocks"))
            for block_label in blocks:
                qualified_label = f"{scene_label}.{block_label}"
                source_uid = block_map.get(qualified_label)
                if source_uid is None:
                    continue

                scripts = action_scripts.get(qualified_label, {})
                for key in ("actions", "continues", "redirects"):
                    for action_data in scripts.get(key, []):
                        successor = action_data.get("successor")
                        if not successor:
                            continue
                        destination_id = self._resolve_successor(
                            successor,
                            scene_label,
                            block_map,
                        )

                        cls = self.domain_manager.resolve_class(action_data.get("obj_cls"))
                        cls = self._ensure_edge_class(cls)

                        payload = self._prepare_payload(
                            cls,
                            action_data,
                            graph,
                            drop_keys=("successor",),
                        )
                        payload.setdefault("label", action_data.get("text"))
                        payload["source_id"] = source_uid
                        payload["destination_id"] = destination_id

                        cls.structure(payload)

    def _resolve_successor(
        self,
        successor: str,
        current_scene: str,
        block_map: dict[str, UUID],
    ) -> UUID:
        """Resolve a successor reference to a block identifier."""

        if successor in block_map:
            return block_map[successor]

        qualified = f"{current_scene}.{successor}"
        if qualified in block_map:
            return block_map[qualified]

        scenes = self._get_scenes_dict()
        if successor in scenes:
            blocks = self._normalize_section(scenes[successor].get("blocks"))
            for block_label in blocks:
                candidate = f"{successor}.{block_label}"
                if candidate in block_map:
                    return block_map[candidate]

        raise ValueError(f"Could not resolve successor reference: {successor}")

    def _get_starting_cursor(self) -> tuple[str, str]:
        """Determine the starting scene and block labels for traversal."""

        metadata = self.script_manager.get_story_metadata() or {}
        scenes = self._get_scenes_dict()

        if not scenes:
            raise ValueError("Story script does not define any scenes")

        start_at = metadata.get("start_at")
        if start_at:
            if "." in start_at:
                scene_label, block_label = start_at.split(".", 1)
                return scene_label, block_label

            if start_at in scenes:
                blocks = self._normalize_section(scenes[start_at].get("blocks"))
                if not blocks:
                    raise ValueError(f"Start scene '{start_at}' has no blocks")
                first_block = next(iter(blocks))
                return start_at, first_block

        scene_label, scene_data = next(iter(scenes.items()))
        blocks = self._normalize_section(scene_data.get("blocks"))
        if not blocks:
            raise ValueError(f"Scene '{scene_label}' does not contain any blocks")
        block_label = next(iter(blocks))
        return scene_label, block_label

    def _get_scenes_dict(self) -> dict[str, dict[str, Any]]:
        scenes_iter = self.script_manager.get_unstructured("scenes") or ()
        scenes: dict[str, dict[str, Any]] = {}
        for scene in scenes_iter:
            label = scene.get("label")
            if not label:
                continue
            scenes[label] = scene
        if scenes:
            return scenes

        raw_scenes = getattr(self.script_manager.master_script, "scenes", None)
        return self._normalize_section(raw_scenes)

    def _normalize_section(self, section: Any) -> dict[str, dict[str, Any]]:
        """Normalize script sections into a label-indexed mapping."""

        if not section:
            return {}

        items: Iterable[tuple[str, dict[str, Any]]]
        if isinstance(section, dict):
            items = (
                (label, self._to_dict(value))
                for label, value in section.items()
            )
        else:
            normalized: list[tuple[str, dict[str, Any]]] = []
            for entry in section:
                entry_dict = self._to_dict(entry)
                label = entry_dict.get("label") or getattr(entry, "label", None)
                if label is None:
                    continue
                normalized.append((label, entry_dict))
            items = normalized

        result: dict[str, dict[str, Any]] = {}
        for label, data in items:
            item = dict(data)
            item.setdefault("label", label)
            result[label] = item
        return result

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
        if model_fields:
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
    def _ensure_edge_class(cls: type[Any]) -> type[Edge]:
        try:
            if issubclass(cls, Edge):
                return cls
        except TypeError:  # pragma: no cover - defensive fallback
            from tangl.vm.frame import ChoiceEdge  # local import to avoid heavy dependency at module scope

            return ChoiceEdge

        if cls is Edge:
            from tangl.vm.frame import ChoiceEdge

            return ChoiceEdge

        return cls

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

    def _normalize_action_entry(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        if "trigger_phase" not in payload:
            phase = self._map_activation_to_phase(payload.get("activation") or payload.get("trigger"))
            if phase is not None:
                payload["trigger_phase"] = phase
        payload.pop("activation", None)
        return payload

    @staticmethod
    def _is_graph_item(cls: type[Any]) -> bool:
        try:
            return issubclass(cls, GraphItem)
        except TypeError:  # pragma: no cover - defensive fallback
            return False

    @staticmethod
    def _to_dict(data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            return dict(data)
        if isinstance(data, BaseModel):
            return data.model_dump()
        if hasattr(data, "model_dump"):
            return data.model_dump()  # pragma: no cover - protocol-style models
        if data is None:
            return {}
        return dict(data)
