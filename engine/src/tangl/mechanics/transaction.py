from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, MutableMapping
from dataclasses import dataclass, field
from typing import ClassVar, Protocol, TypeVar
from uuid import UUID

from pydantic import Field

from tangl.core import Entity, Registry, Token
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
Number = int | float
_PLAN_MISSING = object()


class TransactionHandler(Protocol[SpecT]):
    """Structural protocol for helpers that produce validated transaction offers."""

    def get_transaction_offers(self, spec: SpecT) -> Iterable["TransactionOffer"]:
        ...


@dataclass
class CallbackCommitment:
    """Domain-local commitment backed by explicit preflight, apply, and undo callbacks."""

    label: str
    apply: Callable[[], object | None]
    can_apply: Callable[[], TransactionCheck | bool] | None = None
    undo: Callable[[], None] | None = None
    _committed: bool = False

    def can_commit(self) -> TransactionCheck:
        if self.can_apply is None:
            return TransactionCheck.accept()
        result = self.can_apply()
        if isinstance(result, bool):
            return (
                TransactionCheck.accept()
                if result
                else TransactionCheck.reject("rejected")
            )
        return result

    def commit(self) -> object | None:
        check = self.can_commit()
        if not check.accepted:
            raise ValueError(check.reason or f"{self.label} rejected")
        detail = self.apply()
        self._committed = True
        return detail

    def rollback(self) -> None:
        if not self._committed:
            return
        if self.undo is not None:
            self.undo()
        self._committed = False


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
        planned_deltas: dict[object, Number] = {}
        planned_assets: dict[object, Entity] = {}
        unkeyed_value_delta_seen = False
        for commitment in self.commitments:
            if isinstance(
                commitment,
                (
                    ValueDeltaCommitment,
                    MappingDeltaCommitment,
                    StatDeltaCommitment,
                ),
            ):
                if (
                    isinstance(commitment, ValueDeltaCommitment)
                    and commitment.planning_key is None
                ):
                    if unkeyed_value_delta_seen:
                        prefix = f"{commitment.label}: " if commitment.label else ""
                        return TransactionCheck.reject(
                            prefix
                            + "multiple unkeyed value deltas require planning_key"
                        )
                    unkeyed_value_delta_seen = True
                check = commitment.can_commit_with_plan(planned_deltas)
            elif isinstance(commitment, AssetMoveCommitment):
                check = commitment.can_commit_with_plan(planned_assets)
            else:
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


class AssetHolder(Protocol):
    """Minimal discrete-asset holder surface for move/create commitments."""

    def get_asset(self, label: str) -> Entity | None:
        ...

    def get_asset_key(self, asset: Entity | str) -> str | None:
        ...

    def can_give_asset(
        self,
        asset: Entity,
        receiver: object | None = None,
    ) -> bool:
        ...

    def can_receive_asset(
        self,
        asset: Entity,
        giver: object | None = None,
    ) -> bool:
        ...

    def add_asset(self, asset: Entity, *, label: str | None = None) -> None:
        ...

    def remove_asset(self, asset: Entity | str) -> Entity:
        ...


