# engine/src/tangl/vm/planning/provisioner.py
from __future__ import annotations
from uuid import UUID
from typing import Iterator, TYPE_CHECKING

from pydantic import Field

from tangl.core import Entity, Node, Edge, Graph, Registry
from .requirement import Requirement
from .offer import ProvisionOffer

if TYPE_CHECKING:
    from tangl.vm import Context


class Provisioner(Entity):
    """
    Capability that generates offers to satisfy requirements.
    """
    priority: int = 50

    def get_offers(self, requirement: Requirement = None, **kwargs) -> Iterator[ProvisionOffer]:
        """
        Generate offers.

        Args:
            requirement: If provided, generate responsive offers.
                        If None, generate affordance offers (broadcast).
        """
        raise NotImplementedError


class ProvisionOffer:
    """
    A concrete offer to provide a resource.
    """
    provider_id: UUID
    label: str | None = None  # For uniqueness tracking
    cost: float = 1.0
    proximity: int = 999  # Set by planning system

    # Back-reference to source (set by planning)
    source_provisioner: Provisioner | None = None

    def available(self, ns: dict) -> bool:
        """Check if offer is valid in this namespace."""
        return True

    def satisfied_by(self, node: Node) -> bool:
        """Check if this affordance applies to node."""
        # Override for affordance offers
        return False

    def accept(self, *, ctx: Context) -> Node | Edge:
        """
        Materialize the offer.

        For responsive offers: returns provider Node
        For affordance offers: returns affordance Edge
        """
        raise NotImplementedError


# Concrete implementations

class AffordanceOffer(ProvisionOffer):
    """Proactive offer that broadcasts availability."""

    target_tags: set[str] = Field(default_factory=set)

    def satisfied_by(self, node: Node) -> bool:
        """Check if node has matching tags."""
        if not self.target_tags:
            return True  # Universal affordance
        return bool(self.target_tags & node.tags)

    def accept(self, *, ctx: Context) -> Edge:
        """Create an affordance edge."""
        from tangl.vm.provision import Affordance

        provider = ctx.graph.get(self.provider_id)

        aff = Affordance(
            graph=ctx.graph,
            label=self.label or f"aff_{provider.label}",
            destination_id=provider.uid,
            sources=[]  # Will be populated by caller
        )

        return aff


class DependencyOffer(ProvisionOffer):
    """Reactive offer for a specific requirement."""

    requirement_id: UUID

    def accept(self, *, ctx: Context) -> Node:
        """Return provider node (or instantiate if needed)."""
        provider = ctx.graph.get(self.provider_id)

        if provider is None:
            # Instantiate from template if needed
            provider = self._instantiate_provider(ctx)

        return provider

    def _instantiate_provider(self, ctx: Context) -> Node:
        """Override for template-based provisioning."""
        raise NotImplementedError


# Example concrete provisioner

class RegistryProvisioner(Provisioner):
    """Offers nodes from a registry based on tag matching."""

    registry: Registry
    required_tags: set[str] = Field(default_factory=set)
    offer_as_affordances: bool = False  # Broadcast or respond to deps?

    def get_offers(self, requirement: Requirement = None, **kwargs) -> Iterator[ProvisionOffer]:
        """Generate offers from registry."""

        candidates = self.registry.find_all(has_tags=self.required_tags)

        if requirement is None and self.offer_as_affordances:
            # Broadcast affordance offers
            for candidate in candidates:
                yield AffordanceOffer(
                    provider_id=candidate.uid,
                    label=candidate.label,
                    target_tags=self.required_tags,
                    cost=1.0
                )

        elif requirement is not None:
            # Responsive dependency offers
            for candidate in candidates:
                # Check if candidate matches requirement
                if requirement.satisfied_by(candidate):
                    yield DependencyOffer(
                        provider_id=candidate.uid,
                        requirement_id=requirement.uid,
                        label=candidate.label,
                        cost=1.0
                    )

