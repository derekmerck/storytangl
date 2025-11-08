"""World singleton coordinating managers for story construction."""

from __future__ import annotations
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tangl.core.graph.edge import Edge
from tangl.core.graph.graph import Graph, GraphItem
from tangl.core.singleton import Singleton

# Integrated Story Domains
from .domain_manager import DomainManager  # behaviors and classes
from .script_manager import ScriptManager  # concept templates
from .asset_manager import AssetManager    # platonic objects

# from tangl.discourse.voice_manager import VoiceManager   # narrative and character styles

if TYPE_CHECKING:  # pragma: no cover - hinting only
    from tangl.media.media_resource.resource_manager import ResourceManager

    StoryGraph = Graph
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

        self._setup_default_assets()

    def _create_resource_manager(self) -> "ResourceManager | None":
        try:
            from tangl.media.media_resource.resource_manager import ResourceManager as RM
        except ModuleNotFoundError:  # pragma: no cover - optional dependency gap
            return None
        return RM(Path("."))

    def _setup_default_assets(self) -> None:
        """Register built-in asset classes if not already present."""
        if "countable" in self.asset_manager.asset_classes:
            return
        try:
            from tangl.story.concepts.asset import CountableAsset
        except ModuleNotFoundError:  # pragma: no cover - optional dependency gap
            return
        self.asset_manager.register_asset_class("countable", CountableAsset)

    def create_story(self, story_label: str, mode: str = "full") -> StoryGraph:
        """Create a new story instance from the world script."""
        if mode == "full":
            return self._create_story_full(story_label)
        raise NotImplementedError(f"Mode {mode} not yet implemented")

    def _create_story_full(self, story_label: str) -> StoryGraph:
        """Materialize a fully-instantiated :class:`StoryGraph`."""
        graph = StoryGraph(label=story_label)

        node_map: dict[str, UUID] = {}

        node_map.update(self._build_actors(graph))
        node_map.update(self._build_locations(graph))

        block_map, action_scripts = self._build_blocks(graph)
        node_map.update(block_map)

        scene_map = self._build_scenes(graph, block_map)
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
                qualified_label = f"{scene_label}.{block_label}"
                cls = self.domain_manager.resolve_class(
                    block_data.get("obj_cls") or block_data.get("block_cls")
                )

                scripts = {
                    key: [
                        self._normalize_action_entry(self._to_dict(entry))
                        for entry in block_data.get(key, [])
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

        return node_map, action_scripts

    def _build_scenes(
        self,
        graph: StoryGraph,
        block_map: dict[str, UUID],
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

        return scene_map

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
            if self._is_graph_item(cls):
                allowed.add("graph")
            payload = {key: value for key, value in payload.items() if key in allowed}
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