@dataclass
class ListAssetHolder:
    """Adapter that exposes an ordered entity list as a discrete asset holder.

    The adapter does not own persistence or graph membership. It is a
    transaction-facing view over a domain list, useful when a mechanic wants to
    preserve list order for UI projection while using `AssetMoveCommitment` or
    `CatalogAssetCommitment` for preflight, commit, and rollback.
    """

    items: list[Entity]
    _labels_by_uid: ClassVar[dict[UUID, str]] = {}
    _removed_indices_by_uid: dict[UUID, int] = field(default_factory=dict)

    def _item_key(self, item: Entity, label: str | None = None) -> str:
        key = _asset_holder_key(item, label)
        if key is None:
            raise ValueError("List asset holder item requires a label")
        return key

    def _local_label(self, item: Entity) -> str | None:
        return self._labels_by_uid.get(item.uid)

    def _index_of(self, asset: Entity) -> int | None:
        for index, item in enumerate(self.items):
            if item is asset:
                return index
        return None

    def get_asset(self, label: str) -> Entity | None:
        if not label:
            return None
        for item in self.items:
            if label == self._local_label(item):
                return item
            if label == item.get_label():
                return item
            if isinstance(item, Token) and label == item.token_from:
                return item
        return None

    def get_asset_key(self, asset: Entity | str) -> str | None:
        resolved = self.get_asset(asset) if isinstance(asset, str) else asset
        if resolved is None or not self.has_asset(resolved):
            return None
        local = self._local_label(resolved)
        if local is not None:
            return local
        return _asset_holder_key(resolved)

    def can_give_asset(
        self,
        asset: Entity,
        receiver: object | None = None,
    ) -> bool:
        _ = receiver
        return self.has_asset(asset)

    def can_receive_asset(
        self,
        asset: Entity,
        giver: object | None = None,
    ) -> bool:
        _ = asset, giver
        return True

    def add_asset(self, asset: Entity, *, label: str | None = None) -> None:
        key = self._item_key(asset, label)
        existing = self.get_asset(key)
        if existing is not None and existing is not asset:
            raise ValueError(f"List asset holder already contains key: {key}")
        if self._index_of(asset) is None:
            index = self._removed_indices_by_uid.pop(asset.uid, len(self.items))
            self.items.insert(min(index, len(self.items)), asset)
        if label is not None:
            self._labels_by_uid[asset.uid] = label

    def remove_asset(self, asset: Entity | str) -> Entity:
        resolved = self.get_asset(asset) if isinstance(asset, str) else asset
        if resolved is None:
            raise KeyError(asset)
        index = self._index_of(resolved)
        if index is None:
            key = resolved.get_label() or repr(resolved)
            raise KeyError(f"Unknown list asset holder item: {key}")
        self._removed_indices_by_uid[resolved.uid] = index
        self.items.pop(index)
        self._labels_by_uid.pop(resolved.uid, None)
        return resolved

    def has_asset(self, asset: Entity | str) -> bool:
        if isinstance(asset, str):
            return self.get_asset(asset) is not None
        return any(item is asset for item in self.items)


