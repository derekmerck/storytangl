"""Afreet-derived labels and catalogue declarations for the modiste fixture."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field
import yaml

from tangl.core import BehaviorRegistry, EntityTemplate
from tangl.media.media_creators.svg_forge.vector_spec import VectorSpec
from tangl.media.media_resource import MediaDep
from tangl.media.media_resource.media_provisioning import MediaInventoryProvisioner
from tangl.media.media_creators.svg_forge.svg_catalog import (
    SvgCatalog, SvgCatalogDiagnostic, SvgGroupDeclaration, index_svg_catalog,
)
from tangl.media.media_creators.svg_forge.svg_source_manager import SvgSourceManager
from tangl.media.media_creators.svg_forge.svg_plan import RenderPlan
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.prose.naming import ProseBlock, get_authorities as naming_authorities
from tangl.story import Action, StoryGraph
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm import ProvisionPolicy, Resolver


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
    render_error: str = Field(default="", json_schema_extra={"include": True})


def palette_targets(
    source: Path, plan: RenderPlan, channels: frozenset[str],
) -> tuple[tuple[str, str, str, tuple[int, ...]], ...]:
    """Map Afreet annotations to explicit painted source elements."""
    tree = etree.parse(str(source), etree.XMLParser(resolve_entities=False, no_network=True))
    targets = []
    for entry in plan.entries:
        matches = tree.xpath("//*[@id=$id]", id=entry.source_id)
        if len(matches) != 1:
            raise ValueError(f"Missing or ambiguous group: {entry.source_id}")
        for element in matches[0].iter():
            if not isinstance(element.tag, str):
                continue
            style = dict(item.strip().split(":", 1) for item in element.get("style", "").split(";")
                         if ":" in item)
            if not (fill := style.get("fill", element.get("fill"))) or fill == "none":
                continue
            path = []
            anchor = element
            while anchor is not None:
                identifier = anchor.get("id")
                if identifier:
                    _, found, _, _ = parse_annotation(identifier, channels)
                    if found:
                        if len(found) != 1:
                            raise ValueError(f"Ambiguous channel: {identifier}")
                        targets.append((found[0], "fill", identifier, tuple(reversed(path))))
                        break
                if anchor is matches[0]:
                    break
                parent = anchor.getparent()
                path.append(parent.index(anchor))
                anchor = parent
    expected = {(channel, prop) for entry in plan.entries for channel in entry.channels
                for prop in plan.bindings.get(channel, {})}
    missing = expected - {(channel, prop) for channel, prop, _, _ in targets}
    if missing:
        raise ValueError(f"Missing palette targets: {sorted(missing)}")
    return tuple(targets)


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
        def suspend() -> None:
            if caller.media:
                dep = ctx.graph.get(caller.media[0]["dependency_id"])
                # The next PLANNING precedes UPDATE's replacement request.
                dep.requirement.provision_policy = ProvisionPolicy(0)
                dep.set_provider(None, _ctx=ctx)

        edge = ctx.selected_edge
        if isinstance(edge, Action):
            if edge.label in {"underwear", "camisole"}:
                caller.outfit = edge.label
            elif edge.label in {"rose", "blue"}:
                caller.palette = edge.label
        pack, catalog = catalog_for(ctx.graph)
        plan = resolve_modiste(pack, catalog, outfit=caller.outfit, palette=caller.palette)
        if not plan.ok:
            suspend()
            caller.render_error = ""
            return
        source = ctx.graph.factory.resources.get_rit(catalog.source_label)
        if source is None or source.path is None or not source.path.is_file():
            suspend()
            caller.render_error = "Figure source is unavailable"
            return
        local = MediaInventoryProvisioner.graph_local_copy(source, _ctx=ctx)
        if local.registry is not ctx.graph:
            ctx.graph.add(local, _ctx=ctx)
        try:
            targets = palette_targets(source.path, plan, frozenset(pack.channels))
        except (ValueError, OSError, etree.XMLSyntaxError) as exc:
            suspend()
            caller.render_error = str(exc)
            return
        spec = VectorSpec(
            label="modiste-figure", source_id=local.uid, source_hash=local.get_content_hash(),
            source_sha256=catalog.source_sha256,
            plan_identity=plan.identity, registration=plan.registration,
            locators=tuple(entry.locator for entry in plan.entries), bindings=plan.bindings,
            targets=targets,
        )
        if caller.media:
            dependency = ctx.graph.get(caller.media[0]["dependency_id"])
            if (dependency.render_ready
                    and dependency.requirement.media_spec.spec_fingerprint() == spec.spec_fingerprint()):
                return
            dependency.set_provider(None, _ctx=ctx)
            dependency.requirement.media_spec = spec
        else:
            dependency = EntityTemplate.from_data({
                "kind": MediaDep, "predecessor_id": caller.uid, "media_spec": spec,
                "media_role": "narrative_im", "scope": "story",
            }).materialize(registry=ctx.graph)
            caller.media = [{"dependency_id": dependency.uid, "media_role": "narrative_im"}]
        dependency.requirement.provision_policy = ProvisionPolicy.ANY
        try:
            resolved = Resolver.from_ctx(ctx).resolve_dependency(dependency, _ctx=ctx)
        except ValueError as exc:
            suspend()
            caller.render_error = str(exc)
            return
        if not resolved:
            suspend()
        caller.render_error = "" if resolved else "Figure could not be provisioned"

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
            "modiste_diagnostics": "; ".join(filter(None, [caller.render_error, *(
                f"{item.code}: {item.subject} {item.detail}" for item in plan.diagnostics
            )])),
        }

    return [*naming_authorities(), dispatch]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit an explicitly supplied SVG source")
    parser.add_argument("source", type=Path)
    audit(parser.parse_args().source)
