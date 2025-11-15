"""tangl.vm.provision.offer
=================================

Provision offers describe *how* a requirement could be satisfied without
performing any work up front.  Provisioners emit these offers and the planning
layer selects which ones to accept.

The redesign (v3.7) focuses on three goals:

* **Lazy execution** – accepting an offer performs the real work via a
  callback.
* **Cost-aware arbitration** – offers expose a :class:`ProvisionCost` so
  selectors can order proposals consistently.
* **Clear separation of modes** – dependency and affordance offers share a
  base type but provide distinct accept signatures.

Planning receipts (:class:`BuildReceipt` and :class:`PlanningReceipt`) remain in
this module because they summarise what happened to the emitted offers during a
planning phase.

Offer Selection & Deduplication
-------------------------------

Planning dispatch is responsible for collecting offers, deduplicating
equivalent proposals, and selecting which ones to accept.  EXISTING offers can
now expose :attr:`DependencyOffer.provider_id`, allowing the dispatcher to
retain only the cheapest (and closest) offer for a given node without executing
callbacks.

Example::

    >>> # Two provisioners both offer the same door
    >>> local_offer.provider_id == door.uid
    >>> global_offer.provider_id == door.uid
    >>> # Deduplication keeps only the best-scored offer per requirement/provider

CREATE/UPDATE/CLONE offers omit ``provider_id`` because they either produce a
new node or mutate one after the offer is accepted, so duplicates are inherently
distinct.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Callable, TYPE_CHECKING, Any, Iterable
from uuid import UUID

from pydantic import Field

from tangl.core import CallReceipt, Edge, Entity, Node, Record, Registry
from tangl.type_hints import StringMap
from .requirement import ProvisioningPolicy, Requirement

if TYPE_CHECKING:
    from tangl.vm.context import Context


class ProvisionCost(IntEnum):
    """Relative cost of satisfying a requirement.

    Lower values represent cheaper operations.  The values are intentionally
    spaced so that new categories can be inserted if needed without disrupting
    ordering.
    """

    DIRECT = 10
    """Existing provider can be reused as-is."""

    LIGHT_INDIRECT = 50
    """Existing provider requires light updates."""

    HEAVY_INDIRECT = 100
    """Provider must be cloned and evolved."""

    CREATE = 200
    """Provider must be created from scratch."""


class ProvisionOffer(Entity):
    """Base class for all provision offers."""

    base_cost: ProvisionCost = ProvisionCost.DIRECT
    cost: float = Field(default=float(ProvisionCost.DIRECT))
    proximity: float = 999.0
    proximity_detail: str | None = None
    source_provisioner_id: UUID | None = None
    source_layer: str | None = None
    selection_criteria: StringMap = Field(default_factory=dict)

    @property
    def blame_id(self) -> UUID | None:  # pragma: no cover - compatibility hook
        """Expose the originating provisioner identifier."""

        return self.source_provisioner_id

    def available(self, _ns: StringMap | None = None) -> bool:  # pragma: no cover - compatibility hook
        """Compatibility shim for legacy selectors.

        Legacy planning code expects offers to expose ``available(ns)``.  New
        selectors should prefer inspecting concrete offer subclasses directly.
        """

        return True

    def get_label(self) -> str | None:
        """Return the offer label when available."""

        return getattr(self, "label", None)

    def get_sort_key(self) -> tuple[float, float]:
        """Return the arbitration sort key used for deterministic selection."""

        return (self.cost, self.proximity)

    def accept(self, *, ctx: "Context") -> Node | Edge:
        """Execute the offer and return the resulting graph item."""

        raise NotImplementedError


class DependencyOffer(ProvisionOffer):
    """Proposal to satisfy a dependency by providing a node."""

    requirement_id: UUID
    operation: ProvisioningPolicy
    # Need provider id for existing to dedup
    target_tags: set[str] = Field(default_factory=set)
    accept_func: Callable[[Any], Node]
    provider_id: UUID | None = None
    """Identifier of the node that will be provided when known (EXISTING offers)."""
    requirement: Requirement | None = Field(default=None, exclude=True)

    def accept(self, *, ctx: "Context") -> Node:
        provider = self.accept_func(ctx)
        if provider not in ctx.graph:
            ctx.graph.add(provider)
        return provider

    def get_label(self) -> str | None:
        """Return the offer label when available."""

        return getattr(self, "label", f"{self.operation}")


class AffordanceOffer(ProvisionOffer):
    """Proposal to attach an affordance edge."""

    label: str
    target_tags: set[str] = Field(default_factory=set)
    accept_func: Callable[[Any, Node], Edge]

    def available_for(self, node: Node) -> bool:
        """Return ``True`` when the offer applies to ``node``."""

        if not self.target_tags:
            return True
        return bool(self.target_tags & node.tags)

    def satisfied_by(self, node: Node) -> bool:  # pragma: no cover - compatibility hook
        """Compatibility alias for :meth:`available_for`."""

        return self.available_for(node)

    def accept(self, *, ctx: "Context", destination: Node) -> Edge:
        affordance = self.accept_func(ctx, destination)
        source = affordance.source
        if source is not None and source not in ctx.graph:
            ctx.graph.add(source)
        return affordance


class BuildReceipt(CallReceipt):
    """Summary of what happened when accepting a single offer."""

    record_type: str = Field("build_receipt", alias="type")
    result_type: type[UUID] = UUID

    blame_id: UUID = Field(alias="provisioner_id")
    caller_id: UUID = Field(alias="requirement_id")
    result: UUID | None = Field(None, alias="provider_id")

    operation: ProvisioningPolicy = ProvisioningPolicy.NOOP
    accepted: bool = True
    hard_req: bool | None = None
    reason: str | None = None

    @property
    def provider_id(self) -> UUID | None:
        return self.result

    def provider(self, registry: Registry) -> Node | None:
        return registry.get(self.provider_id) if self.provider_id else None


class PlanningReceipt(Record):
    """Aggregated report for a planning phase."""

    record_type: str = Field("planning_receipt", alias="type")
    cursor_id: UUID = Field(default=UUID(int=0))
    frontier_node_ids: list[UUID] = Field(default_factory=list)
    builds: list[BuildReceipt] = Field(default_factory=list)
    unresolved_hard_requirements: list[UUID] = Field(default_factory=list)
    waived_soft_requirements: list[UUID] = Field(default_factory=list)
    softlock_detected: bool = False
    selection_audit: list[dict[str, object]] = Field(default_factory=list)

    @property
    def attached(self) -> int:
        return sum(
            1
            for build in self.builds
            if build.accepted and build.operation == ProvisioningPolicy.EXISTING
        )

    @property
    def updated(self) -> int:
        return sum(
            1
            for build in self.builds
            if build.accepted and build.operation == ProvisioningPolicy.UPDATE
        )

    @property
    def created(self) -> int:
        return sum(
            1
            for build in self.builds
            if build.accepted and build.operation == ProvisioningPolicy.CREATE
        )

    @property
    def cloned(self) -> int:
        return sum(
            1
            for build in self.builds
            if build.accepted and build.operation == ProvisioningPolicy.CLONE
        )

    @property
    def resolved_dependencies(self) -> int:
        return self.attached + self.updated + self.created + self.cloned

    @classmethod
    def summarize(
        cls,
        *builds: BuildReceipt,
        cursor_id: UUID | None = None,
        frontier_node_ids: Iterable[UUID] | None = None,
        softlock_detected: bool = False,
        selection_audit: Iterable[dict[str, object]] | None = None,
    ) -> PlanningReceipt:
        attached = 0
        updated = 0
        created = 0
        cloned = 0
        unresolved_hard_requirements: list[UUID] = []
        waived_soft_requirements: list[UUID] = []

        for receipt in builds:
            if not receipt.accepted:
                if receipt.caller_id is None:
                    continue
                if receipt.hard_req:
                    unresolved_hard_requirements.append(receipt.caller_id)
                else:
                    waived_soft_requirements.append(receipt.caller_id)
                continue

            match receipt.operation:
                case ProvisioningPolicy.EXISTING:
                    attached += 1
                case ProvisioningPolicy.UPDATE:
                    updated += 1
                case ProvisioningPolicy.CREATE:
                    created += 1
                case ProvisioningPolicy.CLONE:
                    cloned += 1

        receipt = cls(
            cursor_id=cursor_id or UUID(int=0),
            frontier_node_ids=list(frontier_node_ids or ()),
            builds=list(builds),
            unresolved_hard_requirements=unresolved_hard_requirements,
            waived_soft_requirements=waived_soft_requirements,
            softlock_detected=softlock_detected,
            selection_audit=list(selection_audit or ()),
        )

        # Prime derived properties for summarize callers.
        if not getattr(receipt, "builds", None):
            # If builds list is empty, the counts are already zero.
            return receipt

        # Accessing the properties ensures they are evaluated at least once
        # during summarization for test expectations.
        _ = attached + updated + created + cloned  # noqa: F841
        return receipt