@dataclass
class ComponentSlotAssetHolder:
    """Expose one component-manager slot as a transaction asset holder.

    Holder labels are live transaction aliases, not constructor-form state.
    Persist durable item identity through the manager's component UUIDs.
    """

    manager: ComponentManager
    slot_name: str
    _removed_indices_by_uid: dict[UUID, int] = field(default_factory=dict)

    def _item_key(self, item: Entity, label: str | None = None) -> str:
        key = _asset_holder_key(item, label)
        if key is None:
            raise ValueError("Component slot holder item requires a label")
        return key

    def _local_label(self, item: Entity) -> str | None:
        return self._slot_labels().get(item.uid)

    def _slot_ids(self) -> list[UUID]:
        return self.manager.assignment_ids.setdefault(self.slot_name, [])

    def _slot_labels(self) -> dict[UUID, str]:
        return self.manager._holder_labels.setdefault(self.slot_name, {})

    def _index_of(self, asset: Entity) -> int | None:
        for index, item in enumerate(self.manager.get_slot(self.slot_name)):
            if item is asset:
                return index
        return None

    def get_asset(self, label: str) -> Entity | None:
        if not label:
            return None
        slot_labels = self._slot_labels()
        for item in self.manager.get_slot(self.slot_name):
            if label == slot_labels.get(item.uid):
                return item
            if label == item.get_label():
                return item
            if isinstance(item, Token) and label == item.token_from:
                return item
        return None

    def get_asset_key(self, asset: Entity | str) -> str | None:
        resolved = self.get_asset(asset) if isinstance(asset, str) else asset
        if resolved is None or not self.has_asset(resolved):
            return None
        local = self._local_label(resolved)
        if local is not None:
            return local
        return _asset_holder_key(resolved)

    def can_give_asset(
        self,
        asset: Entity,
        receiver: object | None = None,
    ) -> bool:
        _ = receiver
        return self.has_asset(asset)

    def can_receive_asset(
        self,
        asset: Entity,
        giver: object | None = None,
    ) -> bool:
        _ = giver
        if self.has_asset(asset):
            return True
        can_accept_registry, _reason = self.manager.can_accept_component_registry(asset)
        if not can_accept_registry:
            return False
        can_assign, _reason = self.manager.can_assign(self.slot_name, asset)
        return can_assign

    def add_asset(self, asset: Entity, *, label: str | None = None) -> None:
        key = self._item_key(asset, label)
        existing = self.get_asset(key)
        if existing is not None and existing is not asset:
            raise ValueError(f"Component slot holder already contains key: {key}")

        if self._index_of(asset) is None:
            self.manager.assign(self.slot_name, asset)
            index = self._removed_indices_by_uid.pop(asset.uid, None)
            if index is not None:
                slot_ids = self._slot_ids()
                if asset.uid not in slot_ids:
                    raise ValueError("Component slot assignment did not record asset UID")
                slot_ids.remove(asset.uid)
                slot_ids.insert(min(index, len(slot_ids)), asset.uid)
        if label is not None:
            self._slot_labels()[asset.uid] = label

    def remove_asset(self, asset: Entity | str) -> Entity:
        resolved = self.get_asset(asset) if isinstance(asset, str) else asset
        if resolved is None:
            raise KeyError(asset)
        index = self._index_of(resolved)
        if index is None:
            key = resolved.get_label() or repr(resolved)
            raise KeyError(f"Unknown component slot holder item: {key}")
        self._removed_indices_by_uid[resolved.uid] = index
        self.manager.unassign(self.slot_name, resolved)
        self._slot_labels().pop(resolved.uid, None)
        return resolved

    def has_asset(self, asset: Entity | str) -> bool:
        if isinstance(asset, str):
            return self.get_asset(asset) is not None
        return any(item is asset for item in self.manager.get_slot(self.slot_name))

    def all_items(self) -> list[Entity]:
        return list(self.manager.get_slot(self.slot_name))


class StatLike(Protocol):
    """Minimal stat surface for transaction-backed stat deltas."""

    fv: float


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


def _asset_holder_key(asset: Entity, label: str | None = None) -> str | None:
    if label is not None:
        return label
    key = asset.get_label()
    if key:
        return key
    if isinstance(asset, Token) and asset.token_from:
        return asset.token_from
    return None


def _receiver_key_available(
    receiver: AssetHolder,
    asset: Entity,
    label: str | None,
) -> TransactionCheck:
    key = _asset_holder_key(asset, label)
    if key is None:
        return TransactionCheck.accept()
    existing = receiver.get_asset(key)
    if existing is not None and existing is not asset:
        return TransactionCheck.reject("receiver already holds asset key")
    return TransactionCheck.accept()


AssetRef = Entity | str


