"""Legacy importer for scene/block script structures."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel

from tangl.ir.story_ir.scene_script_models import BlockScript, SceneScript


class SceneBlockImporter:
    """Convert legacy scene/block script payloads into addressable templates."""

    def convert_scenes_to_templates(
        self,
        scenes_dict: Mapping[str, Any],
    ) -> list[SceneScript]:
        """Convert scene data into templates with hierarchical addresses."""

        templates: list[SceneScript] = []
        for scene_label, scene_data in scenes_dict.items():
            scene_payload = self._normalize_payload(scene_label, scene_data)
            blocks_data = scene_payload.get("blocks", {})
            scene_payload["blocks"] = self._normalize_blocks(blocks_data)
            scene_payload.setdefault("declares_instance", True)
            scene_template = SceneScript.model_validate(scene_payload)
            templates.append(scene_template)
        return templates

    def _normalize_blocks(self, blocks_data: Any) -> dict[str, BlockScript]:
        normalized: dict[str, BlockScript] = {}
        for block_label, block_data in self._iter_labeled_items(blocks_data):
            payload = self._normalize_payload(block_label, block_data)
            payload.setdefault("declares_instance", True)
            normalized[block_label] = BlockScript.model_validate(payload)
        return normalized

    def _normalize_payload(self, label: str, data: Any) -> dict[str, Any]:
        payload = self._to_dict(data)
        payload.setdefault("label", label)
        return payload

    def _iter_labeled_items(self, data: Any) -> Iterable[tuple[str, Any]]:
        if not data:
            return []
        if isinstance(data, Mapping):
            return list(data.items())
        items: list[tuple[str, Any]] = []
        for entry in data:
            payload = self._to_dict(entry)
            label = payload.get("label")
            if not label:
                raise ValueError("Legacy block entries must provide a label.")
            items.append((label, entry))
        return items

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
