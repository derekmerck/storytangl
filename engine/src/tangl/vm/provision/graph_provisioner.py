"""Graph-scoped provisioner that surfaces lazy dependency offers."""

from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING
from uuid import UUID

from tangl.core import Entity
from tangl.core.behavior import HandlerLayer
from tangl.core.graph import Graph, Node

from .offers import DependencyOffer, ProvisionCost
from .requirement import Requirement, ProvisioningPolicy

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from tangl.vm.context import Context
    from .open_edge import Dependency


_LAYER_PROXIMITY: dict[HandlerLayer | None, int] = {
    None: 0,
    HandlerLayer.INLINE: 0,
    HandlerLayer.LOCAL: 0,
    HandlerLayer.AUTHOR: 1,
    HandlerLayer.APPLICATION: 2,
    HandlerLayer.SYSTEM: 3,
    HandlerLayer.GLOBAL: 4,
}

_LAYER_PENALTY: dict[HandlerLayer | None, float] = {
    None: 0.0,
    HandlerLayer.INLINE: 0.0,
    HandlerLayer.LOCAL: 0.0,
    HandlerLayer.AUTHOR: 0.25,
    HandlerLayer.APPLICATION: 0.5,
    HandlerLayer.SYSTEM: 0.75,
    HandlerLayer.GLOBAL: 1.0,
}


class GraphProvisioner(Entity):
    """Emit dependency offers for nodes already present in a graph."""

    graph: Graph
    layer: HandlerLayer = HandlerLayer.LOCAL
    layer_id: Optional[UUID] = None
    cost_weight: float = 1.0

    def iter_dependency_offers(
        self,
        *,
        requirement: Requirement,
        dependency: "Dependency" | None = None,
    ) -> Iterator[DependencyOffer]:
        if not self._supports_requirement(requirement):
            return

        for node in self._iter_matches(requirement):
            yield self._build_offer(requirement, node, dependency)

    def get_dependency_offers(
        self,
        *,
        requirement: Requirement,
        dependency: "Dependency" | None = None,
    ) -> list[DependencyOffer]:
        return list(self.iter_dependency_offers(requirement=requirement, dependency=dependency))

    # ------------------------------------------------------------------
    # Helpers
    def _supports_requirement(self, requirement: Requirement) -> bool:
        if not requirement.identifier and not requirement.criteria:
            return False
        if requirement.policy is ProvisioningPolicy.NOOP:
            return False
        return bool(requirement.policy & ProvisioningPolicy.EXISTING)

    def _iter_matches(self, requirement: Requirement) -> Iterable[Node]:
        criteria = requirement.get_selection_criteria()
        if not criteria:
            return ()
        return self.graph.find_nodes(**criteria)

    def _build_offer(
        self,
        requirement: Requirement,
        node: Node,
        dependency: "Dependency" | None,
    ) -> DependencyOffer:
        proximity = _LAYER_PROXIMITY.get(self.layer, 0)
        cost = ProvisionCost(
            weight=self.cost_weight,
            proximity=proximity,
            layer_penalty=_LAYER_PENALTY.get(self.layer, 0.0),
        )

        def acceptor(
            *,
            ctx: "Context",
            requirement: Requirement,
            dependency: "Dependency" | None = None,
            **_: object,
        ) -> Node:
            return node

        return DependencyOffer(
            requirement_id=requirement.uid,
            dependency_id=dependency.uid if dependency is not None else None,
            cost=cost,
            operation=ProvisioningPolicy.EXISTING,
            acceptor=acceptor,
            layer_id=self.layer_id,
            source_provisioner_id=self.uid,
            proximity=proximity,
        )

