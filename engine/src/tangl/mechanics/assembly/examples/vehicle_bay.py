from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import ClassVar

from pydantic import Field

from tangl.core import Entity, Registry
from tangl.core.bases import BaseModelPlus
from tangl.mechanics.assembly import ComponentManager
from tangl.mechanics.transaction import (
    AssetMoveCommitment,
    CatalogAssetCommitment,
    ComponentAssignmentCommitment,
    TransactionCheck,
    TransactionOffer,
    ValueDeltaCommitment,
)

from .vehicle import Vehicle, VehicleComponent

SERVICE_TIME_MINUTES = 30
INSTALL_TIME_MINUTES = 60


class VehiclePartInventory(BaseModelPlus):
    """Holder-map inventory for neutral vehicle component examples."""

    guard_unstructure: ClassVar[bool] = True

    items: dict[str, VehicleComponent] = Field(default_factory=dict)

    def _item_key(self, item: VehicleComponent, label: str | None = None) -> str:
        key = label or item.get_label() or item.token_from
        if not key:
            raise ValueError("Vehicle inventory item requires a label")
        return key

    def get_asset(self, label: str) -> VehicleComponent | None:
        if label in self.items:
            return self.items[label]
        for item in self.items.values():
            if label == item.get_label() or label == item.token_from:
                return item
        return None

    def get_asset_key(self, asset: Entity | str) -> str | None:
        resolved = self.get_asset(asset) if isinstance(asset, str) else asset
        if resolved is None:
            return None
        for label, item in self.items.items():
            if item is resolved:
                return label
        return None

    def can_give_asset(
        self,
        asset: Entity,
        receiver: object | None = None,
    ) -> bool:
        _ = receiver
        return isinstance(asset, VehicleComponent) and self.has_asset(asset)

    def can_receive_asset(
        self,
        asset: Entity,
        giver: object | None = None,
    ) -> bool:
        _ = giver
        return isinstance(asset, VehicleComponent)

    def add_asset(self, asset: Entity, *, label: str | None = None) -> None:
        if not isinstance(asset, VehicleComponent):
            raise TypeError("Vehicle inventory accepts only VehicleComponent tokens")
        self.items[self._item_key(asset, label)] = asset

    def remove_asset(self, asset: Entity | str) -> VehicleComponent:
        if isinstance(asset, str):
            resolved = self.get_asset(asset)
            if resolved is None:
                raise KeyError(asset)
            asset = resolved
        for label, item in list(self.items.items()):
            if item is asset:
                return self.items.pop(label)
        key = asset.get_label() or repr(asset)
        raise KeyError(f"Unknown vehicle inventory item: {key}")

    def has_asset(self, asset: Entity | str) -> bool:
        if isinstance(asset, str):
            return self.get_asset(asset) is not None
        return any(item is asset for item in self.items.values())

    def all_items(self) -> list[VehicleComponent]:
        return list(self.items.values())


class VehicleBay(BaseModelPlus):
    """Neutral vehicle service/shop state used by transaction examples."""

    guard_unstructure: ClassVar[bool] = True

    vehicle: Vehicle = Field(default_factory=Vehicle)
    cash: int = 1000
    time_minutes: int = 0
    inventory: VehiclePartInventory = Field(default_factory=VehiclePartInventory)


def component(label: str) -> VehicleComponent:
    return VehicleComponent(token_from=label, label=label)


def value_field_commitment(
    obj: object,
    field_name: str,
    delta: int,
    *,
    label: str,
    detail_label: str | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
) -> ValueDeltaCommitment:
    """Build a typed scalar field mutation commitment."""

    def get_value() -> int:
        return int(getattr(obj, field_name))

    def set_value(value: int | float) -> None:
        setattr(obj, field_name, int(value))

    return ValueDeltaCommitment(
        get_value=get_value,
        set_value=set_value,
        delta=delta,
        label=label,
        detail_label=detail_label or field_name,
        min_value=min_value,
        max_value=max_value,
        planning_key=_value_planning_key(obj, field_name),
    )


def build_service_offer(
    bay: VehicleBay,
    *,
    target: object,
    field_name: str,
    delta: int,
    cash_cost: int = 0,
    time_minutes: int = SERVICE_TIME_MINUTES,
    label: str = "service vehicle",
    value_label: str | None = None,
    min_value: int | None = 0,
    max_value: int | None = None,
    extra_commitments: Iterable[object] = (),
) -> TransactionOffer:
    """Build a service transaction over cash, time, and one scalar state field."""

    commitments: list[object] = []
    commitments.extend(_cost_commitments(bay, cash_cost=cash_cost, time_minutes=time_minutes))
    commitments.append(
        value_field_commitment(
            target,
            field_name,
            delta,
            label=value_label or label,
            min_value=min_value,
            max_value=max_value,
        ),
    )
    commitments.extend(extra_commitments)
    return TransactionOffer(label=label, commitments=commitments)


