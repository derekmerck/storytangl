from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import ClassVar, Protocol, TypeVar

from pydantic import Field

from tangl.core import Entity, Registry
from tangl.core.bases import BaseModelPlus

from .assembly import ComponentManager


class TransactionCheck(BaseModelPlus):
    """Pure preflight result for one transaction offer or commitment."""

    accepted: bool
    reason: str | None = None

    @classmethod
    def accept(cls) -> "TransactionCheck":
        return cls(accepted=True)

    @classmethod
    def reject(cls, reason: str) -> "TransactionCheck":
        return cls(accepted=False, reason=reason)


class TransactionReceipt(BaseModelPlus):
    """Plain result data from accepting an ephemeral transaction offer."""

    offer_label: str | None = None
    commitment_labels: list[str] = Field(default_factory=list)
    details: list[object] = Field(default_factory=list)


class TransactionRollbackError(RuntimeError):
    """Raised when rollback fails while recovering from a commit error."""


class TransactionCommitment(Protocol):
    """One ordered, rollback-capable writeback leg inside a transaction offer."""

    label: str

    def can_commit(self) -> TransactionCheck:
        ...

    def commit(self) -> object | None:
        ...

    def rollback(self) -> None:
        ...


SpecT = TypeVar("SpecT")


class TransactionHandler(Protocol[SpecT]):
    """Structural protocol for helpers that produce validated transaction offers."""

    def get_transaction_offers(self, spec: SpecT) -> Iterable["TransactionOffer"]:
        ...


@dataclass
class TransactionOffer:
    """Ephemeral, preflighted promise to apply ordered commitments.

    Offers deliberately carry live objects and rollback callbacks. They are not
    persistence records; serialize the originating spec and returned receipt instead.
    """

    label: str | None = None
    commitments: list[TransactionCommitment] = field(default_factory=list)

    guard_unstructure: ClassVar[bool] = True

    def can_accept(self) -> TransactionCheck:
        for commitment in self.commitments:
            check = commitment.can_commit()
            if not check.accepted:
                prefix = f"{commitment.label}: " if commitment.label else ""
                return TransactionCheck.reject(prefix + (check.reason or "rejected"))
        return TransactionCheck.accept()

    def accept(self) -> TransactionReceipt:
        check = self.can_accept()
        if not check.accepted:
            raise ValueError(check.reason or "transaction offer rejected")

        applied: list[TransactionCommitment] = []
        details: list[object] = []
        try:
            for commitment in self.commitments:
                applied.append(commitment)
                detail = commitment.commit()
                if detail is not None:
                    details.append(detail)
        except Exception as exc:
            rollback_errors: list[tuple[str, Exception]] = []
            for commitment in reversed(applied):
                try:
                    commitment.rollback()
                except Exception as rollback_error:
                    rollback_errors.append((commitment.label, rollback_error))
            if rollback_errors:
                labels = ", ".join(label for label, _ in rollback_errors)
                error = TransactionRollbackError(
                    f"transaction rollback failed for: {labels}"
                )
                error.add_note(f"original commit error: {exc!r}")
                for label, rollback_error in rollback_errors:
                    error.add_note(f"{label}: {rollback_error!r}")
                raise error from exc
            raise

        return TransactionReceipt(
            offer_label=self.label,
            commitment_labels=[commitment.label for commitment in applied],
            details=details,
        )


class CountableHolder(Protocol):
    """Minimal fungible-wallet surface used by countable transfer commitments."""

    def can_give_countable(
        self,
        asset_label: str,
        amount: int,
        receiver: object | None = None,
    ) -> bool:
        ...

    def can_receive_countable(
        self,
        asset_label: str,
        amount: int,
        giver: object | None = None,
    ) -> bool:
        ...

    def spend_countable(self, asset_label: str, amount: int) -> None:
        ...

    def gain_countable(self, asset_label: str, amount: int) -> None:
        ...


@dataclass
class CountableTransferCommitment:
    """Transfer one fungible asset count between two holders."""

    giver: CountableHolder
    receiver: CountableHolder
    asset_label: str
    amount: int
    label: str = "transfer countable"
    _committed: bool = False

    def can_commit(self) -> TransactionCheck:
        if self.amount < 0:
            return TransactionCheck.reject("amount must be non-negative")
        if not self.giver.can_give_countable(self.asset_label, self.amount, self.receiver):
            return TransactionCheck.reject("giver cannot provide countable asset")
        if not self.receiver.can_receive_countable(self.asset_label, self.amount, self.giver):
            return TransactionCheck.reject("receiver cannot accept countable asset")
        return TransactionCheck.accept()

    def commit(self) -> Mapping[str, object]:
        check = self.can_commit()
        if not check.accepted:
            raise ValueError(check.reason or "countable transfer rejected")
        self.giver.spend_countable(self.asset_label, self.amount)
        try:
            self.receiver.gain_countable(self.asset_label, self.amount)
        except Exception as exc:
            try:
                self.giver.gain_countable(self.asset_label, self.amount)
            except Exception as rollback_error:
                error = TransactionRollbackError("countable transfer rollback failed")
                error.add_note(f"original receive error: {exc!r}")
                error.add_note(f"refund error: {rollback_error!r}")
                raise error from exc
            raise
        self._committed = True
        return {
            "kind": "countable_transfer",
            "asset": self.asset_label,
            "amount": self.amount,
        }

    def rollback(self) -> None:
        if not self._committed:
            return
        self.receiver.spend_countable(self.asset_label, self.amount)
        self.giver.gain_countable(self.asset_label, self.amount)
        self._committed = False