@dataclass
class AssetMoveCommitment:
    """Move one existing discrete graph asset between holder-like objects."""

    giver: AssetHolder
    receiver: AssetHolder
    asset: AssetRef
    label: str = "move asset"
    receiver_label: str | None = None
    _moved: Entity | None = field(default=None, init=False, repr=False)
    _giver_label: str | None = field(default=None, init=False, repr=False)
    _committed: bool = field(default=False, init=False, repr=False)

    def _asset(self) -> Entity | None:
        if isinstance(self.asset, str):
            return self.giver.get_asset(self.asset)
        return self.asset

    def can_commit(self) -> TransactionCheck:
        asset = self._asset()
        if asset is None:
            return TransactionCheck.reject("giver does not hold asset")
        if not self.giver.can_give_asset(asset, self.receiver):
            return TransactionCheck.reject("giver cannot give asset")
        if not self.receiver.can_receive_asset(asset, self.giver):
            return TransactionCheck.reject("receiver cannot receive asset")
        return _receiver_key_available(self.receiver, asset, self.receiver_label)

    def can_commit_with_plan(
        self,
        planned_assets: MutableMapping[object, Entity],
    ) -> TransactionCheck:
        check = self.can_commit()
        if not check.accepted:
            return check
        asset = self._asset()
        if asset is None:
            return TransactionCheck.reject("giver does not hold asset")

        move_key = ("asset_move", id(self.giver), asset.uid)
        if move_key in planned_assets:
            return TransactionCheck.reject("asset already planned for move")

        receiver_key = _asset_holder_key(asset, self.receiver_label)
        receive_key = (
            None
            if receiver_key is None
            else ("asset_receive", id(self.receiver), receiver_key)
        )
        if receive_key is not None:
            planned_asset = planned_assets.get(receive_key)
            if planned_asset is not None and planned_asset is not asset:
                return TransactionCheck.reject("receiver already planned for asset key")

        planned_assets[move_key] = asset
        if receive_key is not None:
            planned_assets[receive_key] = asset
        return TransactionCheck.accept()

    def commit(self) -> Mapping[str, object]:
        check = self.can_commit()
        if not check.accepted:
            raise ValueError(check.reason or "asset move rejected")
        asset = self._asset()
        if asset is None:
            raise ValueError("giver does not hold asset")
        giver_label = self.giver.get_asset_key(asset)
        moved = self.giver.remove_asset(asset)
        try:
            self.receiver.add_asset(moved, label=self.receiver_label)
        except Exception:
            self.giver.add_asset(moved, label=giver_label)
            raise
        self._moved = moved
        self._giver_label = giver_label
        self._committed = True
        return {
            "kind": "asset_move",
            "asset_id": moved.uid,
            "asset_label": moved.get_label(),
        }

    def rollback(self) -> None:
        if not self._committed or self._moved is None:
            return
        moved = self.receiver.remove_asset(self._moved)
        self.giver.add_asset(moved, label=self._giver_label)
        self._moved = None
        self._giver_label = None
        self._committed = False


AssetSupplier = Callable[[], Entity]


@dataclass
class CatalogAssetCommitment:
    """Create one discrete graph asset from a supplier and add it to a holder."""

    receiver: AssetHolder
    supplier: AssetSupplier
    registry: Registry | None = None
    label: str = "create catalog asset"
    receiver_label: str | None = None
    preview: Entity | None = None
    can_create: Callable[[], TransactionCheck | bool] | None = None
    _created: Entity | None = field(default=None, init=False, repr=False)
    _registered: bool = field(default=False, init=False, repr=False)
    _committed: bool = field(default=False, init=False, repr=False)

    def can_commit(self) -> TransactionCheck:
        if self.can_create is not None:
            result = self.can_create()
            if isinstance(result, bool):
                if not result:
                    return TransactionCheck.reject("catalog cannot create asset")
            elif not result.accepted:
                return result
        if self.preview is not None:
            if (
                self.registry is not None
                and self.registry.get(self.preview.uid) is not None
            ):
                return TransactionCheck.reject("registry already contains item uid")
            if not self.receiver.can_receive_asset(self.preview, None):
                return TransactionCheck.reject("receiver cannot receive asset")
            return _receiver_key_available(
                self.receiver,
                self.preview,
                self.receiver_label,
            )
        return TransactionCheck.accept()

    def commit(self) -> Mapping[str, object]:
        check = self.can_commit()
        if not check.accepted:
            raise ValueError(check.reason or "catalog asset creation rejected")
        item = self.supplier()
        if self.registry is not None and self.registry.get(item.uid) is not None:
            raise ValueError("registry already contains item uid")
        if not self.receiver.can_receive_asset(item, None):
            raise ValueError("receiver cannot receive asset")
        key_check = _receiver_key_available(self.receiver, item, self.receiver_label)
        if not key_check.accepted:
            raise ValueError(key_check.reason or "receiver cannot receive asset")

        if self.registry is not None:
            self.registry.add(item)
            self._registered = True
        try:
            self.receiver.add_asset(item, label=self.receiver_label)
        except Exception:
            if self._registered and self.registry is not None:
                self.registry.remove(item.uid)
                self._registered = False
            raise
        self._created = item
        self._committed = True
        return {
            "kind": "catalog_asset",
            "asset_id": item.uid,
            "asset_label": item.get_label(),
        }

    def rollback(self) -> None:
        if not self._committed or self._created is None:
            return
        self.receiver.remove_asset(self._created)
        if self._registered and self.registry is not None:
            self.registry.remove(self._created.uid)
        self._created = None
        self._registered = False
        self._committed = False


