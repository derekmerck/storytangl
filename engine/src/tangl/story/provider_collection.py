"""Provider collection helpers for story runtime handlers."""

from __future__ import annotations

from collections.abc import Iterable as IterableABC
from typing import Any, Iterable

from tangl.core import Singleton, TemplateRegistry, TokenCatalog
from tangl.media.media_resource import MediaInventory


def _registry_from_values(values: Iterable[Any]) -> TemplateRegistry | None:
    found: TemplateRegistry | None = None
    for item in values:
        registry = getattr(item, "registry", None)
        if not isinstance(registry, TemplateRegistry):
            continue
        if found is None:
            found = registry
            continue
        if found is not registry:
            return None
    return found


def _coerce_template_registry_item(value: Any) -> TemplateRegistry | None:
    if isinstance(value, TemplateRegistry):
        return value
    nested = getattr(value, "template_registry", None)
    if isinstance(nested, TemplateRegistry):
        return nested
    if isinstance(value, (str, bytes, dict)) or not isinstance(value, IterableABC):
        return None
    return _registry_from_values(value)


def collect_template_registries(
    providers: Iterable[Any],
    *,
    caller: Any,
    graph: Any = None,
) -> list[TemplateRegistry]:
    registries: list[TemplateRegistry] = []
    seen_ids: set[int] = set()
    for provider in providers:
        if provider is None:
            continue
        get_scope_groups = getattr(provider, "get_template_scope_groups", None)
        raw = get_scope_groups(caller=caller, graph=graph) if callable(get_scope_groups) else provider
        if raw is None:
            continue
        if isinstance(raw, TemplateRegistry):
            values = [raw]
        elif isinstance(raw, (str, bytes, dict)) or not isinstance(raw, IterableABC):
            values = [raw]
        else:
            values = list(raw)
        for value in values:
            registry = _coerce_template_registry_item(value)
            if registry is None:
                continue
            registry_id = id(registry)
            if registry_id in seen_ids:
                continue
            seen_ids.add(registry_id)
            registries.append(registry)
    return registries


def _coerce_token_catalog_item(value: Any) -> TokenCatalog | None:
    if isinstance(value, TokenCatalog):
        return value
    if isinstance(value, type) and issubclass(value, Singleton):
        return TokenCatalog(wst=value)
    return None


def collect_token_catalogs(
    providers: Iterable[Any],
    *,
    caller: Any,
    requirement: Any = None,
    graph: Any = None,
) -> list[TokenCatalog]:
    catalogs: list[TokenCatalog] = []
    seen_ids: set[int] = set()
    for provider in providers:
        if provider is None:
            continue
        get_catalogs = getattr(provider, "get_token_catalogs", None)
        if callable(get_catalogs):
            raw = get_catalogs(caller=caller, requirement=requirement, graph=graph)
        else:
            get_tokenizable = getattr(provider, "get_tokenizable", None)
            raw = get_tokenizable() if callable(get_tokenizable) else None
        if raw is None or isinstance(raw, (str, bytes, dict)):
            continue
        values = list(raw) if isinstance(raw, IterableABC) else [raw]
        for value in values:
            catalog = _coerce_token_catalog_item(value)
            if catalog is None:
                continue
            catalog_id = id(catalog)
            if catalog_id in seen_ids:
                continue
            seen_ids.add(catalog_id)
            catalogs.append(catalog)
    return catalogs


def collect_media_inventories(
    providers: Iterable[Any],
    *,
    caller: Any,
    requirement: Any = None,
    graph: Any = None,
    scope: str | None = None,
) -> list[MediaInventory]:
    inventories: list[MediaInventory] = []
    seen_registry_ids: set[int] = set()
    for provider in providers:
        if provider is None:
            continue
        get_inventories = getattr(provider, "get_media_inventories", None)
        raw = get_inventories(caller=caller, requirement=requirement, graph=graph) if callable(get_inventories) else provider
        if raw is None:
            continue
        if isinstance(raw, (str, bytes, dict)):
            values = [raw]
        elif isinstance(raw, IterableABC):
            values = list(raw)
        else:
            values = [raw]
        for value in values:
            inventory = MediaInventory.from_provider(value, scope=scope)
            if inventory is None:
                continue
            registry_id = id(inventory.registry)
            if registry_id in seen_registry_ids:
                continue
            seen_registry_ids.add(registry_id)
            inventories.append(inventory)
    return inventories


__all__ = [
    "collect_media_inventories",
    "collect_template_registries",
    "collect_token_catalogs",
]
