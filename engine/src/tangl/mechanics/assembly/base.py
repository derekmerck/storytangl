from __future__ import annotations

from collections import defaultdict
from enum import Enum
from inspect import isclass
from numbers import Real
from typing import Any, ClassVar, Generic, Optional, Protocol, TypeVar, cast
from uuid import UUID

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from tangl.core import Entity, Selector
from tangl.type_hints import Tag, UnstructuredData
from .budget import BudgetTracker
from .component import Component, ComponentFacet
from .slot import Slot, SlotGroup

CT = TypeVar("CT", bound=Entity)
FacetComponentT = TypeVar("FacetComponentT", bound=Component)


class HasResourceCost(Protocol):
    """Protocol for components that consume named resources."""

    def get_cost(self, resource: str) -> float:
        ...


class SlottedContainer(BaseModel, Generic[CT]):
    """Generic container that assigns components into named slots.

    Slots declare selector criteria so eligibility is resolved through
    :class:`tangl.core.Selector`. Subclasses define ``slots`` and may enable
    resource tracking via ``tracked_resources``.
    """

    slots: ClassVar[dict[str, Slot]] = {}
    slot_groups: ClassVar[list[SlotGroup]] = []
    tracked_resources: ClassVar[list[str]] = []

    assignments: dict[str, list[CT]] = Field(default_factory=lambda: defaultdict(list))
    budgets: Optional[BudgetTracker] = None
    owner: Any = Field(default=None, exclude=True)

    def _slot_names(self) -> list[str]:
        return list(self.assignments)

    def _slot_components(self, slot_name: str) -> list[CT]:
        return self.assignments.get(slot_name, [])

    def _has_slot_components(self, slot_name: str) -> bool:
        return bool(self._slot_components(slot_name))

    def _slot_count(self, slot_name: str) -> int:
        return len(self._slot_components(slot_name))

    def _add_to_slot(self, slot_name: str, component: CT) -> None:
        self.assignments[slot_name].append(component)

    def _remove_from_slot(self, slot_name: str, component: CT) -> bool:
        if component not in self.assignments.get(slot_name, []):
            return False
        self.assignments[slot_name].remove(component)
        return True

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
            raise ValueError(f"Cannot assign {component.label!r} to {slot_name}: {reason}")

        self._add_to_slot(slot_name, component)

        if self.budgets:
            self.budgets.recalculate(self.all_components())

    def unassign(self, slot_name: str, component: CT) -> None:
        if self._remove_from_slot(slot_name, component):
            if self.budgets:
                self.budgets.recalculate(self.all_components())

    def get_slot(self, slot_name: str) -> list[CT]:
        return self._slot_components(slot_name)

    def all_components(self) -> list[CT]:
        result: list[CT] = []
        for slot_name in self._slot_names():
            result.extend(self._slot_components(slot_name))
        return result

    def component_facets(
        self: "SlottedContainer[FacetComponentT]",
        *,
        channel: str | None = None,
        facet_type: str | None = None,
    ) -> list[ComponentFacet]:
        """Discover matching facets from currently assigned components."""

        facets: list[ComponentFacet] = []
        slot_names = list(self.slots)
        slot_names.extend(name for name in self._slot_names() if name not in self.slots)
        for slot_name in slot_names:
            components = self._slot_components(slot_name)
            for component in components:
                facets.extend(
                    component.component_facets(
                        channel=channel,
                        facet_type=facet_type,
                        subject_id=slot_name,
                    )
                )
        return facets

    def fold_giver_payloads(
        self: "SlottedContainer[FacetComponentT]",
        channel: str,
    ) -> list[object | None]:
        """Return payloads from active ``giver`` facets on one channel."""

        return [
            facet.payload
            for facet in self.component_facets(channel=channel, facet_type="giver")
        ]

    def materialize_defaults(self) -> list[CT]:
        """Opt-in population of enabled empty slots that declare defaults."""

        pending = [
            slot_name
            for slot_name, slot in self.slots.items()
            if slot.default_factory is not None and not self._has_slot_components(slot_name)
        ]
        materialized: list[CT] = []
        while pending:
            progressed = False
            for slot_name in list(pending):
                slot = self.slots[slot_name]
                if self._has_slot_components(slot_name) or not self.is_slot_enabled(slot_name):
                    pending.remove(slot_name)
                    continue
                if any(
                    not self._has_slot_components(prerequisite)
                    for prerequisite in slot.prerequisite_slots
                ):
                    continue

                component = cast(CT, slot.default_factory())
                self.assign(slot_name, component)
                materialized.append(component)
                pending.remove(slot_name)
                progressed = True
            if not progressed:
                break
        return materialized

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
        if not self.is_slot_enabled(slot_name):
            return False, f"Slot disabled: {slot_name}"

        selects, reason = slot.selects_for(component)
        if not selects:
            return False, reason

        missing_prerequisites = [
            prerequisite
            for prerequisite in slot.prerequisite_slots
            if not self._has_slot_components(prerequisite)
        ]
        if missing_prerequisites:
            return False, f"Missing prerequisite slots: {', '.join(missing_prerequisites)}"

        current_count = self._slot_count(slot_name)
        if current_count >= slot.max_count:
            return False, f"Slot full ({current_count}/{slot.max_count})"

        if self.budgets and hasattr(component, "get_cost"):
            for name, budget in self.budgets.budgets.items():
                cost = getattr(component, "get_cost")(name)
                if not budget.can_afford(cost):
                    return False, f"Insufficient {name}: need {cost}, have {budget.available}"

        return True, ""

    def is_slot_enabled(self, slot_name: str) -> bool:
        if slot_name not in self.slots:
            raise KeyError(f"No such slot: {slot_name}")

        slot = self.slots[slot_name]
        if not slot.enablement_criteria:
            return True
        if self.owner is None:
            return False
        return Selector(**slot.enablement_criteria).matches(self.owner)

    def validate(self) -> list[str]:
        errors: list[str] = []

        for slot_name, slot in self.slots.items():
            enabled = self.is_slot_enabled(slot_name)
            if not enabled and self._has_slot_components(slot_name):
                errors.append(f"Disabled slot occupied: {slot_name}")
            if enabled and slot.required and not self._has_slot_components(slot_name):
                errors.append(f"Required slot empty: {slot_name}")
            if enabled and self._has_slot_components(slot_name):
                for prerequisite in slot.prerequisite_slots:
                    if not self._has_slot_components(prerequisite):
                        errors.append(
                            f"Slot '{slot_name}' missing prerequisite slot: {prerequisite}"
                        )

        for group in self.slot_groups:
            total = sum(self._slot_count(name) for name in group.slot_names)
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


