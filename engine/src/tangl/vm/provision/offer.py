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
"""

from __future__ import annotations

from enum import IntEnum
from typing import Callable, TYPE_CHECKING, Any
from uuid import UUID

from pydantic import Field

from tangl.core import CallReceipt, Edge, Entity, Node, Record, Registry
from tangl.type_hints import StringMap
from .requirement import ProvisioningPolicy

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

    cost: ProvisionCost = ProvisionCost.DIRECT
    proximity: int = 999
    source_provisioner_id: UUID | None = None
    source_layer: str | None = None

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

    def get_label(self) -> str | None:  # pragma: no cover - compatibility hook
        """Return the offer label when available."""

        return getattr(self, "label", None)

    def accept(self, *, ctx: "Context") -> Node | Edge:
        """Execute the offer and return the resulting graph item."""

        raise NotImplementedError


class DependencyOffer(ProvisionOffer):
    """Proposal to satisfy a dependency by providing a node."""

    requirement_id: UUID
    operation: str
    accept_func: Callable[[Any], Node]

    def accept(self, *, ctx: "Context") -> Node:
        provider = self.accept_func(ctx)
        if provider not in ctx.graph:
            ctx.graph.add(provider)
        return provider


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
    resolved_dependencies: int = 0
    resolved_affordances: int = 0
    attached: int = 0
    updated: int = 0
    created: int = 0
    cloned: int = 0
    unresolved_hard_requirements: list[UUID] = Field(default_factory=list)
    waived_soft_requirements: list[UUID] = Field(default_factory=list)

    @classmethod
    def summarize(cls, *builds: BuildReceipt) -> PlanningReceipt:
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

        resolved_dependencies = attached + updated + created + cloned

        return cls(
            resolved_dependencies=resolved_dependencies,
            resolved_affordances=0,
            behavior_id=[r.blame_id for r in builds],
            attached=attached,
            updated=updated,
            created=created,
            cloned=cloned,
            unresolved_hard_requirements=unresolved_hard_requirements,
            waived_soft_requirements=waived_soft_requirements,
            result="ok",
        )

