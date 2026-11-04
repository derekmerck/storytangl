"""Pure resolution of explicit selections against an SVG catalog."""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .svg_catalog import (
    SvgCatalog, SvgCatalogDiagnostic, SvgCatalogEntry, validate_palette_bindings,
)


class Recipe(BaseModel):
    """Logical selections and finite consumer-owned facts, without source locators."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    selections: tuple[str, ...]
    facts: tuple[str, ...] = ()
    palette: str
    overrides: dict[str, dict[str, str]] = Field(default_factory=dict)


class Operation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["add", "remove", "substitute", "suppress"]
    target: str
    replacement: str | None = None
    reason: str = ""


class Rule(BaseModel):
    """A finite, explicit policy over recipe facts."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    when: tuple[str, ...] = ()
    require: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    operations: tuple[Operation, ...] = ()


class RenderPlan(BaseModel):
    """Resolved value data only; errors never produce a successful partial plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    recipe: Recipe
    canonical_selections: tuple[str, ...]
    catalog_digest: str
    source_label: str
    source_sha256: str
    resource_hash: str
    registration: tuple[float, float, float, float] | None
    entries: tuple[SvgCatalogEntry, ...]
    bindings: dict[str, dict[str, str]]
    binding_sources: dict[str, dict[str, str]]
    decisions: tuple[str, ...]
    diagnostics: tuple[SvgCatalogDiagnostic, ...]
    rule_digest: str

    @property
    def ok(self) -> bool:
        return not self.diagnostics

    @property
    def identity(self) -> str:
        data = self.model_dump(mode="json")
        data["recipe"]["selections"] = list(self.canonical_selections)
        return sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def resolve_plan(
    catalog: SvgCatalog,
    recipe: Recipe,
    *,
    palettes: dict[str, dict[str, dict[str, str]]],
    defaults: dict[str, dict[str, str]] | None = None,
    rules: tuple[Rule, ...] = (),
    operations: tuple[Operation, ...] = (),
    diagnostics: tuple[SvgCatalogDiagnostic, ...] = (),
    policy_revision: str = "",
) -> RenderPlan:
    """Resolve selections and ordered operations without changing any input."""
    errors = list(catalog.diagnostics) + list(diagnostics)
    decisions: list[str] = []
    selected: list[str] = []
    substitutions: dict[str, str] = {}

    def error(code: str, subject: str, detail: str) -> None:
        errors.append(SvgCatalogDiagnostic(code=code, subject=subject, detail=detail))

    def canonical(key: str) -> str | None:
        try:
            entry = catalog.lookup(key)
        except ValueError:
            error("ambiguous_reference", key, "Catalog alias is ambiguous")
            return None
        if entry is None:
            error("missing_reference", key, "Catalog entry is unavailable")
            return None
        return entry.key

    for key in recipe.selections:
        canonical_key = canonical(key)
        if canonical_key is not None and canonical_key not in selected:
            selected.append(canonical_key)
    canonical_selections = tuple(selected)

    active_operations = list(operations)
    facts = frozenset(recipe.facts)
    for rule in rules:
        if not set(rule.when) <= facts:
            continue
        for fact in rule.require:
            if fact not in facts:
                error("requirement", rule.name, fact)
        for fact in rule.exclude:
            if fact in facts:
                error("excluded", rule.name, fact)
        active_operations.extend(rule.operations)

    for operation in active_operations:
        if operation.kind != "substitute" and operation.replacement is not None:
            error("conflicting_rule", operation.target, "Replacement requires substitution")
            continue
        target = canonical(operation.target)
        if target is None:
            continue
        replacement = canonical(operation.replacement) if operation.replacement else None
        if operation.kind == "add":
            if target not in selected:
                selected.append(target)
                decisions.append(operation.reason or f"add: {target}")
        elif operation.kind in {"remove", "suppress", "substitute"}:
            if (operation.kind == "substitute" and target in substitutions
                    and substitutions[target] != replacement):
                error("conflicting_rule", operation.target, "Conflicting substitutions")
                continue
            if target not in selected:
                error("conflicting_rule", operation.target, "Entry is not selected")
                continue
            if operation.kind == "substitute":
                if replacement is None:
                    error("conflicting_rule", operation.target, "Substitution requires replacement")
                    continue
                substitutions[target] = replacement
                selected.remove(target)
                if replacement not in selected:
                    selected.append(replacement)
            else:
                selected.remove(target)
            decisions.append(operation.reason or f"{operation.kind}: {target}")

    bindings: dict[str, dict[str, str]] = {}
    sources: dict[str, dict[str, str]] = {}
    palette = palettes.get(recipe.palette)
    if palette is None:
        error("unknown_palette", recipe.palette, "Palette is not declared")
        palette = {}
    layers = (("default", defaults or {}), (f"palette:{recipe.palette}", palette),
              ("override", recipe.overrides))
    for origin, layer in layers:
        found, _ = validate_palette_bindings(
            {origin: layer}, channels=frozenset(catalog.declared_channels),
            source_ids=frozenset(catalog.source_ids),
        )
        errors.extend(found)
        if not isinstance(layer, Mapping):
            continue
        for channel, properties in layer.items():
            if not isinstance(channel, str) or not isinstance(properties, Mapping):
                continue
            for prop, value in properties.items():
                if not isinstance(prop, str) or not isinstance(value, str):
                    continue
                bindings.setdefault(channel, {})[prop] = value
                sources.setdefault(channel, {})[prop] = origin

    entries = [catalog.lookup(key) for key in selected] if not errors else []
    entries.sort(key=lambda entry: entry.order)
    def canonical_operation(operation: Operation) -> dict[str, object]:
        data = operation.model_dump(mode="json")
        for field in ("target", "replacement"):
            key = data[field]
            if key is not None:
                try:
                    entry = catalog.lookup(key)
                except ValueError:
                    entry = None
                if entry is not None:
                    data[field] = entry.key
        return data

    rule_data = [policy_revision]
    for rule in rules:
        data = rule.model_dump(mode="json")
        data["operations"] = [canonical_operation(item) for item in rule.operations]
        rule_data.append(data)
    rule_data.extend(canonical_operation(item) for item in operations)
    rule_digest = sha256(
        json.dumps(rule_data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return RenderPlan(
        recipe=recipe, canonical_selections=canonical_selections,
        catalog_digest=catalog.digest, source_label=catalog.source_label,
        source_sha256=catalog.source_sha256, resource_hash=catalog.resource_hash,
        registration=catalog.view_box,
        entries=tuple(entries) if not errors else (), bindings=bindings, binding_sources=sources,
        decisions=tuple(decisions), diagnostics=tuple(errors), rule_digest=rule_digest,
    )