def _check_delta(
    current: Number,
    delta: Number,
    min_value: Number | None,
    max_value: Number | None,
) -> TransactionCheck:
    next_value = current + delta
    if min_value is not None and next_value < min_value:
        return TransactionCheck.reject(
            f"value below minimum: {next_value} < {min_value}"
        )
    if max_value is not None and next_value > max_value:
        return TransactionCheck.reject(
            f"value above maximum: {next_value} > {max_value}"
        )
    return TransactionCheck.accept()


def _is_zero(value: Number) -> bool:
    if isinstance(value, float):
        return abs(value) < 1e-9
    return value == 0


@dataclass
class ValueDeltaCommitment:
    """Apply one bounded numeric delta through explicit getter/setter callbacks."""

    get_value: Callable[[], Number]
    set_value: Callable[[Number], None]
    delta: Number
    label: str = "mutate value"
    detail_label: str | None = None
    min_value: Number | None = None
    max_value: Number | None = None
    planning_key: object | None = None
    _previous: Number = field(default=0, init=False, repr=False)
    _committed: bool = field(default=False, init=False, repr=False)

    def _plan_key(self) -> object:
        if self.planning_key is not None:
            return self.planning_key
        return ("value_delta", id(self))

    def can_commit(self) -> TransactionCheck:
        return _check_delta(
            self.get_value(),
            self.delta,
            self.min_value,
            self.max_value,
        )

    def can_commit_with_plan(
        self,
        planned_deltas: MutableMapping[object, Number],
    ) -> TransactionCheck:
        key = self._plan_key()
        planned_current = planned_deltas.get(key, _PLAN_MISSING)
        current = (
            self.get_value()
            if planned_current is _PLAN_MISSING
            else planned_current
        )
        check = _check_delta(
            current,
            self.delta,
            self.min_value,
            self.max_value,
        )
        if check.accepted:
            planned_deltas[key] = current + self.delta
        return check

    def commit(self) -> Mapping[str, object]:
        current = self.get_value()
        check = _check_delta(
            current,
            self.delta,
            self.min_value,
            self.max_value,
        )
        if not check.accepted:
            raise ValueError(check.reason or "value delta rejected")
        next_value = current + self.delta
        self.set_value(next_value)
        self._previous = current
        self._committed = True
        return {
            "kind": "value_delta",
            "label": self.detail_label or self.label,
            "delta": self.delta,
            "previous_value": current,
            "value": next_value,
        }

    def rollback(self) -> None:
        if not self._committed:
            return
        self.set_value(self._previous)
        self._previous = 0
        self._committed = False


@dataclass
class MappingDeltaCommitment:
    """Apply one bounded numeric delta to a mutable resource mapping."""

    values: MutableMapping[str, Number]
    key: str
    delta: Number
    label: str = "mutate mapping value"
    min_value: Number | None = 0
    max_value: Number | None = None
    default: Number = 0
    drop_zero: bool = False
    _previous: Number = field(default=0, init=False, repr=False)
    _had_previous: bool = field(default=False, init=False, repr=False)
    _committed: bool = field(default=False, init=False, repr=False)

    def _plan_key(self) -> object:
        return ("mapping_delta", id(self.values), self.key)

    def can_commit(self) -> TransactionCheck:
        return _check_delta(
            self.values.get(self.key, self.default),
            self.delta,
            self.min_value,
            self.max_value,
        )

    def can_commit_with_plan(
        self,
        planned_deltas: MutableMapping[object, Number],
    ) -> TransactionCheck:
        key = self._plan_key()
        planned_current = planned_deltas.get(key, _PLAN_MISSING)
        current = (
            self.values.get(self.key, self.default)
            if planned_current is _PLAN_MISSING
            else planned_current
        )
        check = _check_delta(
            current,
            self.delta,
            self.min_value,
            self.max_value,
        )
        if check.accepted:
            planned_deltas[key] = current + self.delta
        return check

    def commit(self) -> Mapping[str, object]:
        self._had_previous = self.key in self.values
        current = self.values.get(self.key, self.default)
        check = _check_delta(
            current,
            self.delta,
            self.min_value,
            self.max_value,
        )
        if not check.accepted:
            raise ValueError(check.reason or "mapping delta rejected")
        next_value = current + self.delta
        if self.drop_zero and _is_zero(next_value):
            self.values.pop(self.key, None)
        else:
            self.values[self.key] = next_value
        self._previous = current
        self._committed = True
        return {
            "kind": "mapping_delta",
            "key": self.key,
            "delta": self.delta,
            "previous_value": current,
            "value": next_value,
        }

    def rollback(self) -> None:
        if not self._committed:
            return
        if self._had_previous:
            self.values[self.key] = self._previous
        else:
            self.values.pop(self.key, None)
        self._previous = 0
        self._had_previous = False
        self._committed = False


