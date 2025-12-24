from __future__ import annotations
import logging
import warnings
from collections.abc import Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from tangl.core.factory import TemplateFactory
from tangl.core.graph import Node
from tangl.core.graph.scope_selectable import ScopeSelector
from tangl.core.registry import Registry
from tangl.ir.core_ir import BaseScriptItem, MasterScript
from tangl.ir.story_ir import StoryScript
from tangl.ir.story_ir.actor_script_models import ActorScript
from tangl.ir.story_ir.location_script_models import LocationScript
from tangl.ir.story_ir.scene_script_models import BlockScript, SceneScript
from tangl.type_hints import StringMap, UnstructuredData

from tangl.story.concepts.actor import Actor
from tangl.story.concepts.location import Location
from tangl.story.episode import Scene

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# @dataclass(frozen=True, slots=True)
# class _DefaultClassConfig:
#     """Configuration describing default ``obj_cls`` wiring for script exports."""
#
#     class_path: str | None = None
#     alias: str | None = None
#     children: dict[str, "_DefaultClassConfig"] = field(default_factory=dict)

from tangl.core import Entity

class ScriptManager(Entity):
    """ScriptManager mediates between input files and the world/story creation."""

    master_script: Optional[MasterScript] = None  # for reference
    template_factory: TemplateFactory = TemplateFactory(label="templates")

    model_config = ConfigDict(extra="allow")

    # === CONSTRUCTORS ===

    @classmethod
    def from_master_script(cls, master_script: MasterScript) -> Self:
        factory = TemplateFactory.from_root_templ(master_script)

        manager = cls(
            master_script=master_script,
            template_factory=factory  # Store factory instead of registry
        )
        manager._register_scoped_templates()
        return manager

    @classmethod
    def from_script(cls, master_script: MasterScript) -> Self:
        return cls.from_master_script(master_script=master_script)

    @classmethod
    def from_data(cls, data: UnstructuredData) -> Self:
        try:
            ms: MasterScript = StoryScript(**data)
        except ValidationError:
            ms = MasterScript(**data)
        # todo: Want to call "on new script" here too.
        return cls.from_master_script(master_script=ms)

    @classmethod
    def from_files(cls, fp: Path) -> Self:
        # todo: implement a file reader
        data = {}
        return cls.from_data(data)

    # === METADATA ===

    def get_story_metadata(self) -> UnstructuredData:
        return self.master_script.metadata.model_dump()

    def get_story_globals(self) -> StringMap:
        if self.master_script.locals is not None:
            return deepcopy(self.master_script.locals)
        return {}

    # === FACTORY SEARCH ===

    # this is just a slightly different api for find-all with sort
    def find_template(
        self,
        identifier: str | None = None,
        selector: Node | None = None,
        **criteria: Any
    ) -> BaseScriptItem | None:
        """Return the first template matching identifier/criteria within scope."""
        if selector is not None:
            criteria.setdefault("selector", selector)

        if identifier is not None and isinstance(identifier, str) and "." in identifier:
            script_label = getattr(self.master_script, "label", None)
            path_candidates = []
            if script_label:
                path_candidates.append(f"{script_label}.{identifier}")
            path_candidates.append(identifier)
            for path_value in path_candidates:
                template = self.template_factory.find_one(
                    sort_key=lambda x: x.scope_specificity(),
                    path=path_value,
                    **criteria,
                )
                if template is not None:
                    return template

        if identifier is not None:
            criteria.setdefault("has_identifier", identifier)
        # anchored lookup is just sort by ancestry and then return first
        return self.template_factory.find_one(sort_key=lambda x: x.scope_specificity(), **criteria)

    def find_templates(
        self,
        *,
        identifier: str | None = None,
        selector: Node | None = None,
        **criteria: Any,
    ) -> list[BaseScriptItem]:
        """Return all templates matching identifier/criteria."""
        results: list[BaseScriptItem] = []
        if selector is not None:
            criteria.setdefault("selector", selector)

        if identifier is not None and isinstance(identifier, str) and "." in identifier:
            script_label = getattr(self.master_script, "label", None)
            path_candidates = []
            if script_label:
                path_candidates.append(f"{script_label}.{identifier}")
            path_candidates.append(identifier)
            seen: set[Any] = set()
            for path_value in path_candidates:
                for template in self.template_factory.find_all(
                    sort_key=lambda x: x.scope_specificity(),
                    path=path_value,
                    **criteria,
                ):
                    if template.uid in seen:
                        continue
                    seen.add(template.uid)
                    results.append(template)
            return results

        if identifier is not None:
            criteria.setdefault("has_identifier", identifier)
        return list(
            self.template_factory.find_all(
                sort_key=lambda x: x.scope_specificity(),
                **criteria,
            )
        )

    # This is similar api to how core.Graph wraps convenience accessors for
    # various sub-types of GraphItem
    def find_scenes(self, **criteria: Any) -> Iterator[SceneScript]:
        criteria.setdefault("is_instance", Scene)
        return iter(
            self.template_factory.find_all(
                sort_key=lambda x: x.scope_specificity(),
                **criteria,
            )
        )

    def find_actors(self, **criteria: Any) -> Iterator[ActorScript]:
        criteria.setdefault("is_instance", Actor)
        return self.find_templates(**criteria)

    def find_locations(self, **criteria: Any) -> Iterator[LocationScript]:
        criteria.setdefault("is_instance", Location)
        return self.find_templates(**criteria)

    def find_items(self, **criteria: Any) -> Iterator[BaseScriptItem]:
        """Return item templates if present (defaults to empty)."""
        return iter(())

    def find_flags(self, **criteria: Any) -> Iterator[BaseScriptItem]:
        """Return flag templates if present (defaults to empty)."""
        return iter(())

    # todo: find blocks, actions, roles, settings similarly if useful

    def _register_scoped_templates(self) -> None:
        script = self.master_script
        if script is None:
            return

        def _determine_template_cls(payload: Mapping[str, Any]) -> type[BaseScriptItem]:
            obj_cls = payload.get("obj_cls")
            if isinstance(obj_cls, type) and issubclass(obj_cls, BaseScriptItem):
                return obj_cls
            if isinstance(obj_cls, str):
                lowered = obj_cls.lower()
                if "location" in lowered:
                    return LocationScript
                if "actor" in lowered:
                    return ActorScript
            return BaseScriptItem

        def _add_templates(templates: Mapping[str, Any] | None, path_pattern: str | None) -> None:
            if not templates:
                return
            if not isinstance(templates, Mapping):
                logger.warning("Expected mapping for templates but received %r", type(templates))
                return
            for template_label, template_data in templates.items():
                label_value = template_label if isinstance(template_label, str) else str(template_label)
                if isinstance(template_data, BaseScriptItem):
                    updates = {}
                    if label_value and not template_data.label:
                        updates["label"] = label_value
                    if path_pattern and not getattr(template_data, "req_path_pattern", None):
                        updates["path_pattern"] = path_pattern
                    template = template_data.model_copy(update=updates) if updates else template_data
                elif isinstance(template_data, Mapping):
                    payload = dict(template_data)
                    payload.setdefault("label", label_value)
                    if path_pattern and "path_pattern" not in payload:
                        payload["path_pattern"] = path_pattern
                    template_cls = _determine_template_cls(payload)
                    try:
                        template = template_cls.model_validate(payload)
                    except ValidationError as exc:
                        logger.warning(
                            "Skipping template %s due to validation error: %s", label_value, exc
                        )
                        continue
                else:
                    logger.warning("Skipping template %s with unsupported payload %r", label_value, template_data)
                    continue
                try:
                    self.template_factory.add(template)
                except ValueError as exc:
                    logger.warning("Duplicate template %s skipped: %s", template.label, exc)

        world_templates = getattr(script, "templates", None)
        if isinstance(world_templates, Mapping):
            _add_templates(world_templates, path_pattern=None)
        elif world_templates:
            logger.warning("World templates should be a mapping; received %r", type(world_templates))

        scenes = getattr(script, "scenes", None)
        if isinstance(scenes, Mapping):
            scene_items = scenes.items()
        elif isinstance(scenes, list | tuple):
            scene_items = ((getattr(scene, "label", None), scene) for scene in scenes)
        else:
            scene_items = ()

        for scene_key, scene_obj in scene_items:
            scene_label = scene_key if isinstance(scene_key, str) else getattr(scene_obj, "label", None)
            if not scene_label:
                continue
            scene_templates = getattr(scene_obj, "templates", None)
            _add_templates(scene_templates, path_pattern=f"{scene_label}.*")

            blocks = getattr(scene_obj, "blocks", None)
            if isinstance(blocks, Mapping):
                block_items = blocks.items()
            elif isinstance(blocks, list | tuple):
                block_items = ((getattr(block, "label", None), block) for block in blocks)
            else:
                block_items = ()

            for block_key, block_obj in block_items:
                block_label = block_key if isinstance(block_key, str) else getattr(block_obj, "label", None)
                if not block_label:
                    continue
                block_templates = getattr(block_obj, "templates", None)
                _add_templates(block_templates, path_pattern=f"{scene_label}.*")

    @staticmethod
    def _is_qualified(identifier: str) -> bool:
        """Return ``True`` when identifier includes a scope separator."""

        return "." in identifier

    def _get_scope_chain(self, selector: Node) -> list[str]:
        """Return the selector's scope chain from most specific to global."""

        labels: list[str] = []
        current: Any | None = selector

        while current is not None:
            label = getattr(current, "label", None)
            if isinstance(label, str) and label:
                labels.append(label)
            current = getattr(current, "parent", None)

        labels.reverse()

        paths: list[str] = []
        for index in range(len(labels), 0, -1):
            path = ".".join(labels[:index])
            paths.append(path)

        paths.append("")

        return paths

    def _compile_templates(self) -> Registry:
        script = self.master_script
        registry = Registry(label=f"{script.label}_templates")

        def _extract_label(default: str | None, item: Any) -> str | None:
            if isinstance(item, BaseScriptItem):
                if item.label:
                    return item.label
                if default:
                    return default
                return item.get_label()
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
            if isinstance(raw_data, Mapping):
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
                label_value = template_label if isinstance(template_label, str) else str(template_label)
                template = _parse_template(label_value, template_data, scope)
                if template is None or template.label is None:
                    continue
                try:
                    registry.add(template)
                except ValueError as exc:  # pragma: no cover - Registry guards
                    logger.warning("Duplicate template %s skipped: %s", template.label, exc)

        world_templates = getattr(script, "templates", None)
        if isinstance(world_templates, Mapping):
            _add_templates(world_templates, scope=None)
        elif world_templates:
            logger.warning("World templates should be a mapping; received %r", type(world_templates))

        scenes = getattr(script, "scenes", None)
        if isinstance(scenes, Mapping):
            scene_items = scenes.items()
        elif isinstance(scenes, list | tuple):
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
                    "Scene %s templates should be a mapping; received %r", scene_label, type(scene_templates)
                )

            blocks = getattr(scene_obj, "blocks", None)
            if isinstance(blocks, Mapping):
                block_items = blocks.items()
            elif isinstance(blocks, list | tuple):
                block_items = ((getattr(block, "label", None), block) for block in blocks)
            else:
                block_items = ()

            for block_key, block_obj in block_items:
                block_label = _extract_label(block_key if isinstance(block_key, str) else None, block_obj)
                if block_label is None:
                    continue
                block_templates = getattr(block_obj, "templates", None)
                if isinstance(block_templates, Mapping):
                    _add_templates(block_templates, scope=ScopeSelector(parent_label=scene_label))
                elif block_templates:
                    logger.warning(
                        "Block %s templates should be a mapping; received %r", block_label, type(block_templates)
                    )

                try:
                    parsed_block = block_obj
                    if isinstance(block_obj, Mapping):
                        parsed_block = dict(block_obj)
                        if "block_cls" not in parsed_block and "obj_cls" in parsed_block:
                            parsed_block["block_cls"] = parsed_block.get("obj_cls")
                            parsed_block.pop("obj_cls", None)

                    block_script = BlockScript.model_validate(parsed_block)
                    updates: dict[str, Any] = {}
                    if not block_script.label and block_label:
                        updates["label"] = block_label
                    if block_script.obj_cls is None:
                        updates["obj_cls"] = "tangl.story.episode.block.Block"
                    if block_script.scope is None or block_script.scope.is_global():
                        updates["scope"] = ScopeSelector(parent_label=scene_label)
                    if updates:
                        block_script = block_script.model_copy(update=updates)
                    registry.add(block_script)
                except ValidationError as exc:
                    logger.warning("Skipping block %s due to validation error: %s", block_label, exc)

        return registry

    def get_unstructured(self, key: str) -> Iterator[UnstructuredData]:
        if not hasattr(self.master_script, key):
            return

        logger.debug("Starting node data %s", key)
        section = getattr(self.master_script, key)
        if not section:
            return

        config = getattr(self, "_default_tree", {}).get(key)

        if isinstance(section, dict):
            for label, item in section.items():
                payload = self._export_item(item, config)
                payload.setdefault("label", label)
                self._apply_defaults(key, payload)
                logger.debug(payload)
                yield payload
            return

        for item in section:
            payload = self._export_item(item, config)
            self._apply_defaults(key, payload)
            logger.debug(payload)
            yield payload


    @classmethod
    def _export_item(
        cls,
        item: Any,
        config: _DefaultClassConfig | None,
    ) -> dict[str, Any]:
        payload = cls._dump_item(item)
        if config is None:
            return payload
        return cls._apply_default_classes(payload, config)

    @staticmethod
    def _dump_item(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return dict(item)

        if hasattr(item, "model_dump"):
            rebuild = getattr(item.__class__, "model_rebuild", None)
            if callable(rebuild):
                rebuild()
            try:
                payload = item.model_dump(exclude_none=True, exclude_defaults=True)
            except TypeError:
                payload = dict(item.__dict__)

            return {key: value for key, value in payload.items() if value is not None}

        return dict(item)

    @staticmethod
    def _apply_defaults(key: str, payload: dict[str, Any]) -> None:
        if key == "actors":
            payload.setdefault("obj_cls", "tangl.story.concepts.actor.actor.Actor")
            return
        if key == "locations":
            payload.setdefault("obj_cls", "tangl.story.concepts.location.location.Location")
            return
        if key == "scenes":
            payload.setdefault("obj_cls", "tangl.story.episode.scene.Scene")
            blocks = payload.get("blocks")
            if isinstance(blocks, dict):
                for block_label, block in blocks.items():
                    if not isinstance(block, dict):
                        continue
                    block.setdefault("label", block_label)
                    block.setdefault("obj_cls", "tangl.story.episode.block.Block")
                    block.setdefault("block_cls", "tangl.story.episode.block.Block")
                    for edge_key in ("actions", "continues", "redirects"):
                        entries = block.get(edge_key)
                        if not isinstance(entries, list):
                            continue
                        for entry in entries:
                            if isinstance(entry, dict):
                                entry.setdefault(
                                    "obj_cls",
                                    "tangl.story.episode.action.Action",
                                )
    #
    # @classmethod
    # def _apply_default_classes(
    #     cls,
    #     data: dict[str, Any],
    #     config: _DefaultClassConfig,
    # ) -> dict[str, Any]:
    #     payload = dict(data)
    #
    #     class_path = config.class_path
    #     if class_path and not payload.get("obj_cls"):
    #         payload["obj_cls"] = class_path
    #     if config.alias and not payload.get(config.alias):
    #         payload[config.alias] = class_path
    #
    #     if not config.children:
    #         return payload
    #
    #     for field_name, child_config in config.children.items():
    #         value = payload.get(field_name)
    #         if not value:
    #             continue
    #
    #         if isinstance(value, dict):
    #             child_payload: dict[str, dict[str, Any]] = {}
    #             for child_label, child_value in value.items():
    #                 child_dict = cls._dump_item(child_value)
    #                 enriched = cls._apply_default_classes(child_dict, child_config)
    #                 enriched.setdefault("label", child_dict.get("label", child_label))
    #                 child_payload[child_label] = enriched
    #             payload[field_name] = child_payload
    #             continue
    #
    #         if isinstance(value, list):
    #             enriched_list = [
    #                 cls._apply_default_classes(cls._dump_item(child), child_config)
    #                 for child in value
    #             ]
    #             payload[field_name] = enriched_list
    #
    #     return payload

    # def get_story_text(self) -> list[tuple[str, str]]:
    #
    #     result = []
    #
    #     def _get_text_fields(path: str, item: list | dict):
    #         nonlocal result
    #         if not item:
    #             return
    #         if isinstance(item, list) and isinstance( item[0], dict ):
    #             [ _get_text_fields(path + f'.{i}', v) for i, v in enumerate(item) ]
    #         elif isinstance(item, dict):
    #             if 'text' in item:
    #                 data = {"path": path,
    #                         # "hash": key_for_secret(item['text'])[:6],
    #                         "text": item['text']}
    #                 result.append(data)
    #             [ _get_text_fields( path + f'.{k}', v) for k, v in item.items() ]
    #
    #     _get_text_fields(self.master_script.label, self.master_script.model_dump())
    #     return result
