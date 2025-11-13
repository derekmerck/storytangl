from __future__ import annotations

import logging
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ValidationError

from tangl.type_hints import StringMap, UnstructuredData
from tangl.ir.core_ir import MasterScript
from tangl.ir.story_ir import StoryScript

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

@dataclass(frozen=True, slots=True)
class _DefaultClassConfig:
    """Configuration describing default ``obj_cls`` wiring for script exports."""

    class_path: str | None = None
    alias: str | None = None
    children: dict[str, "_DefaultClassConfig"] = field(default_factory=dict)


class ScriptManager:
    """ScriptManager mediates between input files and the world/story creation."""

    master_script: MasterScript

    def __init__(self, master_script: MasterScript) -> None:
        self.master_script = master_script
        self._default_tree: dict[str, _DefaultClassConfig] = {
            "actors": _DefaultClassConfig(
                class_path="tangl.story.concepts.actor.actor.Actor",
            ),
            "locations": _DefaultClassConfig(
                class_path="tangl.story.concepts.location.location.Location",
            ),
            "items": _DefaultClassConfig(
                class_path="tangl.story.concepts.item.Item",
            ),
            "flags": _DefaultClassConfig(
                class_path="tangl.story.concepts.item.Flag",
            ),
            "scenes": _DefaultClassConfig(
                class_path="tangl.story.episode.scene.Scene",
                children={
                    "blocks": _DefaultClassConfig(
                        class_path="tangl.story.episode.block.Block",
                        alias="block_cls",
                        children={
                            key: _DefaultClassConfig(
                                class_path="tangl.story.episode.Action",
                            )
                            for key in ("actions", "continues", "redirects")
                        },
                    ),
                    "roles": _DefaultClassConfig(
                        class_path="tangl.story.concepts.actor.role.Role",
                    ),
                    "settings": _DefaultClassConfig(
                        class_path="tangl.story.concepts.location.setting.Setting",
                    ),
                },
            ),
        }

    @classmethod
    def from_data(cls, data: UnstructuredData) -> Self:
        try:
            ms: MasterScript = StoryScript(**data)
        except ValidationError:
            ms = MasterScript(**data)
        # todo: Want to call "on new script" here too.
        return cls(master_script=ms)

    @classmethod
    def from_files(cls, fp: Path) -> Self:
        # todo: implement a file reader
        data = {}
        return cls.from_data(data)

    def get_story_globals(self) -> StringMap:
        if self.master_script.locals:
            return deepcopy(self.master_script.locals)
        return {}

    def get_unstructured(self, key: str) -> Iterator[UnstructuredData]:
        if not hasattr(self.master_script, key):
            return

        logger.debug("Starting node data %s", key)
        section = getattr(self.master_script, key)
        if not section:
            return

        config = self._default_tree.get(key)

        if isinstance(section, dict):
            for label, item in section.items():
                payload = self._export_item(item, config)
                payload.setdefault("label", label)
                logger.debug(payload)
                yield payload
            return

        for item in section:
            payload = self._export_item(item, config)
            logger.debug(payload)
            yield payload

    def get_story_metadata(self) -> UnstructuredData:
        return self.master_script.metadata.model_dump()

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
        if isinstance(item, BaseModel):
            return item.model_dump()
        if hasattr(item, "model_dump"):
            return item.model_dump()  # pragma: no cover - duck-typed models
        return dict(item)

    @classmethod
    def _apply_default_classes(
        cls,
        data: dict[str, Any],
        config: _DefaultClassConfig,
    ) -> dict[str, Any]:
        payload = dict(data)

        class_path = config.class_path
        if class_path and not payload.get("obj_cls"):
            payload["obj_cls"] = class_path
        if config.alias and not payload.get(config.alias):
            payload[config.alias] = class_path

        if not config.children:
            return payload

        for field_name, child_config in config.children.items():
            value = payload.get(field_name)
            if not value:
                continue

            if isinstance(value, dict):
                child_payload: dict[str, dict[str, Any]] = {}
                for child_label, child_value in value.items():
                    child_dict = cls._dump_item(child_value)
                    enriched = cls._apply_default_classes(child_dict, child_config)
                    enriched.setdefault("label", child_dict.get("label", child_label))
                    child_payload[child_label] = enriched
                payload[field_name] = child_payload
                continue

            if isinstance(value, list):
                enriched_list = [
                    cls._apply_default_classes(cls._dump_item(child), child_config)
                    for child in value
                ]
                payload[field_name] = enriched_list

        return payload

    def get_story_text(self) -> list[tuple[str, str]]:

        result = []

        def _get_text_fields(path: str, item: list | dict):
            nonlocal result
            if not item:
                return
            if isinstance(item, list) and isinstance( item[0], dict ):
                [ _get_text_fields(path + f'.{i}', v) for i, v in enumerate(item) ]
            elif isinstance(item, dict):
                if 'text' in item:
                    data = {"path": path,
                            # "hash": key_for_secret(item['text'])[:6],
                            "text": item['text']}
                    result.append(data)
                [ _get_text_fields( path + f'.{k}', v) for k, v in item.items() ]

        _get_text_fields(self.master_script.label, self.master_script.model_dump())
        return result