@dataclass
class RegistryAddCommitment:
    """Add a newly prepared entity to a registry during offer acceptance."""

    registry: Registry
    item: Entity
    label: str = "add registry item"
    _committed: bool = False

    def can_commit(self) -> TransactionCheck:
        existing = self.registry.get(self.item.uid)
        if existing is not None and existing is not self.item:
            return TransactionCheck.reject("registry already contains item uid")
        return TransactionCheck.accept()

    def commit(self) -> Mapping[str, object]:
        check = self.can_commit()
        if not check.accepted:
            raise ValueError(check.reason or "registry add rejected")
        if self.registry.get(self.item.uid) is None:
            self.registry.add(self.item)
            self._committed = True
        return {
            "kind": "registry_add",
            "item_id": self.item.uid,
            "item_label": self.item.get_label(),
        }

    def rollback(self) -> None:
        if not self._committed:
            return
        self.registry.remove(self.item.uid)
        self._committed = False


ComponentSupplier = Entity | Callable[[], Entity]


@dataclass
class ComponentAssignmentCommitment:
    """Assign a graph component to an owner-bound component manager slot."""

    manager: ComponentManager
    slot_name: str
    component: ComponentSupplier
    label: str = "assign component"
    validate_after: bool = False
    allow_replace: bool = False
    _previous: list[Entity] = field(default_factory=list)
    _committed: bool = False
    _registered_by_assignment: Entity | None = field(default=None, repr=False)
    _resolved: Entity | None = field(default=None, repr=False)

    def _component(self) -> Entity:
        if self._resolved is None:
            self._resolved = (
                self.component()
                if callable(self.component)
                else self.component
            )
        return self._resolved

    def _can_replace(self, component: Entity) -> TransactionCheck:
        if not self.allow_replace:
            return TransactionCheck.reject("replacement disabled")
        if self.slot_name not in self.manager.slots:
            return TransactionCheck.reject(f"No such slot: {self.slot_name}")

        slot = self.manager.slots[self.slot_name]
        replaced = self.manager.get_slot(self.slot_name)
        if slot.max_count != 1 or not replaced:
            return TransactionCheck.reject("replacement requires one occupied single slot")
        if not self.manager.is_slot_enabled(self.slot_name):
            return TransactionCheck.reject(f"Slot disabled: {self.slot_name}")

        selects, reason = slot.selects_for(component)
        if not selects:
            return TransactionCheck.reject(reason)

        missing_prerequisites = [
            prerequisite
            for prerequisite in slot.prerequisite_slots
            if not self.manager._has_slot_components(prerequisite)
        ]
        if missing_prerequisites:
            return TransactionCheck.reject(
                f"Missing prerequisite slots: {', '.join(missing_prerequisites)}"
            )

        if self.manager.budgets and hasattr(component, "get_cost"):
            current = [
                item
                for item in self.manager.all_components()
                if item not in replaced
            ]
            current.append(component)
            for name, budget in self.manager.budgets.budgets.items():
                total = 0.0
                for item in current:
                    if hasattr(item, "get_cost"):
                        total += float(getattr(item, "get_cost")(name))
                if total > budget.capacity:
                    return TransactionCheck.reject(
                        f"Insufficient {name}: need {total}, have {budget.capacity}"
                    )

        return TransactionCheck.accept()

    def can_commit(self) -> TransactionCheck:
        component = self._component()
        can_assign, reason = self.manager.can_assign(self.slot_name, component)
        if can_assign:
            return TransactionCheck.accept()
        replace_check = self._can_replace(component)
        if replace_check.accepted:
            return replace_check
        return TransactionCheck.reject(reason)

    def commit(self) -> Mapping[str, object]:
        check = self.can_commit()
        if not check.accepted:
            raise ValueError(check.reason or "component assignment rejected")

        component = self._component()
        self._previous = list(self.manager.get_slot(self.slot_name))
        component_registry = getattr(component, "registry", None)
        slot = self.manager.slots[self.slot_name]
        replacing = self.allow_replace and slot.max_count == 1 and bool(self._previous)
        if replacing:
            for item in self._previous:
                self.manager.unassign(self.slot_name, item)
        try:
            self.manager.assign(self.slot_name, component)
        except Exception:
            if replacing:
                for item in self._previous:
                    self.manager.assign(self.slot_name, item)
            raise
        self._committed = True
        owner_registry = self.manager._owner_registry()
        if (
            component_registry is None
            and owner_registry is not None
            and owner_registry.get(component.uid) is component
        ):
            self._registered_by_assignment = component

        if self.validate_after:
            errors = self.manager.validate()
            if errors:
                raise ValueError("; ".join(errors))

        return {
            "kind": "component_assignment",
            "slot": self.slot_name,
            "component_id": component.uid,
            "component_label": component.get_label(),
            "replaced_ids": [item.uid for item in self._previous],
        }

    def rollback(self) -> None:
        if not self._committed:
            return
        for item in list(self.manager.get_slot(self.slot_name)):
            self.manager.unassign(self.slot_name, item)
        for item in self._previous:
            self.manager.assign(self.slot_name, item)
        owner_registry = self.manager._owner_registry()
        if self._registered_by_assignment is not None and owner_registry is not None:
            owner_registry.remove(self._registered_by_assignment.uid)
        self._registered_by_assignment = None
        self._previous = []
        self._committed = False


__all__ = [
    "ComponentAssignmentCommitment",
    "CountableHolder",
    "CountableTransferCommitment",
    "RegistryAddCommitment",
    "TransactionCheck",
    "TransactionCommitment",
    "TransactionHandler",
    "TransactionOffer",
    "TransactionReceipt",
    "TransactionRollbackError",
]
