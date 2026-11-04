"""Afreet-derived labels and catalogue declarations for the modiste fixture."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field
import yaml

from tangl.core import BehaviorRegistry
from tangl.media.media_creators.svg_forge.svg_catalog import (
    SvgCatalog, SvgCatalogDiagnostic, SvgGroupDeclaration, index_svg_catalog,
)
from tangl.media.media_creators.svg_forge.svg_source_manager import SvgSourceManager
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.prose.naming import ProseBlock, get_authorities as naming_authorities
from tangl.story import Action, StoryGraph
from tangl.vm.runtime.frame import PhaseCtx


class Collection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shapes: tuple[str, ...]
    tags: tuple[str, ...] = ()
    flags: dict[str, tuple[str, ...] | bool] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class Group(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    order: int
    aliases: tuple[str, ...] = ()


class Pack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    registration: tuple[float, float, float, float]
    channels: tuple[str, ...]
    groups: dict[str, Group]
    collections: dict[str, dict[str, Collection]]
    coverage: dict[str, Any]
    palettes: dict[str, Any]


def parse_annotation(
    identifier: str, channels: frozenset[str],
) -> tuple[str | None, tuple[str, ...], dict[str, str], tuple[str, ...]]:
    """Interpret Afreet's encoded labels without rewriting source IDs.

    Unknown words are retained so a caller can distinguish fixed-color or
    experimental annotations from recognized channel and hint vocabulary.
    """
    parts = SvgSourceManager.clean_label(identifier).split()
    name = None
    if parts and parts[0] not in channels and ":" not in parts[0]:
        name = parts.pop(0)
    found_channels = []
    hints = {}
    other = []
    for part in parts:
        if part in channels:
            found_channels.append(part)
        elif ":" in part:
            key, value = part.split(":", 1)
            hints[key] = value
        else:
            other.append(part)
    return name, tuple(found_channels), hints, tuple(other)


def load_pack(manager: ResourceManager) -> tuple[Pack, SvgCatalog]:
    """Load one explicitly selected world resource pack through its manager."""
    root = manager.resource_path
    data = yaml.safe_load((root / "catalog.yaml").read_text())
    data["palettes"] = yaml.safe_load((root / "palettes.yaml").read_text())
    pack = Pack.model_validate(data)
    source = manager.get_rit("afreet-subset.svg")
    if source is None:
        source = manager.register_file(Path("afreet-subset.svg"))
    tree = etree.parse(str(source.path), etree.XMLParser(resolve_entities=False, no_network=True))
    channels = frozenset(pack.channels)
    declarations = []
    for key, group in pack.groups.items():
        matches = tree.xpath("//*[@id=$identifier]", identifier=group.id)
        found_channels = set()
        if len(matches) == 1:
            for element in matches[0].iter():
                if identifier := element.get("id"):
                    _, annotated_channels, _, _ = parse_annotation(identifier, channels)
                    found_channels.update(annotated_channels)
        parent, _ = key.split(".", 1)
        normalized = f"{parent}.{SvgSourceManager.clean_label(group.id)}"
        aliases = group.aliases + ((normalized,) if normalized != key else ())
        declarations.append(SvgGroupDeclaration(
            key=key, source_id=group.id, aliases=aliases, order=group.order,
            channels=tuple(sorted(found_channels)), registration=pack.registration,
        ))
    result = index_svg_catalog(
        source, tuple(declarations), channels=channels, palettes=pack.palettes,
    )
    diagnostics = list(result.diagnostics)
    available = {name for entry in result.entries for name in (entry.key, *entry.aliases)}
    for family, choices in pack.collections.items():
        for choice, collection in choices.items():
            references = list(collection.shapes)
            for changes in collection.flags.values():
                if changes is not False and changes is not True:
                    references.extend(shape.lstrip("+-") for shape in changes)
            for shape in references:
                if shape not in available:
                    diagnostics.append(SvgCatalogDiagnostic(
                        code="missing_collection_group", subject=f"{family}.{choice}", detail=shape,
                    ))
    diagnostics.sort(key=lambda d: (d.code, d.subject, d.detail))
    return pack, result.model_copy(update={"diagnostics": tuple(diagnostics)})


def audit(path: Path) -> None:
    """Report structure and integrity of an explicitly supplied SVG."""
    from collections import Counter
    from hashlib import sha256

    raw = path.read_bytes()
    root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True))
    print(f"sha256={sha256(raw).hexdigest()}")
    print(f"viewBox={root.get('viewBox')}")
    print(f"elements={sum(1 for _ in root.iter())}")
    top_groups = sum(
        1 for element in root if isinstance(element.tag, str) and element.tag.endswith("}g")
    )
    print(f"top_groups={top_groups}")
    manager = ResourceManager(path.parent)
    result = index_svg_catalog(manager.register_file(path.resolve()), ())
    counts = Counter(diagnostic.code for diagnostic in result.diagnostics)
    print(f"group_entries={len(result.source_groups)}")
    for code, count in sorted(counts.items()):
        print(f"{code}={count}")


def resolve_modiste(
    pack: Pack,
    catalog: SvgCatalog,
    *,
    body: str = "common",
    hair: str = "toulouse",
    outfit: str = "underwear",
    palette: str = "rose",
    variants: tuple[str, ...] = (),
    overrides: dict[str, dict[str, str]] | None = None,
):
    """Translate this world's collections and flag operations into a pure plan."""
    from hashlib import sha256
    import json

    from tangl.media.media_creators.svg_forge.svg_plan import Operation, Recipe, resolve_plan

    choices = (("body", body), ("hair", hair), ("outfit", outfit))
    selections = []
    operations = []
    diagnostics = []
    known_variants: set[str] = set()
    for family, choice in choices:
        collection = pack.collections.get(family, {}).get(choice)
        if collection is None:
            diagnostics.append(SvgCatalogDiagnostic(
                code="unknown_collection", subject=family, detail=choice,
            ))
            continue
        selections.extend(collection.shapes)
        known_variants.update(collection.flags)
        for variant in variants:
            changes = collection.flags.get(variant)
            if changes is None:
                continue
            if changes is False:
                diagnostics.append(SvgCatalogDiagnostic(
                    code="unsupported_variant", subject=f"{family}.{choice}", detail=variant,
                ))
            elif changes is not True:
                for change in changes:
                    operations.append(Operation(
                        kind="remove" if change.startswith("-") else "add",
                        target=change.lstrip("+-"), reason=f"{family}.{choice}:{variant}",
                    ))
    for variant in variants:
        if variant not in known_variants:
            diagnostics.append(SvgCatalogDiagnostic(
                code="unsupported_variant", subject="recipe", detail=variant,
            ))
    recipe = Recipe(
        selections=tuple(selections),
        facts=tuple(f"{family}:{choice}" for family, choice in choices)
        + tuple(f"variant:{variant}" for variant in variants),
        palette=palette,
        overrides=overrides or {},
    )
    revision = sha256(json.dumps(pack.model_dump(mode="json"), sort_keys=True,
                                 separators=(",", ":")).encode()).hexdigest()
    return resolve_plan(catalog, recipe, palettes=pack.palettes, operations=tuple(operations),
                        diagnostics=tuple(diagnostics), policy_revision=revision)


