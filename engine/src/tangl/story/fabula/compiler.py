from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from tangl.core import Entity, EntityTemplate, Selector, TemplateRegistry
from tangl.core.template import TemplateGroup
from tangl.ir.story_ir import StoryScript
from tangl.vm import TraversableNode

from ..concepts import Actor, Location
from ..episode import Action, Block, MenuBlock, Scene


@dataclass(slots=True)
class StoryTemplateBundle:
    """StoryTemplateBundle()

    Canonical output of :class:`StoryCompiler`.

    Why
    ----
    Separating compilation from materialization lets one validated script bundle
    produce many independent story graphs without reparsing authored input.

    Key Features
    ------------
    * Carries the validated :class:`~tangl.core.TemplateRegistry` tree used by
      the materializer.
    * Preserves ``metadata``, story ``locals``, source mapping, and codec state
      alongside the template hierarchy.
    * Records ``entry_template_ids`` so materialization can resolve the graph's
      initial cursor positions deterministically.

    API
    ---
    - :attr:`metadata` stores story-level metadata used by runtime setup.
    - :attr:`locals` stores authored top-level namespace values.
    - :attr:`template_registry` contains the validated template hierarchy.
    - :attr:`entry_template_ids` lists the template ids used for initial cursor
      resolution.
    - :attr:`source_map`, :attr:`codec_state`, and :attr:`codec_id` preserve
      compile-time provenance and codec context.
    """

    metadata: dict[str, Any]
    locals: dict[str, Any]
    template_registry: TemplateRegistry
    entry_template_ids: list[str]
    source_map: dict[str, Any]
    codec_state: dict[str, Any]
    codec_id: str | None


class StoryCompiler:
    """StoryCompiler()

    Validate and normalize authored story script data into a
    :class:`StoryTemplateBundle`.

    Why
    ----
    Authored story scripts are intentionally lightweight. The compiler turns
    that loose authoring shape into a typed, scoped template tree that runtime
    materialization and provisioning can trust.

    Key Features
    ------------
    * Accepts raw dicts or validated :class:`~tangl.ir.story_ir.StoryScript`
      instances.
    * Builds scene and block template hierarchy used by runtime scope matching.
    * Canonicalizes action references so authored shorthand and qualified
      references resolve into a stable form.
    * Attempts to resolve authored ``kind`` references during compilation when
      an override cannot be imported.

    API
    ---
    - :meth:`compile` is the supported public entry point.
    """

    @staticmethod
    def validate_ir(script_data: dict[str, Any]) -> StoryScript:
        """Validate raw script data against the near-native IR schema.

        Use this when authored near-native YAML should be linted explicitly.
        Compilation itself accepts runtime-ready dicts directly so codecs are
        not forced through the at-rest IR model.
        """
        return StoryScript.model_validate(script_data)

    def compile(
        self,
        script_data: dict[str, Any] | StoryScript,
        *,
        source_map: dict[str, Any] | None = None,
        codec_state: dict[str, Any] | None = None,
        codec_id: str | None = None,
    ) -> StoryTemplateBundle:
        """Compile authored story data into a reusable template bundle.

        Accepts raw script dictionaries or validated
        :class:`~tangl.ir.story_ir.StoryScript` objects.

        Raw dicts are compiled directly. Use :meth:`validate_ir` separately
        when authored near-native data should be linted against the IR schema.
        """
        if isinstance(script_data, StoryScript):
            data = script_data.model_dump(by_alias=True, exclude_none=True)
            label = script_data.label
        else:
            data = dict(script_data)
            label = str(data.get("label") or "story")

        metadata = dict(data.get("metadata") or {})
        locals_ns = dict(data.get("globals") or data.get("locals") or {})

        registry = TemplateRegistry(label=f"{label}_templates")
        root = TemplateGroup(
            label=label,
            payload=Entity(label=label),
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
                kind=self._resolve_kind(
                    scene_data.get("kind"),
                    fallback=Scene,
                ),
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

            self._compile_section(
                parent=scene_templ,
                items=scene_data.get("templates"),
                fallback_kind=TraversableNode,
            )

            blocks = self._normalize_mapping(scene_data.get("blocks"))
            for block_index, (block_label, block_data) in enumerate(blocks):
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
                next_qualified = self._next_block_label(blocks, block_index, scene_label)
                for spec_list in (actions, continues, redirects):
                    for spec in spec_list:
                        if not spec.get("successor_ref") and next_qualified is not None:
                            spec["successor_ref"] = next_qualified
                            spec["successor_is_absolute"] = False
                            spec["successor_is_inferred"] = True

                block_payload = self._build_payload(
                    kind=self._resolve_kind(
                        block_data.get("kind")
                        or block_data.get("block_cls"),
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
                kind=self._resolve_kind(
                    item_data.get("kind"),
                    fallback=fallback_kind,
                ),
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
        anon_counter = 0
        for item in value:
            if isinstance(item, dict):
                payload = dict(item)
            else:
                payload = dict(getattr(item, "model_dump", lambda **_: {})())
            label = payload.get("label")
            if not label:
                label = f"_anon_{anon_counter}"
                anon_counter += 1
                payload["label"] = label
                payload["_is_anonymous"] = True
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
                        or payload.get("next")
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
        """Resolve compile-time entry template ids using authored priority rules."""
        start_at = metadata.get("start_at")
        if isinstance(start_at, str) and start_at:
            return [start_at]
        if isinstance(start_at, list):
            values = [str(v) for v in start_at if str(v)]
            if values:
                return values

        block_templates = [
            template
            for template in registry.values()
            if hasattr(template, "has_payload_kind") and template.has_payload_kind(Block)
        ]

        for tag_name in ("start", "entry"):
            for template in block_templates:
                if template.has_tags({tag_name}):
                    return [template.get_label()]

        for template in block_templates:
            payload = getattr(template, "payload", None)
            if payload is None:
                continue
            block_locals = getattr(payload, "locals", None) or {}
            if isinstance(block_locals, dict) and (
                block_locals.get("is_start") or block_locals.get("start_at")
            ):
                return [template.get_label()]

        for template in block_templates:
            label = template.get_label()
            short_label = label.rsplit(".", 1)[-1] if "." in label else label
            if short_label.lower() == "start":
                return [label]

        first_block = registry.find_one(Selector(has_payload_kind=Block))
        if first_block is not None:
            return [first_block.get_label()]

        return []

    @staticmethod
    def _next_block_label(
        blocks: list[tuple[str, dict[str, Any]]],
        current_index: int,
        scene_label: str,
    ) -> str | None:
        next_index = current_index + 1
        if next_index >= len(blocks):
            return None
        return f"{scene_label}.{blocks[next_index][0]}"

    def _resolve_kind(self, raw_kind: Any, *, fallback: type[Entity]) -> type[Entity]:
        if isinstance(raw_kind, type):
            return self._map_external_kind(raw_kind.__name__, fallback=fallback)

        if isinstance(raw_kind, str):
            mapped = self._map_external_kind(raw_kind.split(".")[-1], fallback=fallback)
            if mapped is not fallback:
                return mapped
            try:
                module_name, class_name = raw_kind.rsplit(".", 1)
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
            "MenuBlock": MenuBlock,
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
                mapped_ref = (
                    payload.get("successor")
                    or payload.get("next")
                    or payload.get("target_ref")
                    or payload.get("target_node")
                )
                if mapped_ref is not None:
                    payload["successor_ref"] = mapped_ref
            if not payload.get("text") and payload.get("content"):
                payload["text"] = payload.get("content")

        if issubclass(kind, Block) and payload.get("_is_anonymous"):
            payload["is_anonymous"] = True

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
