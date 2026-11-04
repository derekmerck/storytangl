"""Read-only indexing of selected groups from an admitted SVG resource."""
from __future__ import annotations

from hashlib import sha256
import json
import math
import re
from typing import Mapping

from lxml import etree
from PIL import ImageColor
from pydantic import BaseModel, ConfigDict

from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag
from tangl.utils.hashing import compute_data_hash, hashing_func

_SVG = "http://www.w3.org/2000/svg"
_URL_REF = re.compile(r"url\(\s*['\"]?#([^\s)'\"]+)['\"]?\s*\)")


class SvgGroupDeclaration(BaseModel):
    """An explicit source-group nomination and its consumer-owned metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    key: str
    source_id: str
    aliases: tuple[str, ...] = ()
    order: int = 0
    channels: tuple[str, ...] = ()
    registration: tuple[float, float, float, float] | None = None


class SvgCatalogEntry(SvgGroupDeclaration):
    """A nominated group with its original source locator."""

    locator: str


class SvgCatalogDiagnostic(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    code: str
    subject: str
    detail: str


class SvgCatalog(BaseModel):
    """A value-only snapshot; no XML tree or resource registry is retained."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    source_label: str
    resource_hash: str
    source_sha256: str
    view_box: tuple[float, float, float, float] | None
    declared_channels: tuple[str, ...]
    palette_sha256: str
    source_groups: tuple[tuple[str, ...], ...]
    source_ids: tuple[str, ...]
    entries: tuple[SvgCatalogEntry, ...]
    diagnostics: tuple[SvgCatalogDiagnostic, ...]

    @property
    def digest(self) -> str:
        """Hash the portable catalog value, including diagnostics and provenance."""
        data = self.model_dump(mode="json")
        return sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def lookup(self, key: str) -> SvgCatalogEntry | None:
        matches = [entry for entry in self.entries if key == entry.key or key in entry.aliases]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous catalog key: {key}")
        return matches[0] if matches else None


def index_svg_catalog(
    source: MediaResourceInventoryTag,
    declarations: tuple[SvgGroupDeclaration, ...],
    *,
    channels: frozenset[str] = frozenset(),
    palettes: Mapping[str, Mapping[str, Mapping[str, str]]] | None = None,
) -> SvgCatalog:
    """Index declared groups and report integrity problems without altering the source.

    The caller owns names, aliases, ordering, channel meanings and registration.
    Only file-backed, explicitly admitted SVG resources are supported here.
    """
    if source.path is None:
        raise ValueError("SVG catalog requires a file-backed media resource")
    raw = source.path.read_bytes()
    root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True))
    if root.tag != f"{{{_SVG}}}svg":
        raise ValueError("Expected an SVG document")
    diagnostics: list[SvgCatalogDiagnostic] = []

    def report(code: str, subject: str, detail: str) -> None:
        diagnostics.append(SvgCatalogDiagnostic(code=code, subject=subject, detail=detail))

    if source.content_hash != hashing_func(compute_data_hash(raw)):
        report("resource_hash_mismatch", source.label or source.path.name, "Source bytes changed")

    try:
        view_box = tuple(float(value) for value in root.attrib["viewBox"].replace(",", " ").split())
        if (len(view_box) != 4 or not all(math.isfinite(value) for value in view_box)
                or view_box[2] <= 0 or view_box[3] <= 0):
            raise ValueError
    except (KeyError, ValueError):
        view_box = None
        report("invalid_viewbox", source.label or source.path.name, "Expected four viewBox values")

    elements: dict[str, etree._Element] = {}
    source_groups = []
    duplicates: set[str] = set()
    refs: set[str] = set()
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        identifier = element.get("id")
        if identifier:
            if identifier in elements:
                duplicates.add(identifier)
            else:
                elements[identifier] = element
            if element.tag == f"{{{_SVG}}}g":
                ancestors = [parent.get("id") for parent in reversed(list(element.iterancestors()))
                             if parent.tag == f"{{{_SVG}}}g" and parent.get("id")]
                source_groups.append((*ancestors, identifier))
        for name, value in element.attrib.items():
            refs.update(_URL_REF.findall(value))
            if etree.QName(name).localname == "href" and value.startswith("#"):
                refs.add(value[1:])
        if etree.QName(element).localname == "style" and element.text:
            refs.update(_URL_REF.findall(element.text))
    for identifier in sorted(duplicates):
        report("duplicate_id", identifier, "SVG ID occurs more than once")
    for identifier in sorted(refs - elements.keys()):
        report("unresolved_reference", identifier, "Local SVG reference is missing")

    entries: list[SvgCatalogEntry] = []
    names: dict[str, str] = {}
    for declaration in declarations:
        for name in (declaration.key, *declaration.aliases):
            if name in names:
                report("key_collision", name, f"Already declared by {names[name]}")
            else:
                names[name] = declaration.key
        element = elements.get(declaration.source_id)
        if element is None or element.tag != f"{{{_SVG}}}g":
            report("missing_group", declaration.key, declaration.source_id)
            continue
        if declaration.source_id in duplicates:
            report("ambiguous_group", declaration.key, declaration.source_id)
            continue
        if declaration.registration is not None and declaration.registration != view_box:
            report("registration_mismatch", declaration.key, str(declaration.registration))
        for channel in declaration.channels:
            if channel not in channels:
                report("undeclared_channel", declaration.key, channel)
        entries.append(SvgCatalogEntry(
            **declaration.model_dump(), locator=f"#{declaration.source_id}",
        ))

    palette_diagnostics, valid_palettes = validate_palette_bindings(
        palettes, channels=channels, source_ids=frozenset(elements),
    )
    diagnostics.extend(palette_diagnostics)

    return SvgCatalog(
        source_label=source.label or source.path.name,
        resource_hash=source.content_hash.hex(),
        source_sha256=sha256(raw).hexdigest(),
        view_box=view_box,
        declared_channels=tuple(sorted(channels)),
        palette_sha256=sha256(json.dumps(valid_palettes, sort_keys=True,
                                           separators=(",", ":")).encode()).hexdigest(),
        source_groups=tuple(source_groups),
        source_ids=tuple(sorted(elements)),
        entries=tuple(entries),
        diagnostics=tuple(sorted(diagnostics, key=lambda d: (d.code, d.subject, d.detail))),
    )