class ModisteDesk(ProseBlock):
    """The accepted selections for the catalogue's one demonstrator."""

    outfit: str = Field(default="underwear", json_schema_extra={"include": True})
    palette: str = Field(default="rose", json_schema_extra={"include": True})


def get_authorities() -> list[BehaviorRegistry]:
    """Create one world-local authority and its resource-derived catalog cache."""
    dispatch = BehaviorRegistry(label="modiste.catalogue")
    cached: dict[ResourceManager, tuple[Pack, SvgCatalog]] = {}

    def catalog_for(graph: StoryGraph) -> tuple[Pack, SvgCatalog]:
        manager = graph.factory.resources
        if manager not in cached:
            cached[manager] = load_pack(manager)
        return cached[manager]

    @dispatch.register(task="story_ready", wants_caller_kind=StoryGraph, wants_exact_kind=False)
    def prepare_catalogue(*, caller: StoryGraph, **_kwargs: object) -> None:
        if caller.factory.label == "modiste_demo":
            catalog_for(caller)

    @dispatch.register(task="apply_update", wants_caller_kind=ModisteDesk, wants_exact_kind=False)
    def select(*, caller: ModisteDesk, ctx: PhaseCtx, **_kwargs: object) -> None:
        edge = ctx.selected_edge
        if not isinstance(edge, Action):
            return
        if edge.label in {"underwear", "camisole"}:
            caller.outfit = edge.label
        elif edge.label in {"rose", "blue"}:
            caller.palette = edge.label

    @dispatch.register(task="gather_ns", wants_caller_kind=ModisteDesk, wants_exact_kind=False)
    def describe(*, caller: ModisteDesk, **_kwargs: object) -> dict[str, object]:
        pack, catalog = catalog_for(caller.graph)
        plan = resolve_modiste(pack, catalog, outfit=caller.outfit, palette=caller.palette)
        return {
            "modiste_outfit": caller.outfit,
            "modiste_palette": caller.palette,
            "modiste_parts": ", ".join(entry.key for entry in plan.entries),
            "modiste_bindings": ", ".join(
                f"{channel}.{prop}={value}"
                for channel, properties in sorted(plan.bindings.items())
                for prop, value in sorted(properties.items())
            ),
            "modiste_plan_id": plan.identity,
            "modiste_diagnostics": "; ".join(
                f"{item.code}: {item.subject} {item.detail}" for item in plan.diagnostics
            ),
        }

    return [*naming_authorities(), dispatch]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit an explicitly supplied SVG source")
    parser.add_argument("source", type=Path)
    audit(parser.parse_args().source)
