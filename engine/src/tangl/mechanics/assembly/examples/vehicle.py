from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import Field, model_validator

from tangl.core import Node, Singleton, Token, contribute_ns
from tangl.lang.helpers import oxford_join
from tangl.mechanics.assembly import ComponentManager, Slot


class VehiclePartType(Enum):
    """Named vehicle loadout slots for the neutral vehicle example."""

    CHASSIS = "chassis"
    POWERPLANT = "powerplant"
    SUSPENSION = "suspension"
    TIRES = "tires"


class VehicleComponentType(Singleton):
    """Vehicle component definition used by graph-local vehicle part tokens."""

    part_type: VehiclePartType
    weight_cost: float = 0.0
    price_cost: float = 0.0
    power_draw: float = 0.0
    power_output: float = 0.0
    max_weight: float | None = None

    damage: int = Field(0, json_schema_extra={"instance_var": True})

    def get_cost(self, resource: str) -> float:
        if resource == "price":
            return self.price_cost
        if resource == "power":
            return self.power_draw
        return getattr(self, f"{resource}_cost", 0.0)


class VehicleComponentToken(Token):
    """Vehicle part token whose label-like display is the referenced part type."""

    def get_label(self) -> str:
        return self.token_from or self.label


VehicleComponent = VehicleComponentToken._create_wrapper_cls(
    VehicleComponentType,
    "VehicleComponent",
)


def _part(part_type: VehiclePartType):
    return lambda component: getattr(component, "part_type", None) is part_type


def _part_name(component: VehicleComponent) -> str:
    return (component.token_from or component.label).replace("_", " ")


def _install_component_types() -> None:
    if VehicleComponentType.has_instance("mini_chassis"):
        return
    VehicleComponentType(
        label="mini_chassis",
        part_type=VehiclePartType.CHASSIS,
        weight_cost=500,
        price_cost=500,
        max_weight=900,
    )
    VehicleComponentType(
        label="mid_chassis",
        part_type=VehiclePartType.CHASSIS,
        weight_cost=800,
        price_cost=1000,
        max_weight=1400,
    )
    VehicleComponentType(
        label="truck_chassis",
        part_type=VehiclePartType.CHASSIS,
        weight_cost=1400,
        price_cost=1600,
        max_weight=2500,
    )
    VehicleComponentType(
        label="cheap_powerplant",
        part_type=VehiclePartType.POWERPLANT,
        weight_cost=200,
        price_cost=400,
        power_output=45,
    )
    VehicleComponentType(
        label="big_powerplant",
        part_type=VehiclePartType.POWERPLANT,
        weight_cost=450,
        price_cost=1200,
        power_output=120,
    )
    VehicleComponentType(
        label="cheap_tires",
        part_type=VehiclePartType.TIRES,
        weight_cost=80,
        price_cost=100,
    )
    VehicleComponentType(
        label="slicks",
        part_type=VehiclePartType.TIRES,
        weight_cost=90,
        price_cost=350,
    )
    VehicleComponentType(
        label="all_terrain",
        part_type=VehiclePartType.TIRES,
        weight_cost=150,
        price_cost=450,
    )
    VehicleComponentType(
        label="cheap_suspension",
        part_type=VehiclePartType.SUSPENSION,
        weight_cost=100,
        price_cost=200,
    )
    VehicleComponentType(
        label="off_road_suspension",
        part_type=VehiclePartType.SUSPENSION,
        weight_cost=220,
        price_cost=600,
    )
    VehicleComponentType(
        label="racing_suspension",
        part_type=VehiclePartType.SUSPENSION,
        weight_cost=180,
        price_cost=700,
    )


_install_component_types()


