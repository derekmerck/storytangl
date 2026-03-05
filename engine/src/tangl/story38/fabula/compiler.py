from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from tangl.core38 import Entity, EntityTemplate, Selector, TemplateRegistry
from tangl.core38.template import TemplateGroup
from tangl.ir.story_ir import StoryScript
from tangl.vm38 import TraversableNode

from ..concepts import Actor, Location
from ..episode import Action, Block, Scene


@dataclass(slots=True)
class StoryTemplateBundle:
    """Canonical story38 compile artifact."""

    metadata: dict[str, Any]
    locals: dict[str, Any]
    template_registry: TemplateRegistry
    entry_template_ids: list[str]
    source_map: dict[str, Any]
    codec_state: dict[str, Any]
    codec_id: str | None


class StoryCompiler38:
    """Compile story script data into a core38 TemplateRegistry bundle."""

    def compile(
        self,
        script_data: dict[str, Any] | StoryScript,
        *,
        source_map: dict[str, Any] | None = None,
        codec_state: dict[str, Any] | None = None,
        codec_id: str | None = None,
    ) -> StoryTemplateBundle:
        script = script_data if isinstance(script_data, StoryScript) else StoryScript.model_validate(script_data)
        data = script.model_dump(by_alias=True, exclude_none=True)

        metadata = dict(data.get("metadata") or {})
        locals_ns = dict(data.get("globals") or {})

        registry = TemplateRegistry(label=f"{script.label}_templates")
        root = TemplateGroup(
            label=script.label,
            payload=Entity(label=script.label),
            registry=registry,
        )

        self._compile_section(
            parent=root,
            items=data.get("templates"),
            fallback_kind=TraversableNode,
        )
        self._compile_section(
            parent=root,
            items=data.get("actors"),
            fallback_kind=Actor,
        )
        self._compile_section(
            parent=root,
            items=data.get("locations"),
            fallback_kind=Location,
        )

        scenes = self._normalize_mapping(data.get("scenes"))
        self._validate_unique_root_scene_labels(scenes)
        root_scene_labels = {scene_label for scene_label, _ in scenes}
        for scene_label, scene_data in scenes:
            scene_payload = self._build_payload(
                kind=self._resolve_kind(scene_data.get("obj_cls"), fallback=Scene),
                payload={
                    **scene_data,
                    "label": scene_data.get("label") or scene_label,
                    "title": scene_data.get("title") or scene_data.get("text") or "",
                    "roles": self._normalize_list(scene_data.get("roles")),
                    "settings": self._normalize_list(scene_data.get("settings")),
                },
                default_label=scene_label,
            )
            scene_templ = TemplateGroup(
                label=scene_label,
                payload=scene_payload,
                registry=registry,
            )
            root.add_child(scene_templ)

            blocks = self._normalize_mapping(scene_data.get("blocks"))
            for block_label, block_data in blocks:
                qualified_label = f"{scene_label}.{block_label}"
                actions = self._canonicalize_action_specs(
                    self._normalize_list(block_data.get("actions")),
                    scene_label=scene_label,
                    root_scene_labels=root_scene_labels,
                )
                continues = self._canonicalize_action_specs(
                    self._normalize_list(block_data.get("continues")),
                    scene_label=scene_label,
                    root_scene_labels=root_scene_labels,
                )
                redirects = self._canonicalize_action_specs(
                    self._normalize_list(block_data.get("redirects")),
                    scene_label=scene_label,
                    root_scene_labels=root_scene_labels,
                )
                block_payload = self._build_payload(
                    kind=self._resolve_kind(
                        block_data.get("obj_cls") or block_data.get("block_cls"),
                        fallback=Block,
                    ),
                    payload={
                        **block_data,
                        "label": block_data.get("label") or block_label,
                        "actions": actions,
                        "continues": continues,
                        "redirects": redirects,
                        "roles": self._normalize_list(block_data.get("roles")),
                        "settings": self._normalize_list(block_data.get("settings")),
                        "media": self._normalize_list(block_data.get("media")),
                    },
                    default_label=block_label,
                )
                block_templ = TemplateGroup(
                    label=qualified_label,
                    payload=block_payload,
                    registry=registry,
                )
                scene_templ.add_child(block_templ)

                self._compile_section(
                    parent=block_templ,
                    items=block_data.get("templates"),
                    fallback_kind=TraversableNode,
                )

        entry_template_ids = self._resolve_entry_template_ids(metadata=metadata, registry=registry)

        return StoryTemplateBundle(
            metadata=metadata,
            locals=locals_ns,
            template_registry=registry,
            entry_template_ids=entry_template_ids,
            source_map=source_map or {},
            codec_state=codec_state or {},
            codec_id=codec_id,
        )

    def _compile_section(
        self,
        *,
        parent: TemplateGroup,
        items: Any,
        fallback_kind: type[Entity],
    ) -> None:
        for label, item_data in self._normalize_mapping(items):
            parent_label = parent.get_label()
            scoped_label = (
                label
                if getattr(parent, "parent", None) is None
                else f"{parent_label}.{label}"
            )
            payload = self._build_payload(
                kind=self._resolve_kind(item_data.get("obj_cls"), fallback=fallback_kind),
                payload={**item_data, "label": item_data.get("label") or label},
                default_label=label,
            )
            templ = TemplateGroup(
                label=scoped_label,
                payload=payload,
                registry=parent.registry,
            )
            parent.add_child(templ)
            self._compile_section(
                parent=templ,
                items=item_data.get("templates"),
                fallback_kind=fallback_kind,
            )

    @staticmethod
    def _normalize_mapping(value: Any) -> list[tuple[str, dict[str, Any]]]:
        if not value:
            return []
        if isinstance(value, dict):
            items: list[tuple[str, dict[str, Any]]] = []
            for label, data in value.items():
                if isinstance(data, dict):
                    payload = dict(data)
                else:
                    payload = dict(getattr(data, "model_dump", lambda **_: {})())
                payload.setdefault("label", label)
                items.append((str(label), payload))
            return items
        items = []
        for item in value:
            if isinstance(item, dict):
                payload = dict(item)
            else:
                payload = dict(getattr(item, "model_dump", lambda **_: {})())
            label = payload.get("label") or "item"
            items.append((str(label), payload))
        return items

    @staticmethod
    def _normalize_list(value: Any) -> list[dict[str, Any]]:
        if not value:
            return []
        if isinstance(value, dict):
            out: list[dict[str, Any]] = []
            for label, data in value.items():
                if isinstance(data, dict):
                    payload = dict(data)
                else:
                    payload = dict(getattr(data, "model_dump", lambda **_: {})())
                payload.setdefault("label", label)
                out.append(payload)
            return out
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append(dict(item))
            else:
                out.append(dict(getattr(item, "model_dump", lambda **_: {})()))
        return out

    @staticmethod
    def _canonicalize_action_specs(
        specs: list[dict[str, Any]],
        *,
        scene_label: str,
        root_scene_labels: set[str],
    ) -> list[dict[str, Any]]:
        """Return canonical action specs for one scene.

        Part A policy: when a bare successor token collides with a root scene
        label, it is treated as an absolute scene destination by design.
        """
        normalized: list[dict[str, Any]] = []
        for spec in specs:
            payload = dict(spec)
            authored = payload.get("authored_successor_ref")
            if not (isinstance(authored, str) and authored):
                authored = payload.get("successor_ref")
                if authored is None:
                    authored = (
                        payload.get("successor")
                        or payload.get("target_ref")
                        or payload.get("target_node")
                    )
                if isinstance(authored, str) and authored:
                    payload["authored_successor_ref"] = authored

            canonical = payload.get("successor_ref")
            if not (isinstance(canonical, str) and canonical):
                canonical = authored
            if isinstance(canonical, str) and canonical:
                if "." in canonical:
                    payload["successor_ref"] = canonical
                    payload["successor_is_absolute"] = False
                elif canonical in root_scene_labels:
                    payload["successor_ref"] = canonical
                    payload["successor_is_absolute"] = True
                else:
                    payload["successor_ref"] = f"{scene_label}.{canonical}"
                    payload["successor_is_absolute"] = False
            normalized.append(payload)
        return normalized

    @staticmethod
    def _validate_unique_root_scene_labels(scenes: list[tuple[str, dict[str, Any]]]) -> None:
        labels = [label for label, _ in scenes]
        duplicates = sorted(
            label
            for label, count in Counter(labels).items()
            if count > 1
        )
        if duplicates:
            joined = ", ".join(duplicates)
            raise ValueError(f"Duplicate root scene labels declared: {joined}")

    @staticmethod
    def _resolve_entry_template_ids(
        *,
        metadata: dict[str, Any],
        registry: TemplateRegistry,
    ) -> list[str]:
        start_at = metadata.get("start_at")
        if isinstance(start_at, str) and start_at:
            return [start_at]
        if isinstance(start_at, list):
            values = [str(v) for v in start_at if str(v)]
            if values:
                return values

        first_block = registry.find_one(Selector(has_payload_kind=Block))
        if first_block is not None:
            return [first_block.get_label()]

        return []

    def _resolve_kind(self, raw_obj_cls: Any, *, fallback: type[Entity]) -> type[Entity]:
        if isinstance(raw_obj_cls, type):
            return self._map_external_kind(raw_obj_cls.__name__, fallback=fallback)

        if isinstance(raw_obj_cls, str):
            mapped = self._map_external_kind(raw_obj_cls.split(".")[-1], fallback=fallback)
            if mapped is not fallback:
                return mapped
            try:
                module_name, class_name = raw_obj_cls.rsplit(".", 1)
                cls = getattr(import_module(module_name), class_name)
                if isinstance(cls, type):
                    return self._map_external_kind(cls.__name__, fallback=fallback)
            except Exception:
                return fallback

        return fallback

    @staticmethod
    def _map_external_kind(kind_name: str, *, fallback: type[Entity]) -> type[Entity]:
        mapping: dict[str, type[Entity]] = {
            "Actor": Actor,
            "Location": Location,
            "Role": Actor,
            "Setting": Location,
            "Scene": Scene,
            "Block": Block,
            "MenuBlock": Block,
            "Action": Action,
            "Node": TraversableNode,
            "TraversableNode": TraversableNode,
        }
        return mapping.get(kind_name, fallback)

    @staticmethod
    def _build_payload(kind: type[Entity], payload: dict[str, Any], default_label: str) -> Entity:
        payload = dict(payload)

        if isinstance(payload.get("effects"), list):
            normalized_effects: list[dict[str, Any]] = []
            for effect in payload["effects"]:
                if isinstance(effect, str):
                    normalized_effects.append({"expr": effect})
                elif isinstance(effect, dict):
                    normalized_effects.append(dict(effect))
            payload["effects"] = normalized_effects

        if kind is Action:
            if payload.get("successor_ref") is None:
                mapped_ref = payload.get("successor") or payload.get("target_ref") or payload.get("target_node")
                if mapped_ref is not None:
                    payload["successor_ref"] = mapped_ref

        allowed = set(getattr(kind, "model_fields", {}).keys())
        filtered = {k: v for k, v in payload.items() if k in allowed}
        filtered.setdefault("label", payload.get("label") or default_label)

        try:
            return kind(**filtered)
        except Exception:
            fallback = TraversableNode(label=filtered.get("label", default_label))
            if "locals" in payload and isinstance(payload["locals"], dict):
                fallback.locals.update(payload["locals"])
            return fallback