def validate_palette_bindings(
    palettes: Mapping[str, Mapping[str, Mapping[str, str]]] | None, *,
    channels: frozenset[str], source_ids: frozenset[str],
) -> tuple[list[SvgCatalogDiagnostic], dict[str, dict[str, dict[str, str]]]]:
    """Validate palette data without modifying it or loading SVG geometry."""
    diagnostics: list[SvgCatalogDiagnostic] = []

    def report(code: str, subject: str, detail: str) -> None:
        diagnostics.append(SvgCatalogDiagnostic(code=code, subject=subject, detail=detail))

    if palettes is not None and not isinstance(palettes, Mapping):
        report("malformed_palette", "palettes", "Expected named palettes")
        palettes = {}
    valid_palettes: dict[str, dict[str, dict[str, str]]] = {}
    for palette, bindings in sorted((palettes or {}).items(), key=lambda item: str(item[0])):
        if not isinstance(palette, str) or not palette.strip():
            report("malformed_palette", str(palette), "Expected a palette name")
            continue
        if not isinstance(bindings, Mapping):
            report("malformed_palette", palette, "Expected channel bindings")
            continue
        valid_palettes[palette] = {}
        for channel, properties in sorted(bindings.items(), key=lambda item: str(item[0])):
            if not isinstance(channel, str) or not channel.strip():
                report("malformed_palette_binding", palette, f"Invalid channel: {channel}")
                continue
            if channel not in channels:
                report("undeclared_palette_channel", palette, channel)
            if not isinstance(properties, Mapping) or not properties or any(
                not isinstance(key, str) or not key.strip()
                or not isinstance(value, str) or not value.strip()
                for key, value in properties.items()
            ):
                report("malformed_palette_binding", palette, channel)
                continue
            valid_palettes[palette][channel] = dict(properties)
            for prop, value in properties.items():
                if prop in {"opacity", "fill-opacity", "stroke-opacity", "stop-opacity"}:
                    try:
                        if not 0 <= float(value) <= 1:
                            raise ValueError(value)
                    except ValueError:
                        report("malformed_palette_binding", palette, f"{channel}.{prop}: {value}")
                if prop in {"fill", "stroke", "stop-color"}:
                    local_refs = _URL_REF.findall(value)
                    if local_refs:
                        for identifier in local_refs:
                            if identifier not in source_ids:
                                report("unresolved_reference", identifier, f"Palette {palette}")
                    elif value not in {"none", "currentColor"}:
                        try:
                            if value.startswith("#"):
                                pattern = r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})"
                                if not re.fullmatch(pattern, value):
                                    raise ValueError(value)
                            else:
                                ImageColor.getrgb(value)
                        except ValueError:
                            report(
                                "malformed_palette_binding", palette, f"{channel}.{prop}: {value}",
                            )

    return diagnostics, valid_palettes