@dataclass
class StatDeltaCommitment:
    """Apply one bounded delta to a stat-like value in a stat mapping."""

    stats: MutableMapping[str, StatLike]
    stat_name: str
    delta: float
    label: str = "mutate stat"
    min_value: float | None = None
    max_value: float | None = None
    _previous: float = field(default=0.0, init=False, repr=False)
    _committed: bool = field(default=False, init=False, repr=False)

    def _plan_key(self) -> object:
        return ("stat_delta", id(self.stats), self.stat_name)

    def can_commit(self) -> TransactionCheck:
        if self.stat_name not in self.stats:
            return TransactionCheck.reject(f"missing stat: {self.stat_name}")
        return _check_delta(
            self.stats[self.stat_name].fv,
            self.delta,
            self.min_value,
            self.max_value,
        )

    def can_commit_with_plan(
        self,
        planned_deltas: MutableMapping[object, Number],
    ) -> TransactionCheck:
        if self.stat_name not in self.stats:
            return TransactionCheck.reject(f"missing stat: {self.stat_name}")
        key = self._plan_key()
        planned_current = planned_deltas.get(key, _PLAN_MISSING)
        current = (
            self.stats[self.stat_name].fv
            if planned_current is _PLAN_MISSING
            else planned_current
        )
        check = _check_delta(
            current,
            self.delta,
            self.min_value,
            self.max_value,
        )
        if check.accepted:
            planned_deltas[key] = current + self.delta
        return check

    def commit(self) -> Mapping[str, object]:
        if self.stat_name not in self.stats:
            raise ValueError(f"missing stat: {self.stat_name}")
        stat = self.stats[self.stat_name]
        current = stat.fv
        check = _check_delta(
            current,
            self.delta,
            self.min_value,
            self.max_value,
        )
        if not check.accepted:
            raise ValueError(check.reason or "stat delta rejected")
        next_value = current + self.delta
        stat.fv = next_value
        self._previous = current
        self._committed = True
        return {
            "kind": "stat_delta",
            "stat": self.stat_name,
            "delta": self.delta,
            "previous_value": current,
            "value": next_value,
        }

    def rollback(self) -> None:
        if not self._committed:
            return
        self.stats[self.stat_name].fv = self._previous
        self._previous = 0.0
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
    "AssetHolder",
    "AssetMoveCommitment",
    "CallbackCommitment",
    "CatalogAssetCommitment",
    "ComponentAssignmentCommitment",
    "ComponentSlotAssetHolder",
    "CountableHolder",
    "CountableTransferCommitment",
    "ListAssetHolder",
    "MappingDeltaCommitment",
    "RegistryAddCommitment",
    "StatDeltaCommitment",
    "StatLike",
    "TransactionCheck",
    "TransactionCommitment",
    "TransactionHandler",
    "TransactionOffer",
    "TransactionReceipt",
    "TransactionRollbackError",
    "ValueDeltaCommitment",
]
