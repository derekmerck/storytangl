from __future__ import annotations

from collections import defaultdict
from enum import Enum
from numbers import Real
from typing import Any, ClassVar, Generic, Optional, Protocol, TypeVar

from pydantic import BaseModel, Field, model_validator

from tangl.core import Entity
from tangl.type_hints import Tag
from .budget import BudgetTracker
from .slot import Slot, SlotGroup

CT = TypeVar("CT", bound=Entity)


class HasResourceCost(Protocol):
    """Protocol for components that consume named resources."""

    def get_cost(self, resource: str) -> float:
        ...


class SlottedContainer(BaseModel, Generic[CT]):
    """Generic container that assigns components into named slots.

    Slots declare selection criteria that mirror :meth:`Entity.matches` so that eligibility is
    resolved by the components themselves. Subclasses define ``slots`` and may enable resource
    tracking via ``tracked_resources``.
    """

    slots: ClassVar[dict[str, Slot]] = {}
    slot_groups: ClassVar[list[SlotGroup]] = []
    tracked_resources: ClassVar[list[str]] = []

    assignments: dict[str, list[CT]] = Field(default_factory=lambda: defaultdict(list))
    budgets: Optional[BudgetTracker] = None
    owner: Any = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _initialize_budgets(self) -> "SlottedContainer[CT]":
        if self.tracked_resources and not self.budgets:
            self.budgets = BudgetTracker()
            for resource in self.tracked_resources:
                capacity = None
                if self.owner:
                    capacity = getattr(self.owner, f"max_{resource}", None)
                if capacity is not None:
                    self.budgets.add_budget(resource, capacity)
        return self

    def assign(self, slot_name: str, component: CT) -> None:
        can_assign, reason = self.can_assign(slot_name, component)
        if not can_assign:
            raise ValueError(f"Cannot assign {getattr(component, 'label', component)!r} to {slot_name}: {reason}")

        self.assignments[slot_name].append(component)

        if self.budgets:
            self.budgets.recalculate(self.all_components())

    def unassign(self, slot_name: str, component: CT) -> None:
        if slot_name not in self.assignments:
            return

        if component in self.assignments[slot_name]:
            self.assignments[slot_name].remove(component)
            if self.budgets:
                self.budgets.recalculate(self.all_components())

    def get_slot(self, slot_name: str) -> list[CT]:
        return self.assignments.get(slot_name, [])

    def all_components(self) -> list[CT]:
        result: list[CT] = []
        for components in self.assignments.values():
            result.extend(components)
        return result

    def get_aggregate(self, name: str, default: float = 0.0) -> float:
        """Sum one direct numeric attribute across assigned components.

        Aggregates operate over :meth:`all_components` exactly as returned by
        the container. Missing or ``None`` values contribute nothing.
        """

        total = float(default)
        for component in self.all_components():
            value = getattr(component, name, None)
            if value is None:
                continue
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(
                    f"Aggregate '{name}' expected numeric values, got {type(value).__name__}"
                )
            total += float(value)
        return total

    def get_aggregate_cost(self, name: str, default: float = 0.0) -> float:
        """Sum one named resource cost across assigned components.

        Aggregates operate over :meth:`all_components` exactly as returned by
        the container. Components without ``get_cost`` contribute nothing.
        """

        total = float(default)
        for component in self.all_components():
            if not hasattr(component, "get_cost"):
                continue
            value = getattr(component, "get_cost")(name)
            if value is None:
                continue
            if not isinstance(value, Real) or isinstance(value, bool):
                raise TypeError(
                    f"Aggregate cost '{name}' expected numeric values, got {type(value).__name__}"
                )
            total += float(value)
        return total

    @staticmethod
    def _is_tag_value(value: object) -> bool:
        return isinstance(value, (Enum, str, int))

    def get_aggregate_tags(self, name: str = "tags") -> set[Tag]:
        """Union one tag or tag collection attribute across assigned components.

        Aggregates operate over :meth:`all_components` exactly as returned by
        the container. Missing or ``None`` values contribute nothing.
        """

        tags: set[Tag] = set()
        for component in self.all_components():
            value = getattr(component, name, None)
            if value is None:
                continue
            if self._is_tag_value(value):
                tags.add(value)
                continue
            if not isinstance(value, (list, tuple, set, frozenset)):
                raise TypeError(
                    f"Aggregate tags '{name}' expected a tag or tag collection, got {type(value).__name__}"
                )
            for item in value:
                if not self._is_tag_value(item):
                    raise TypeError(
                        f"Aggregate tags '{name}' expected Tag entries, got {type(item).__name__}"
                    )
                tags.add(item)
        return tags

    def can_assign(self, slot_name: str, component: CT) -> tuple[bool, str]:
        if slot_name not in self.slots:
            return False, f"No such slot: {slot_name}"

        slot = self.slots[slot_name]
        selects, reason = slot.selects_for(component)
        if not selects:
            return False, reason

        current_count = len(self.assignments.get(slot_name, []))
        if current_count >= slot.max_count:
            return False, f"Slot full ({current_count}/{slot.max_count})"

        if self.budgets and hasattr(component, "get_cost"):
            for name, budget in self.budgets.budgets.items():
                cost = getattr(component, "get_cost")(name)
                if not budget.can_afford(cost):
                    return False, f"Insufficient {name}: need {cost}, have {budget.available}"

        return True, ""

    def validate(self) -> list[str]:
        errors: list[str] = []

        for slot_name, slot in self.slots.items():
            if slot.required and not self.assignments.get(slot_name):
                errors.append(f"Required slot empty: {slot_name}")

        for group in self.slot_groups:
            total = sum(len(self.assignments.get(name, [])) for name in group.slot_names)
            if group.min_total is not None and total < group.min_total:
                errors.append(f"Group '{group.name}': {total} < {group.min_total} (min)")
            if group.max_total is not None and total > group.max_total:
                errors.append(f"Group '{group.name}': {total} > {group.max_total} (max)")

        if self.budgets:
            errors.extend(self.budgets.get_errors())

        errors.extend(self._validate_custom())
        return errors

    def _validate_custom(self) -> list[str]:
        return []

    @property
    def is_valid(self) -> bool:
        return len(self.validate()) == 0


class HasSlottedContainer:
    """Mixin for entities that own a :class:`SlottedContainer`.

    Place the mixin *before* Pydantic models in the inheritance list so its
    serialization helpers run (e.g., ``class Vehicle(HasSlottedContainer, Node)``).
    """

    _container_class: ClassVar[type[SlottedContainer]] = SlottedContainer
    _container: Optional[SlottedContainer] = None

    @property
    def loadout(self) -> SlottedContainer:
        if self._container is None:
            self._container = self._container_class(owner=self)
        return self._container

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        data = super().model_dump(**kwargs)  # type: ignore[misc]
        if self._container:
            data["_container"] = self._container.model_dump()
        return data

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any):  # type: ignore[override]
        instance = super().model_validate(obj, **kwargs)  # type: ignore[misc]
        if "_container" in obj:
            instance._container = instance._container_class.model_validate(obj["_container"])
            instance._container.owner = instance
        return instance