def build_inventory_install_offer(
    bay: VehicleBay,
    *,
    component_key: str,
    slot_name: str,
    price: int = 0,
    install_time: int = INSTALL_TIME_MINUTES,
    extra_commitments: Iterable[object] = (),
) -> TransactionOffer:
    """Build a transaction that installs one already-held inventory component."""

    installed = VehiclePartInventory()
    part = bay.inventory.get_asset(component_key)
    if part is None:
        raise ValueError(f"Vehicle inventory item not found: {component_key}")
    commitments: list[object] = []
    commitments.extend(_cost_commitments(bay, cash_cost=price, time_minutes=install_time))
    commitments.extend(
        [
            AssetMoveCommitment(
                bay.inventory,
                installed,
                part,
                label="remove selected part from inventory",
            ),
            ComponentAssignmentCommitment(
                bay.vehicle.loadout,
                slot_name,
                part,
                label="assign vehicle part",
                allow_replace=True,
                validate_after=True,
            ),
        ],
    )
    commitments.extend(extra_commitments)
    return TransactionOffer(label=f"install {part.get_label()}", commitments=commitments)


def build_catalog_purchase_offer(
    bay: VehicleBay,
    *,
    label: str,
    price: int,
    supplier: Callable[[], VehicleComponent] | None = None,
    registry: Registry | None = None,
    stock: Mapping[str, int] | None = None,
) -> TransactionOffer:
    """Build a transaction that buys one catalog component into inventory."""

    can_create = None
    if stock is not None:

        def can_create() -> TransactionCheck:
            if stock.get(label, 0) <= 0:
                return TransactionCheck.reject("catalog item unavailable")
            return TransactionCheck.accept()

    return TransactionOffer(
        label=f"buy {label}",
        commitments=[
            *_cost_commitments(bay, cash_cost=price, time_minutes=0),
            CatalogAssetCommitment(
                bay.inventory,
                supplier or (lambda: component(label)),
                registry=registry,
                receiver_label=label,
                can_create=can_create,
            ),
        ],
    )


@dataclass
class CatalogInstallCommitment:
    """Create a catalog component and install it in one committed writeback."""

    manager: ComponentManager[VehicleComponent]
    slot_name: str
    supplier: Callable[[], VehicleComponent]
    preview: VehicleComponent
    label: str = "catalog install"
    allow_replace: bool = True
    validate_after: bool = True
    _assignment: ComponentAssignmentCommitment | None = field(default=None, init=False)

    def can_commit(self) -> TransactionCheck:
        return ComponentAssignmentCommitment(
            self.manager,
            self.slot_name,
            self.preview,
            label=self.label,
            allow_replace=self.allow_replace,
            validate_after=self.validate_after,
        ).can_commit()

    def commit(self) -> Mapping[str, object]:
        check = self.can_commit()
        if not check.accepted:
            raise ValueError(check.reason or "catalog install rejected")
        item = self.supplier()
        assignment = ComponentAssignmentCommitment(
            self.manager,
            self.slot_name,
            item,
            label=self.label,
            allow_replace=self.allow_replace,
            validate_after=self.validate_after,
        )
        self._assignment = assignment
        detail = assignment.commit()
        return {"kind": "catalog_install", **detail}

    def rollback(self) -> None:
        if self._assignment is None:
            return
        self._assignment.rollback()
        self._assignment = None


def build_catalog_install_offer(
    bay: VehicleBay,
    *,
    label: str,
    slot_name: str,
    price: int,
    install_time: int = INSTALL_TIME_MINUTES,
    supplier: Callable[[], VehicleComponent] | None = None,
    preview: VehicleComponent | None = None,
    extra_commitments: Iterable[object] = (),
) -> TransactionOffer:
    """Build a transaction that creates a catalog part and installs it directly."""

    preview_part = preview or component(label)
    commitments: list[object] = []
    commitments.extend(_cost_commitments(bay, cash_cost=price, time_minutes=install_time))
    commitments.append(
        CatalogInstallCommitment(
            bay.vehicle.loadout,
            slot_name,
            supplier or (lambda: component(label)),
            preview_part,
            label="create and assign vehicle part",
        ),
    )
    commitments.extend(extra_commitments)
    return TransactionOffer(label=f"buy and install {label}", commitments=commitments)


def _cost_commitments(
    bay: VehicleBay,
    *,
    cash_cost: int,
    time_minutes: int,
) -> list[ValueDeltaCommitment]:
    commitments: list[ValueDeltaCommitment] = []
    if cash_cost < 0:
        raise ValueError("cash cost must be non-negative")
    if time_minutes < 0:
        raise ValueError("time cost must be non-negative")
    if cash_cost:
        commitments.append(
            value_field_commitment(
                bay,
                "cash",
                -cash_cost,
                label="pay cash",
                detail_label="cash",
                min_value=0,
            ),
        )
    if time_minutes:
        commitments.append(
            value_field_commitment(
                bay,
                "time_minutes",
                time_minutes,
                label="spend time",
                detail_label="time_minutes",
                min_value=0,
            ),
        )
    return commitments


def _value_planning_key(obj: object, field_name: str) -> tuple[str, object, str]:
    uid = getattr(obj, "uid", None)
    identifier = id(obj) if uid is None else uid
    return (obj.__class__.__name__, identifier, field_name)


__all__ = [
    "CatalogInstallCommitment",
    "INSTALL_TIME_MINUTES",
    "SERVICE_TIME_MINUTES",
    "VehicleBay",
    "VehiclePartInventory",
    "build_catalog_install_offer",
    "build_catalog_purchase_offer",
    "build_inventory_install_offer",
    "build_service_offer",
    "component",
    "value_field_commitment",
]
