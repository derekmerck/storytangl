"""Afreet-derived labels and catalogue declarations for the modiste fixture."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field
import yaml

from tangl.media.media_creators.svg_forge.svg_catalog import (
    SvgCatalog, SvgCatalogDiagnostic, SvgGroupDeclaration, index_svg_catalog,
)
from tangl.media.media_creators.svg_forge.svg_source_manager import SvgSourceManager
from tangl.media.media_resource.resource_manager import ResourceManager


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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit an explicitly supplied SVG source")
    parser.add_argument("source", type=Path)
    audit(parser.parse_args().source)