class ComponentManager(SlottedContainer[CT]):
    """Owner-bound slotted manager that persists graph-member assignments by UUID."""

    assignment_ids: dict[str, list[UUID]] = Field(default_factory=dict)
    _component_cache: dict[UUID, CT] = PrivateAttr(default_factory=dict)

    def bind_owner(self, owner: Any) -> "ComponentManager[CT]":
        self.owner = owner
        for component_ids in self.assignment_ids.values():
            for component_id in component_ids:
                component = self._component_cache.get(component_id)
                if component is not None:
                    self._validate_component_registry(component)
        return self

    def _slot_names(self) -> list[str]:
        return list(self.assignment_ids)

    def _owner_registry(self):
        if self.owner is None:
            return None
        return getattr(self.owner, "registry", None)

    def _resolve_component(self, component_id: UUID) -> CT:
        registry = self._owner_registry()
        if registry is not None:
            component = registry.get(component_id)
            if component is not None:
                return cast(CT, component)
        if component_id in self._component_cache:
            return self._component_cache[component_id]
        raise KeyError(f"Component {component_id} is not available through the owner registry")

    def _slot_components(self, slot_name: str) -> list[CT]:
        return [
            self._resolve_component(component_id)
            for component_id in self.assignment_ids.get(slot_name, [])
        ]

    def _has_slot_components(self, slot_name: str) -> bool:
        return bool(self.assignment_ids.get(slot_name))

    def _slot_count(self, slot_name: str) -> int:
        return len(self.assignment_ids.get(slot_name, []))

    def _validate_component_registry(self, component: CT) -> None:
        registry = self._owner_registry()
        if registry is None:
            return
        component_registry = getattr(component, "registry", None)
        registered_component = registry.get(component.uid)
        if component_registry is None:
            if registered_component is not None and registered_component is not component:
                raise ValueError("Assigned component UID is already registered to another item")
            registry.add(component)
            return
        if component_registry is not registry:
            raise ValueError("Assigned component must belong to the owner's registry")
        if registered_component is None:
            registry.add(component)
            return
        if registered_component is not component:
            raise ValueError("Assigned component UID is already registered to another item")

    def _add_to_slot(self, slot_name: str, component: CT) -> None:
        self._validate_component_registry(component)
        self.assignment_ids.setdefault(slot_name, []).append(component.uid)
        self._component_cache[component.uid] = component

    def _remove_from_slot(self, slot_name: str, component: CT) -> bool:
        component_ids = self.assignment_ids.get(slot_name)
        if not component_ids or component.uid not in component_ids:
            return False
        component_ids.remove(component.uid)
        if not component_ids:
            self.assignment_ids.pop(slot_name, None)
        if not any(component.uid in ids for ids in self.assignment_ids.values()):
            self._component_cache.pop(component.uid, None)
        return True

    def unstructure(self) -> UnstructuredData:
        data: UnstructuredData = {"kind": self.__class__}
        if self.assignment_ids:
            data["assignment_ids"] = self.assignment_ids
        if self.budgets is not None:
            data["budgets"] = self.budgets.model_dump(exclude_defaults=True)
        return data

    @classmethod
    def structure(cls, data: UnstructuredData, _ctx: Any = None) -> "ComponentManager[CT]":
        _ = _ctx
        payload = dict(data)
        cls_ = payload.pop("kind", cls)
        if not isclass(cls_) or not issubclass(cls_, cls):
            raise TypeError(f"Expected a subclass of {cls.__name__}, got {cls_!r}")
        return cls_(**payload)


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