class VehicleLoadout(ComponentManager[VehicleComponent]):
    """Owner-bound single-slot manager for a neutral vehicle configuration."""

    slots: ClassVar[dict[str, Slot]] = {
        "chassis": Slot.for_predicate(
            "chassis",
            _part(VehiclePartType.CHASSIS),
            required=True,
        ),
        "powerplant": Slot.for_predicate(
            "powerplant",
            _part(VehiclePartType.POWERPLANT),
            required=True,
        ),
        "suspension": Slot.for_predicate(
            "suspension",
            _part(VehiclePartType.SUSPENSION),
            required=True,
        ),
        "tires": Slot.for_predicate(
            "tires",
            _part(VehiclePartType.TIRES),
            required=True,
        ),
    }

    def assign(self, slot_name: str, component: VehicleComponent) -> None:
        slot = self.slots[slot_name]
        replaced = []
        if slot.max_count == 1 and self._has_slot_components(slot_name):
            replaced = list(self.get_slot(slot_name))
            for old_component in replaced:
                self._remove_from_slot(slot_name, old_component)

        try:
            super().assign(slot_name, component)
        except Exception:
            for old_component in replaced:
                self._add_to_slot(slot_name, old_component)
            if self.budgets:
                self.budgets.recalculate(self.all_components())
            raise

    def total_weight(self) -> float:
        return self.get_aggregate_cost("weight")

    def total_price(self) -> float:
        return self.get_aggregate_cost("price")

    def _single(self, slot_name: str) -> VehicleComponent | None:
        components = self.get_slot(slot_name)
        return components[0] if components else None

    def describe_items(self) -> list[str]:
        """Return concise slot/component labels for prose or prompt adapters."""
        items: list[str] = []
        for slot_name in self.slots:
            component = self._single(slot_name)
            if component is not None:
                items.append(f"{slot_name}: {_part_name(component)}")
        return items

    def describe_warnings(self) -> list[str]:
        """Return concise loadout warning phrases derived from validation errors."""
        warnings: list[str] = []
        for error in self.validate():
            if error.startswith("Required slot empty: "):
                slot_name = error.removeprefix("Required slot empty: ")
                warnings.append(f"missing {slot_name}")
            elif error.startswith("Powerplant output too low: "):
                warnings.append("powerplant output is too low")
            elif error.startswith("Weight exceeds chassis capacity: "):
                warnings.append("weight exceeds chassis capacity")
            elif error.startswith("Price exceeds budget: "):
                warnings.append("price exceeds budget")
            else:
                warnings.append(error[:1].lower() + error[1:])
        return warnings

    def describe(self) -> str:
        """Return a compact procedural description of the vehicle loadout."""
        chassis = self._single("chassis")
        powerplant = self._single("powerplant")
        suspension = self._single("suspension")
        tires = self._single("tires")

        if not any((chassis, powerplant, suspension, tires)):
            description = "an unconfigured vehicle"
            warnings = self.describe_warnings()
            if warnings:
                return f"{description}. Warning: {oxford_join(warnings)}."
            return description

        parts: list[str] = []
        if chassis is not None:
            parts.append(f"built on a {_part_name(chassis)}")
        if powerplant is not None:
            parts.append(f"powered by a {_part_name(powerplant)}")
        if suspension is not None:
            parts.append(f"riding on {_part_name(suspension)}")
        if tires is not None:
            parts.append(f"with {_part_name(tires)}")

        summary = oxford_join(parts)
        description = f"a vehicle {summary}"
        warnings = self.describe_warnings()
        if warnings:
            return f"{description}. Warning: {oxford_join(warnings)}."
        return description

    def _validate_custom(self) -> list[str]:
        errors: list[str] = []

        chassis = self._single("chassis")
        powerplant = self._single("powerplant")
        total_weight = self.total_weight()
        total_price = self.total_price()

        if chassis is not None and chassis.max_weight is not None:
            if total_weight > chassis.max_weight:
                errors.append(
                    f"Weight exceeds chassis capacity: {total_weight:.1f} > {chassis.max_weight:.1f}"
                )

        if powerplant is not None:
            owner = self.owner
            heavy_threshold = getattr(owner, "heavy_weight_threshold", 1200.0)
            required_power = (
                getattr(owner, "heavy_power_required", 90.0)
                if total_weight > heavy_threshold
                else getattr(owner, "light_power_required", 40.0)
            )
            if powerplant.power_output < required_power:
                errors.append(
                    "Powerplant output too low: "
                    f"{powerplant.power_output:.1f} < {required_power:.1f}"
                )

        owner = self.owner
        max_price = getattr(owner, "max_price", None)
        if max_price is not None and total_price > max_price:
            errors.append(f"Price exceeds budget: {total_price:.1f} > {max_price:.1f}")

        return errors


class Vehicle(Node):
    """Vehicle graph member with an embedded owner-bound loadout manager."""

    max_price: float = 5000.0
    heavy_weight_threshold: float = 1200.0
    light_power_required: float = 40.0
    heavy_power_required: float = 90.0
    loadout: VehicleLoadout = Field(
        default_factory=VehicleLoadout,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @model_validator(mode="after")
    def _bind_loadout_owner(self) -> "Vehicle":
        self.loadout.bind_owner(self)
        return self

    @property
    def vehicle_loadout(self) -> VehicleLoadout:
        return self.loadout

    def describe_vehicle(self) -> str:
        """Return a compact procedural description of this vehicle."""
        return self.loadout.describe()

    @contribute_ns
    def provide_vehicle_symbols(self) -> dict[str, object]:
        """Publish vehicle loadout symbols into the entity-local namespace."""
        return {
            "vehicle_loadout": self.loadout,
            "vehicle_description": self.describe_vehicle(),
            "vehicle_component_tokens": self.loadout.describe_items(),
        }


__all__ = [
    "Vehicle",
    "VehicleComponent",
    "VehicleComponentToken",
    "VehicleComponentType",
    "VehicleLoadout",
    "VehiclePartType",
]
