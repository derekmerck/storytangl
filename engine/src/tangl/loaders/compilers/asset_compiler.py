from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import TypeAdapter

from tangl.core import Singleton, TokenCatalog

from ..bundle import WorldBundle


class AssetManagerProtocol(Protocol):
    values: dict[str, Any]


class AssetCompiler:
    """Compile world-owned singleton catalog sources into the assets facet."""

    def load_into(
        self,
        bundle: WorldBundle,
        asset_manager: AssetManagerProtocol,
        class_registry: dict[str, type],
    ) -> None:
        for source in bundle.manifest.assets:
            definition_type = class_registry.get(source.asset_kind)
            if (
                not isinstance(definition_type, type)
                or not issubclass(definition_type, Singleton)
            ):
                raise ValueError(
                    f"Unknown singleton asset kind '{source.asset_kind}' "
                    f"in world '{bundle.manifest.label}'."
                )
            catalog = self._load_catalog(
                source_path=bundle.bundle_root / source.source,
                definition_type=definition_type,
                world_label=bundle.manifest.label,
                catalog_label=source.catalog,
            )
            if source.catalog in asset_manager.values:
                if asset_manager.values[source.catalog] == catalog:
                    continue
                raise ValueError(
                    f"Duplicate asset catalog '{source.catalog}' "
                    f"in world '{bundle.manifest.label}'."
                )
            asset_manager.values[source.catalog] = catalog

    @staticmethod
    def _load_catalog(
        *,
        source_path: Path,
        definition_type: type[Singleton],
        world_label: str,
        catalog_label: str,
    ) -> TokenCatalog[Singleton]:
        with source_path.open(encoding="utf-8") as source_file:
            data = yaml.safe_load(source_file) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Singleton catalog at {source_path} must be a mapping.")

        definitions: list[Singleton] = []
        for catalog_id, raw_definition in data.items():
            if not isinstance(catalog_id, str) or not isinstance(raw_definition, dict):
                raise ValueError(f"Singleton catalog at {source_path} must map ids to mappings.")
            payload = {
                **raw_definition,
                "label": f"{world_label}:{catalog_label}:{catalog_id}",
                "catalog_id": catalog_id,
            }
            existing = definition_type.get_instance(payload["label"])
            if existing is None:
                definitions.append(definition_type(**payload))
                continue
            expected = AssetCompiler._normalized_fields(definition_type, payload)
            actual = {
                field_name: getattr(existing, field_name)
                for field_name in expected
            }
            if actual != expected:
                raise ValueError(
                    f"Conflicting singleton catalog definition '{payload['label']}'."
                )
            definitions.append(existing)
        return TokenCatalog(
            wst=definition_type,
            members=tuple(definitions),
            label=catalog_label,
        )

    @staticmethod
    def _normalized_fields(
        definition_type: type[Singleton],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        unknown = set(payload) - set(definition_type.model_fields)
        if unknown:
            raise ValueError(
                f"Unknown fields for {definition_type.__name__}: {', '.join(sorted(unknown))}."
            )
        expected: dict[str, Any] = {}
        for field_name, field_info in definition_type.model_fields.items():
            if field_name == "uid":
                continue
            if field_name in payload:
                value = payload[field_name]
            elif field_info.is_required():
                raise ValueError(
                    f"Missing required field '{field_name}' for {definition_type.__name__}."
                )
            else:
                value = field_info.get_default(call_default_factory=True)
            expected[field_name] = TypeAdapter(field_info.annotation).validate_python(value)
        return expected
