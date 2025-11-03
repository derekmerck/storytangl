from __future__ import annotations

"""Lazy offer records used by the planning subsystem.

The planning system surfaces :class:`DependencyOffer` and
:class:`AffordanceOffer` as pure value objects. They capture provenance and a
callable that, when invoked, resolves :class:`~tangl.core.graph.Node` or
:class:`~tangl.core.graph.Edge` instances via the
:class:`~tangl.vm.context.Context`.  This keeps handlers free to perform graph
work only when an offer is accepted.
"""

from dataclasses import dataclass, field
from typing import Optional, Protocol, TYPE_CHECKING
from uuid import UUID

from tangl.core.graph import Edge, Node

from .requirement import ProvisioningPolicy

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from tangl.vm.context import Context
    from .open_edge import Affordance, Dependency
    from .requirement import Requirement


class DependencyAcceptor(Protocol):
    """Signature for dependency offer acceptance callbacks."""

    def __call__(
        self,
        *,
        ctx: Context,
        requirement: Requirement,
        dependency: Optional[Dependency] = None,
        **kwargs,
    ) -> Optional[Node]:
        ...


class AffordanceAcceptor(Protocol):
    """Signature for affordance offer acceptance callbacks."""

    def __call__(
        self,
        *,
        ctx: Context,
        affordance: Affordance,
        requirement: Requirement,
        destination: Optional[Node] = None,
        **kwargs,
    ) -> Optional[Edge]:
        ...


@dataclass(slots=True, frozen=True)
class ProvisionCost:
    """ProvisionCost(weight: float = 1.0, proximity: int | None = None, layer_penalty: float = 0.0)

    Lightweight scoring tuple used to compare provision offers.

    Why
    ----
    Selectors rank competing offers using a blend of intrinsic cost, frontier
    proximity, and behavior layer penalties.  :class:`ProvisionCost` bundles
    those factors so selectors can stay agnostic to how the values were
    produced.

    Key Features
    ------------
    * **Frozen dataclass** – safe to share between collectors and selectors.
    * **Comparable** – :meth:`total` returns an aggregate score for simple
      ordering.
    * **Metadata friendly** – retains the raw components for richer heuristics.

    API
    ---
    - :attr:`weight` – base scalar weight (lower is preferred).
    - :attr:`proximity` – integer distance hint (e.g., hops from cursor).
    - :attr:`layer_penalty` – additive penalty for crossing behavior layers.
    - :meth:`total` – aggregate helper used by default arbitration.
    """

    weight: float = 1.0
    """Base selection weight (lower is preferred)."""

    proximity: Optional[int] = None
    """Optional distance metric (e.g., hops from cursor)."""

    layer_penalty: float = 0.0
    """Additional penalty applied when crossing behavior layers."""

    def total(self) -> float:
        """Return the aggregate score used for arbitration."""

        return self.weight + self.layer_penalty


@dataclass(slots=True, frozen=True)
class DependencyOffer:
    """DependencyOffer(requirement_id: UUID, dependency_id: UUID | None, cost: ProvisionCost)

    Lazy offer describing how to satisfy a :class:`Dependency` requirement.

    Why
    ----
    Captures the bare minimum metadata for selectors to arbitrate and accept an
    offer without forcing collectors to eagerly resolve providers.  The stored
    :class:`DependencyAcceptor` callback will pull registries/templates from the
    :class:`~tangl.vm.context.Context` when needed.

    Key Features
    ------------
    * **Deferred execution** – :meth:`accept` invokes the callback only when
      selected.
    * **Provenance tracking** – stores the originating provisioner, layer, and
      proximity hints.
    * **Context-aware** – resolves :class:`Requirement` and :class:`Dependency`
      graph items from the supplied context at call time.

    API
    ---
    - :attr:`requirement_id` – requirement backing the offer.
    - :attr:`dependency_id` – optional edge the requirement travelled on.
    - :attr:`cost` – :class:`ProvisionCost` used for arbitration.
    - :attr:`operation` – :class:`~tangl.vm.provision.requirement.ProvisioningPolicy`
      implied by this offer.
    - :attr:`layer_id` – emitting behavior layer (if any).
    - :attr:`source_provisioner_id` – provisioning capability that produced the
      offer.
    - :attr:`proximity` – cached hop-count or other distance hint.
    - :meth:`accept` – resolve the dependency via the lazy callback.
    """

    requirement_id: UUID
    dependency_id: Optional[UUID]
    cost: ProvisionCost
    acceptor: DependencyAcceptor = field(repr=False)
    operation: ProvisioningPolicy = ProvisioningPolicy.EXISTING
    layer_id: Optional[UUID] = None
    source_provisioner_id: Optional[UUID] = None
    proximity: Optional[int] = None

    def accept(self, *, ctx: Context, **kwargs) -> Optional[Node]:
        """Resolve the dependency by invoking the stored callback."""

        requirement = ctx.graph.get(self.requirement_id)
        if requirement is None:
            raise LookupError(
                f"Requirement {self.requirement_id} not present in planning graph"
            )

        dependency = (
            ctx.graph.get(self.dependency_id) if self.dependency_id is not None else None
        )
        return self.acceptor(
            ctx=ctx,
            requirement=requirement,
            dependency=dependency,
            **kwargs,
        )


@dataclass(slots=True, frozen=True)
class AffordanceOffer:
    """AffordanceOffer(affordance_id: UUID, requirement_id: UUID, cost: ProvisionCost)

    Lazy offer describing how to fulfill an :class:`Affordance` requirement.

    Why
    ----
    Mirrors :class:`DependencyOffer` for open-source affordances.  Selectors can
    optionally override the destination node when accepting the offer, keeping
    collectors decoupled from presentation logic.

    Key Features
    ------------
    * **Deferred execution** – :meth:`accept` pulls data from
      :class:`~tangl.vm.context.Context` at call time.
    * **Destination override** – accepts an optional ``destination`` keyword
      when callers want to force a specific target.
    * **Provenance tracking** – persists cost, layer, proximity, and source
      provisioner metadata.

    API
    ---
    - :attr:`affordance_id` – affordance edge backing the offer.
    - :attr:`requirement_id` – requirement bound to the affordance.
    - :attr:`cost` – :class:`ProvisionCost` used for arbitration.
    - :attr:`layer_id` – originating behavior layer identifier (optional).
    - :attr:`source_provisioner_id` – identifier for the provisioner emitting
      the offer.
    - :attr:`proximity` – distance hint for selectors.
    - :meth:`accept` – invoke the lazy callback, optionally overriding the
      destination.
    """

    affordance_id: UUID
    requirement_id: UUID
    cost: ProvisionCost
    acceptor: AffordanceAcceptor = field(repr=False)
    layer_id: Optional[UUID] = None
    source_provisioner_id: Optional[UUID] = None
    proximity: Optional[int] = None

    def accept(
        self,
        *,
        ctx: Context,
        destination: Optional[Node] = None,
        **kwargs,
    ) -> Optional[Edge]:
        """Resolve the affordance by invoking the stored callback."""

        affordance = ctx.graph.get(self.affordance_id)
        if affordance is None:
            raise LookupError(
                f"Affordance {self.affordance_id} not present in planning graph"
            )

        requirement = ctx.graph.get(self.requirement_id)
        if requirement is None:
            raise LookupError(
                f"Requirement {self.requirement_id} not present in planning graph"
            )

        if destination is None and getattr(affordance, "destination", None) is not None:
            destination = affordance.destination

        return self.acceptor(
            ctx=ctx,
            affordance=affordance,
            requirement=requirement,
            destination=destination,
            **kwargs,
        )
