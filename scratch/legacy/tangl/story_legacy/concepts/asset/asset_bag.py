"""Discrete asset bag helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Optional, Type

if TYPE_CHECKING:  # pragma: no cover - used for static analysis only
    from tangl.core import Node
    from tangl.vm.context import Context
    from .discrete_asset import DiscreteAsset


class AssetBag:
    """Maintain discrete asset nodes for a single owner.

    Why
    ====
    Provide a lightweight inventory for nodes that track individual asset
    instances, enforcing optional limits without introducing slot logic or
    dispatch dependencies.

    Key Features
    ------------
    * **Capacity checks** – optional maximum count and weight constraints.
    * **Graph-friendly** – ensures items belong to the same graph as the owner.
    * **State updates** – writes back ``owner_id`` on add/remove operations.

    API
    ===
    ``items``
        Snapshot of discrete asset nodes currently tracked.
    ``add`` / ``remove``
        Validate membership transitions, updating ownership metadata.
    ``validate``
        Audit the bag for overflow/overweight conditions.
    """

    def __init__(
        self,
        owner: Node,
        *,
        max_items: Optional[int] = None,
        max_weight: Optional[float] = None,
    ) -> None:
        self.owner = owner
        self.max_items = max_items
        self.max_weight = max_weight
        self._items: list[DiscreteAsset] = []

    # ==================
    # Collection Access
    # ==================

    @property
    def items(self) -> list[DiscreteAsset]:
        """Return a snapshot of tracked items."""
        return list(self._items)

    def items_of_type(self, asset_type: Type[DiscreteAsset]) -> list[DiscreteAsset]:
        """Return items that are instances of ``asset_type``."""
        return [item for item in self._items if isinstance(item, asset_type)]

    def get_item(self, label: str) -> Optional[DiscreteAsset]:
        """Locate an item by its label (first match wins)."""
        for item in self._items:
            if item.label == label:
                return item
        return None

    def contains(self, label: str) -> bool:
        """Return ``True`` when an item with ``label`` is present."""
        return self.get_item(label) is not None

    def count(self) -> int:
        """Return the number of items in the bag."""
        return len(self._items)

    def total_weight(self) -> float:
        """Total weight across all items."""
        return sum(self._weight_for(item) for item in self._items)

    # ==================
    # Validation
    # ==================

    def can_accept(self, item: DiscreteAsset) -> tuple[bool, list[str]]:
        """Check whether ``item`` may be added."""
        errors: list[str] = []

        if self._find_index(item) is not None:
            errors.append(f"Item {item.label!r} already in bag")

        if item.graph is None:
            errors.append("Item is not attached to a graph")
        elif self.owner.graph is not None and item.graph is not self.owner.graph:
            errors.append("Item belongs to a different graph")

        if item.owner_id is not None and item.owner_id != self.owner.uid:
            errors.append(f"Item already owned by {item.owner_id}")

        if self.max_items is not None and self.count() >= self.max_items:
            errors.append(f"Bag full ({self.max_items} items)")

        if self.max_weight is not None:
            projected = self.total_weight() + self._weight_for(item)
            if projected > self.max_weight:
                errors.append(
                    f"Too heavy: {projected:.1f} > {self.max_weight:.1f}"
                )

        return (not errors, errors)

    def can_remove(self, item: DiscreteAsset) -> tuple[bool, list[str]]:
        """Check whether ``item`` may be removed."""
        if self._find_index(item) is None:
            return False, [f"Item {item.label!r} not in bag"]
        return True, []

    def validate(self) -> list[str]:
        """Audit current capacity limits and ownership invariants."""
        errors: list[str] = []

        if self.max_items is not None and self.count() > self.max_items:
            errors.append(
                f"Too many items: {self.count()} > {self.max_items}"
            )

        if self.max_weight is not None:
            total = self.total_weight()
            if total > self.max_weight:
                errors.append(
                    f"Overweight: {total:.1f} > {self.max_weight:.1f}"
                )

        if self.owner.graph is not None:
            for item in self._items:
                if item.graph is not self.owner.graph:
                    errors.append(
                        f"Item {item.label!r} belongs to a different graph"
                    )
        for item in self._items:
            if item.owner_id not in (None, self.owner.uid):
                errors.append(
                    f"Item {item.label!r} owned by {item.owner_id}"
                )

        return errors

    # ==================
    # Mutation API
    # ==================

    def add(self, item: DiscreteAsset, *, ctx: Optional[Context] = None) -> None:
        """Add ``item`` to the bag, enforcing capacity constraints."""
        can_add, errors = self.can_accept(item)
        if not can_add:
            raise ValueError(f"Cannot add item: {', '.join(errors)}")

        self._items.append(item)
        item.owner_id = self.owner.uid
        # ``ctx`` reserved for future dispatch integration.

    def remove(self, item: DiscreteAsset, *, ctx: Optional[Context] = None) -> None:
        """Remove ``item`` from the bag."""
        can_remove, errors = self.can_remove(item)
        if not can_remove:
            raise ValueError(f"Cannot remove item: {', '.join(errors)}")

        index = self._find_index(item)
        if index is not None:
            self._items.pop(index)
        item.owner_id = None
        # ``ctx`` reserved for future dispatch integration.

    def clear(self) -> None:
        """Remove all items from the bag."""
        for item in list(self._items):
            self.remove(item)

    # ==================
    # Description
    # ==================

    def describe(self) -> str:
        """Return a human-readable summary of the bag contents."""
        if not self._items:
            return "empty bag"

        parts = [
            f"{self.count()} item{'s' if self.count() != 1 else ''}"
        ]
        if self.max_items is not None:
            parts.append(f"max {self.max_items}")
        if self.max_weight is not None:
            parts.append(
                f"{self.total_weight():.1f}/{self.max_weight:.1f} lbs"
            )
        return ", ".join(parts)

    # ==================
    # Internal helpers
    # ==================

    def _find_index(self, item: DiscreteAsset) -> Optional[int]:
        for index, existing in enumerate(self._items):
            if existing.uid == item.uid:
                return index
        return None

    @staticmethod
    def _weight_for(item: DiscreteAsset) -> float:
        weight = getattr(item, "weight", 0.0)
        if weight is None:
            return 0.0
        return float(weight)


class HasAssetBag:
    """Mixin that lazily provisions an :class:`AssetBag`."""

    _bag: Optional[AssetBag] = None
    _bag_max_items: ClassVar[Optional[int]] = None
    _bag_max_weight: ClassVar[Optional[float]] = None

    @property
    def bag(self) -> AssetBag:
        """Return (and create if needed) the asset bag for this node."""
        bag = getattr(self, "_bag", None)
        if bag is None:
            max_items = getattr(type(self), "_bag_max_items", None)
            max_weight = getattr(type(self), "_bag_max_weight", None)
            bag = AssetBag(self, max_items=max_items, max_weight=max_weight)
            setattr(self, "_bag", bag)
        return bag
