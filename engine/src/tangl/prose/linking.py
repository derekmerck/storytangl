"""Conservative, opt-in near-native source lowering into ordered prose values.

This is a source frontend, not a persistence serializer. World domains adopt
it through ``get_story_codecs``; graph restoration uses ordinary constructor form.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

from tangl.core import EntityTemplate, Selector, TemplateRegistry
from tangl.loaders.bundle import WorldBundle
from tangl.loaders.codec import DecodeResult, NearNativeYamlCodec
from tangl.story import Actor, Block, Location, Scene
from tangl.story.fabula import StoryCompiler

from .dialog import DialogHandler
from .naming import (
    BindingReference, ConceptReference, HasNaming, NamingActor, NamingLocation,
    ProseBlock, ReferenceIntent,
)


def _items(
    value: dict[str, dict[str, Any]] | list[dict[str, Any]] | None,
) -> list[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        return list(value.items())
    return [(item["label"], item) for item in value or []]


def _catalog(
    templates: TemplateRegistry, scopes: list[str], overrides: dict[str, dict[str, str]],
) -> dict[str, list[ConceptReference]]:
    """Only scope declarations are eligible; prototypes supply spellings, not links."""
    bindings: dict[
        tuple[str, str], tuple[BindingReference, dict[str, Any], EntityTemplate],
    ] = {}
    for scope in scopes:
        owner = templates.find_one(Selector(label=scope))
        owner_path = owner.payload.label
        if isinstance(owner.payload, Block):
            owner_path = f"{owner.parent.payload.label}.{owner_path}"
        for collection, specs in (
            ("role_edges", owner.payload.roles),
            ("setting_edges", owner.payload.settings),
        ):
            labels: set[str] = set()
            for spec in specs or []:
                label = spec["label"]
                if label in labels:
                    raise ValueError(f"{scope}: duplicate {collection} declaration {label!r}")
                labels.add(label)
                bindings[collection, label] = (
                    BindingReference(scope=owner_path, label=label, collection=collection),
                    spec,
                    owner,
                )
    missing = set(overrides) - {binding.label for binding, _, _ in bindings.values()}
    if missing:
        raise ValueError(f"{scopes[-1]}: unavailable link_forms bindings {sorted(missing)}")
    forms: dict[str, list[ConceptReference]] = {}
    for binding, spec, owner in bindings.values():
        prototype = None
        provider_ref = (
            spec.get("actor_ref") or spec.get("actor_template_ref")
            or spec.get("location_ref") or spec.get("location_template_ref")
        )
        if provider_ref:
            current = owner
            while current is not None and prototype is None:
                prefix = current.label if isinstance(current.payload, (Scene, Block)) else ""
                qualified = f"{prefix}.{provider_ref}" if prefix else provider_ref
                prototype = templates.find_one(Selector(label=qualified))
                current = current.parent
        explicit = overrides.get(binding.label, {})
        proper = explicit.get("proper")
        nominal = explicit.get("anonymous")
        if prototype is not None and isinstance(prototype.payload, (Actor, Location)):
            proper = proper or prototype.payload.name
            if isinstance(prototype.payload, HasNaming):
                nominal = nominal or prototype.payload.anonymous_name
        adopted = [(binding.label, ReferenceIntent.AUTO, False)]
        if proper:
            adopted.append((proper, ReferenceIntent.AUTO, False))
        if nominal:
            adopted.append((nominal, ReferenceIntent.ANONYMOUS, False))
            capitalized = nominal[:1].upper() + nominal[1:]
            if capitalized != nominal:
                adopted.append((capitalized, ReferenceIntent.ANONYMOUS, True))
        for spelling, intent, capitalize in adopted:
            reference = ConceptReference(ref=binding, intent=intent, capitalize=capitalize)
            bucket = forms.setdefault(spelling, [])
            if reference not in bucket:
                bucket.append(reference)
    return forms


def link_text(
    text: str, forms: dict[str, list[ConceptReference]], *, source: str,
) -> list[str | ConceptReference]:
    """Exact boundaries and longest match; a backslash escapes one adopted form."""
    if not forms:
        if "#intro" in text:
            raise ValueError(f"{source}: introduction has no eligible binding")
        return [text]
    spellings = sorted(forms, key=lambda value: (-len(value), value))
    pattern = re.compile(r"(?<!\w)(?P<escape>\\)?(?P<form>" + "|".join(
        re.escape(value) for value in spellings
    ) + r")(?!\w)(?P<intro>[ \t]*#intro\b)?")
    parts: list[str | ConceptReference] = []
    offset = 0
    for match in pattern.finditer(text):
        literal = text[offset:match.start()]
        if "#intro" in literal:
            raise ValueError(f"{source}:{offset}: unmatched #intro; eligible={spellings}")
        parts.append(literal)
        if match["escape"]:
            parts.append(match["form"] + (match["intro"] or ""))
        else:
            candidates = forms[match["form"]]
            if len(candidates) != 1:
                eligible = [f"{ref.ref.scope}:{ref.ref.label}" for ref in candidates]
                raise ValueError(
                    f"{source}:{match.start()}: ambiguous {match['form']!r}; eligible={eligible}"
                )
            parts.append(candidates[0].model_copy(update={"introduce": bool(match["intro"])}))
        offset = match.end()
    tail = text[offset:]
    parts.append(tail)
    if "#intro" in tail:
        raise ValueError(f"{source}: unmatched #intro; eligible={spellings}")
    return parts


def lower_linked_prose(
    story_data: dict[str, Any], *, source: str = "script",
    class_registry: dict[str, type] | None = None,
) -> dict[str, Any]:
    """Pure source transform: compile a declaration catalog without materializing a graph."""
    data = deepcopy(story_data)
    world_enabled = data.pop("link_prose", False)
    world_forms = data.pop("link_forms", {})
    plans: list[tuple[str, dict[str, Any], bool, dict[str, dict[str, str]]]] = []
    for scene_label, scene in _items(data.get("scenes")):
        enabled = scene.pop("link_prose", world_enabled)
        forms = world_forms | scene.pop("link_forms", {})
        for block_label, block in _items(scene.get("blocks")):
            plans.append((
                f"{scene_label}.{block_label}", block,
                block.pop("link_prose", enabled), forms | block.pop("link_forms", {}),
            ))
    if not any(enabled or "prose" in block for _, block, enabled, _ in plans):
        return data
    # The catalog compiler sees only canonical payloads. Source strings in prose
    # segments are lowered below; they are not ProseSegment model values yet.
    catalog_data = deepcopy(data)
    for _, scene in _items(catalog_data.get("scenes")):
        for _, block in _items(scene.get("blocks")):
            block.pop("prose", None)
    registry = {
        "NamingActor": NamingActor, "NamingLocation": NamingLocation, "ProseBlock": ProseBlock,
    } | (class_registry or {})
    templates = StoryCompiler().compile(catalog_data, class_registry=registry).template_registry
    for scope, block, enabled, overrides in plans:
        if not enabled and "prose" not in block:
            continue
        try:
            forms = (
                _catalog(templates, [scope.rsplit(".", 1)[0], scope], overrides)
                if enabled else {}
            )
        except ValueError as exc:
            raise ValueError(f"{source}:{exc}") from exc
        if "content" in block and "prose" in block:
            raise ValueError(f"{source}:{scope}: choose content or ordered prose, not both")
        segments = block.pop("prose", None)
        if segments is None:
            content = block.get("content", "")
            # Ordinary whole-block Jinja retains the existing late-binding path.
            # Only explicit template segments can be interleaved with linked text.
            if any(marker in content for marker in ("{{", "{%", "{#")):
                continue
            if DialogHandler.has_mu_blocks(content):
                raise ValueError(
                    f"{source}:{scope}: use explicit speaker segments for linked dialog"
                )
            block.pop("content", None)
            segments = [{"text": content}]
        lowered = []
        for index, segment in enumerate(segments):
            segment = dict(segment)
            raw = segment.pop("raw", False)
            location = f"{source}:{scope}.prose[{index}]"
            speaker = segment.get("speaker")
            if enabled and speaker is not None:
                candidates = forms.get(speaker, [])
                if len(candidates) != 1:
                    raise ValueError(
                        f"{location}: unavailable/ambiguous speaker {speaker!r}; "
                        f"eligible={list(forms)}"
                    )
                segment["speaker"] = candidates[0].ref.model_dump(mode="json")
            if "template" in segment:
                lowered.append(segment)
                continue
            text = segment.get("text", "")
            if not enabled and isinstance(text, list):
                lowered.append(segment)
                continue
            if not isinstance(text, str):
                raise ValueError(
                    f"{location}: lexical text must be a string; use explicit ProseBlock otherwise"
                )
            if enabled and not raw and speaker is None and any(
                marker in text for marker in ("{{", "{%", "{#")
            ):
                raise ValueError(f"{location}: use an explicit template segment for Jinja")
            parts = (
                [text] if not enabled or raw or speaker is not None
                else link_text(text, forms, source=location)
            )
            # These are source value DTOs, not persisted graph entities.
            segment["text"] = [
                part if isinstance(part, str) else part.model_dump(mode="json")
                for part in parts
            ]
            lowered.append(segment)
        prototype = templates.find_one(Selector(label=scope)).payload
        if type(prototype) is Block:
            block["kind"] = "tangl.prose.naming.ProseBlock"
        elif not isinstance(prototype, ProseBlock):
            raise ValueError(f"{source}:{scope}: custom block kind must inherit ProseBlock")
        block["prose"] = lowered
    return data


class LinkedProseYamlCodec(NearNativeYamlCodec):
    """World-local exact linker, adopted separately from naming policy."""

    codec_id = "linked_prose_yaml"

    def __init__(self, class_registry: dict[str, type] | None = None) -> None:
        self.class_registry = class_registry

    def decode(
        self, *, bundle: WorldBundle, script_paths: list[Path], story_key: str | None,
    ) -> DecodeResult:
        result = super().decode(bundle=bundle, script_paths=script_paths, story_key=story_key)
        result.story_data = lower_linked_prose(
            result.story_data, source=", ".join(str(path) for path in script_paths),
            class_registry=self.class_registry,
        )
        return result
