from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from tangl.core import Node
from tangl.mechanics.assembly import HasResourceCost, HasSlottedContainer, Slot, SlottedContainer


class VehicleComponent(Node, HasResourceCost):
    """Base class for vehicle parts used in :class:`VehicleLoadout`."""

    power_cost: float = 0.0
    weight_cost: float = 0.0

    def get_cost(self, resource: str) -> float:
        return getattr(self, f"{resource}_cost", 0.0)


class VehicleLoadout(SlottedContainer[VehicleComponent]):
    """Slot definitions and validation for a vehicle configuration."""

    slots: ClassVar[dict[str, Slot]] = {
        "chassis": Slot.for_tags("chassis", tags={"chassis"}, required=True),
        "powerplant": Slot.for_tags("powerplant", tags={"powerplant"}, required=True),
        "weapon_front": Slot.for_tags("weapon_front", tags={"weapon"}, max_count=2),
        "weapon_rear": Slot.for_tags("weapon_rear", tags={"weapon"}, max_count=2),
        "weapon_turret": Slot(
            name="weapon_turret",
            selection_criteria={
                "has_tags": {"weapon"},
                "predicate": lambda weapon: not weapon.has_tags({"melee"}),
            },
            max_count=1,
        ),
        "gadget": Slot.for_tags("gadget", tags={"gadget"}, max_count=5),
    }

    tracked_resources: ClassVar[list[str]] = ["power", "weight"]

    def _validate_custom(self) -> list[str]:
        errors: list[str] = []

        chassis_list = self.get_slot("chassis")
        if chassis_list and self.budgets:
            chassis = chassis_list[0]
            max_weight = getattr(chassis, "max_weight", None)
            weight_budget = self.budgets.budgets.get("weight") if self.budgets else None
            if max_weight is not None and weight_budget and weight_budget.consumed > max_weight:
                errors.append(
                    f"Weight exceeds chassis capacity: {weight_budget.consumed:.1f} > {max_weight}"
                )

        powerplant_list = self.get_slot("powerplant")
        if powerplant_list and self.budgets:
            powerplant = powerplant_list[0]
            max_power = getattr(powerplant, "max_power_output", None)
            power_budget = self.budgets.budgets.get("power") if self.budgets else None
            if max_power is not None and power_budget and power_budget.consumed > max_power:
                errors.append(
                    f"Power exceeds powerplant capacity: {power_budget.consumed:.1f} > {max_power}"
                )

        return errors


class Vehicle(HasSlottedContainer, Node):
    """Vehicle entity with an attached :class:`VehicleLoadout`."""

    _container_class: ClassVar[type[SlottedContainer]] = VehicleLoadout

    max_power: float = Field(100.0, description="Power budget available to the loadout.")
    max_weight: float = Field(1000.0, description="Weight budget available to the loadout.")

    @property
    def vehicle_loadout(self) -> VehicleLoadout:
        return self.loadout  # type: ignore[return-value]
