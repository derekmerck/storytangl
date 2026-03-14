from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterator

from tangl.core import Selector

from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from .media_resource_registry import MediaResourceRegistry


@dataclass(frozen=True)
class MediaInventory:
    """Provisioner-facing adapter over one media registry."""

    registry: Any
    scope: str = "world"
    label: str = "media_inventory"

    @property
    def identity(self) -> tuple[int, str]:
        return id(self.registry), self.scope

    @classmethod
    def from_provider(
        cls,
        value: Any,
        *,
        scope: str | None = None,
        label: str | None = None,
    ) -> "MediaInventory" | None:
        if value is None:
            return None
        if isinstance(value, cls):
            return value

        registry: Any = None
        if isinstance(value, MediaResourceRegistry):
            registry = value
        else:
            nested = getattr(value, "registry", None)
            if isinstance(nested, MediaResourceRegistry):
                registry = nested
            elif callable(getattr(value, "find_all", None)):
                registry = value
        if registry is None and callable(getattr(value, "find_all", None)):
            registry = value

        if registry is None:
            return None

        resolved_scope = (
            scope
            or getattr(value, "scope", None)
            or getattr(registry, "scope", None)
            or "world"
        )
        resolved_label = (
            label
            or getattr(value, "label", None)
            or getattr(registry, "label", None)
            or f"{resolved_scope}_media"
        )
        return cls(
            registry=registry,
            scope=str(resolved_scope),
            label=str(resolved_label),
        )

    def find_all(
        self,
        selector: Selector | None = None,
        sort_key: Callable[[MediaRIT], Any] | None = None,
    ) -> Iterator[MediaRIT]:
        return self.registry.find_all(selector=selector, sort_key=sort_key)

    @classmethod
    def chain_find_all(
        cls,
        *inventories: "MediaInventory",
        selector: Selector | None = None,
        sort_key: Callable[[MediaRIT], Any] | None = None,
    ) -> Iterator[MediaRIT]:
        for inventory in inventories:
            yield from inventory.find_all(selector=selector, sort_key=sort_key)
