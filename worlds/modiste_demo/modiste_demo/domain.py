"""Afreet-derived labels and catalogue declarations for the modiste fixture."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field
import yaml

from tangl.core import BehaviorRegistry, EntityTemplate
from tangl.core.bases import Unstructurable
from tangl.media.media_creators.svg_forge.vector_spec import VectorSpec
from tangl.media.media_creators.svg_forge.svg_png_spec import SvgPngSpec
from tangl.media.media_creators.svg_forge.render_playwright import renderer_identity
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
    regions: dict[str, tuple[str, ...]] = Field(default_factory=dict)


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
    revision = sha256(json.dumps(pack.model_dump(mode="json", exclude={"regions"}), sort_keys=True,
                                 separators=(",", ":")).encode()).hexdigest()
    return resolve_plan(catalog, recipe, palettes=pack.palettes, operations=tuple(operations),
                        diagnostics=tuple(diagnostics), policy_revision=revision)


class RegionExport(Unstructurable):
    source_id: UUID
    beauty_id: UUID
    plan_identity: str
    masks: dict[str, UUID]
    coverage: dict[str, str]
    view_box: tuple[float, float, float, float]
    dimensions: tuple[int, int]
    renderer: str
    mask_revision: str = "1"
    fit: str = "contain"
    encoding: str = "white=region; black=occluder; multiply red by alpha"
    depth: str = "absent"
    limits: tuple[str, ...] = (
        "opaque fill approximation; source transparency, strokes and filters are not represented",
        "only path and primitive fills are supported; use, image and text are not represented",
        "stylesheet-driven geometry and clipping are not represented",
    )


class ModisteDesk(ProseBlock):
    """The accepted selections for the catalogue's one demonstrator."""

    outfit: str = Field(default="underwear", json_schema_extra={"include": True})
    palette: str = Field(default="rose", json_schema_extra={"include": True})
    render_png: bool = False
    render_error: str = Field(default="", json_schema_extra={"include": True})
    exports: list[RegionExport] = Field(default_factory=list,
        json_schema_extra={"include": True, "unstructurable": True})


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
            for item in caller.media:
                dep = ctx.graph.get(item["dependency_id"])
                # The next PLANNING precedes UPDATE's replacement request.
                dep.requirement.provision_policy = ProvisionPolicy(0)
                dep.set_provider(None, _ctx=ctx)

        edge = ctx.selected_edge
        if isinstance(edge, Action) and edge.label == "export_regions":
            from hashlib import sha256
            from PIL import Image, ImageChops

            pack, catalog = catalog_for(ctx.graph)
            plan = resolve_modiste(pack, catalog, outfit=caller.outfit, palette=caller.palette)
            if not pack.regions:
                caller.render_error = "Missing region coverage metadata"
                return
            if not plan.ok or len(caller.media) < 2:
                caller.render_error = "A valid figure and beauty PNG are required for export"
                return
            svg_dep = ctx.graph.get(caller.media[0]["dependency_id"])
            png_dep = ctx.graph.get(caller.media[1]["dependency_id"])
            if not svg_dep.render_ready or not png_dep.render_ready:
                caller.render_error = "A valid figure and beauty PNG are required for export"
                return
            source, beauty = svg_dep.provider, png_dep.provider
            selected = {entry.key: entry.source_id for entry in plan.entries}
            regions = {name: tuple(selected[key] for key in keys if key in selected)
                       for name, keys in pack.regions.items()}
            used = {item for ids in regions.values() for item in ids}
            occluders = tuple(entry.source_id for entry in plan.entries if entry.source_id not in used)
            coverage = {name: "unrepresented" for name, ids in regions.items() if not ids}
            masks = {}
            try:
                version = renderer_identity()
                tree = etree.parse(str(source.path), etree.XMLParser(resolve_entities=False, no_network=True))
                shapes = {"path", "rect", "circle", "ellipse", "polygon", "polyline"}
                unsupported = {"use", "image", "text", "foreignObject", "line"}
                dimensions = (png_dep.requirement.media_spec.width, png_dep.requirement.media_spec.height)
                with Image.open(beauty.path) as image:
                    if image.size != dimensions:
                        raise ValueError("Beauty PNG dimensions do not match its request")
                for name, ids in regions.items():
                    if not ids:
                        continue
                    elements = [element for identifier in ids
                                for group in tree.xpath("//*[@id=$id]", id=identifier)
                                for element in group.iter() if isinstance(element.tag, str)]
                    kinds = {etree.QName(element).localname for element in elements}
                    if not kinds & shapes:
                        coverage[name] = "unrepresented"
                        continue
                    spec = SvgPngSpec(label=f"region-{name}", source_id=source.uid,
                        source_hash=source.get_content_hash(),
                        source_sha256=sha256(source.path.read_bytes()).hexdigest(),
                        width=dimensions[0], height=dimensions[1], renderer_version=version,
                        mask_region=name, mask_regions=regions, mask_occluders=occluders)
                    dep = EntityTemplate.from_data({"kind": MediaDep, "predecessor_id": caller.uid,
                        "media_spec": spec, "scope": "story"}).materialize(registry=ctx.graph)
                    try:
                        resolved = Resolver.from_ctx(ctx).resolve_dependency(dep, _ctx=ctx)
                    except (ValueError, OSError):
                        dep.requirement.provision_policy = ProvisionPolicy(0)
                        raise
                    if not resolved:
                        dep.requirement.provision_policy = ProvisionPolicy(0)
                        raise ValueError(f"Region export failed: {name}")
                    masks[name] = dep.provider.uid
                    with Image.open(dep.provider.path) as image:
                        red, _, _, alpha = image.convert("RGBA").split()
                        if len(ids) < len(pack.regions[name]) or kinds & unsupported:
                            coverage[name] = "partial"
                        else:
                            coverage[name] = "visible" if ImageChops.multiply(red, alpha).getbbox() else "occluded"
                caller.exports = [*caller.exports, RegionExport(source_id=source.uid, beauty_id=beauty.uid,
                    plan_identity=plan.identity, masks=masks, coverage=coverage, view_box=plan.registration,
                    dimensions=dimensions, renderer=version)]
                caller.render_error = ""
            except (ValueError, OSError) as exc:
                caller.render_error = str(exc)
            return
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
            same = (dependency.render_ready
                    and dependency.requirement.media_spec.spec_fingerprint() == spec.spec_fingerprint())
            if not same:
                dependency.set_provider(None, _ctx=ctx)
                dependency.requirement.media_spec = spec
        else:
            same = False
            dependency = EntityTemplate.from_data({
                "kind": MediaDep, "predecessor_id": caller.uid, "media_spec": spec,
                "media_role": "narrative_im", "scope": "story",
            }).materialize(registry=ctx.graph)
            caller.media = [{"dependency_id": dependency.uid, "media_role": "narrative_im"}]
        if not same:
            dependency.requirement.provision_policy = ProvisionPolicy.ANY
            try:
                resolved = Resolver.from_ctx(ctx).resolve_dependency(dependency, _ctx=ctx)
            except ValueError as exc:
                suspend()
                caller.render_error = str(exc)
                return
            if not resolved:
                suspend()
                caller.render_error = "Figure could not be provisioned"
                return
        if not caller.render_png:
            caller.render_error = ""
            return
        from hashlib import sha256

        try:
            figure = dependency.provider
            png = SvgPngSpec(
                label="modiste-figure-png", source_id=figure.uid,
                source_hash=figure.get_content_hash(), source_sha256=sha256(figure.path.read_bytes()).hexdigest(),
                width=496, height=665, renderer_version=renderer_identity(),
            )
            if len(caller.media) > 1:
                raster_dep = ctx.graph.get(caller.media[1]["dependency_id"])
                if (raster_dep.render_ready
                        and raster_dep.requirement.media_spec.spec_fingerprint() == png.spec_fingerprint()):
                    caller.render_error = ""
                    return
                raster_dep.set_provider(None, _ctx=ctx)
                raster_dep.requirement.media_spec = png
            else:
                raster_dep = EntityTemplate.from_data({
                    "kind": MediaDep, "predecessor_id": caller.uid, "media_spec": png,
                    "media_role": "narrative_im", "scope": "story",
                }).materialize(registry=ctx.graph)
                caller.media = [*caller.media, {"dependency_id": raster_dep.uid, "media_role": "narrative_im"}]
            raster_dep.requirement.provision_policy = ProvisionPolicy.ANY
            if not Resolver.from_ctx(ctx).resolve_dependency(raster_dep, _ctx=ctx):
                raise ValueError("PNG figure could not be provisioned")
            caller.render_error = ""
        except (ValueError, OSError) as exc:
            if len(caller.media) > 1:
                raster_dep = ctx.graph.get(caller.media[1]["dependency_id"])
                raster_dep.requirement.provision_policy = ProvisionPolicy(0)
                raster_dep.set_provider(None, _ctx=ctx)
            caller.render_error = str(exc)

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
            "modiste_export": (
                ", ".join(f"{name}: {status}" for name, status in caller.exports[-1].coverage.items())
                + "; depth: absent" if caller.exports else ""
            ),
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
