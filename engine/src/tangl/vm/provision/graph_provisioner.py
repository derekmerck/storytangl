"""Graph-aware provisioner that surfaces existing node offers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Sequence, TYPE_CHECKING
from uuid import UUID, uuid4

from tangl.core.graph import Graph, Node

from .offers import DependencyOffer, DependencyAcceptor, ProvisionCost
from .requirement import Requirement, ProvisioningPolicy

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from tangl.vm.context import Context
    from .open_edge import Dependency


@dataclass(slots=True)
class GraphProvisioner:
    """Collect existing graph nodes as dependency offers."""

    graphs: Sequence[Graph] = field(default_factory=tuple)
    uid: UUID = field(default_factory=uuid4, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "graphs", tuple(self.graphs))

    def iter_dependency_offers(
        self,
        requirement: Requirement,
        *,
        dependency: Dependency | None = None,
        ctx: Context | None = None,
    ) -> Iterator[DependencyOffer]:
        """Yield dependency offers that attach existing nodes."""

        criteria = requirement.get_selection_criteria()
        if not criteria:
            return

        seen_nodes: set[UUID] = set()
        for proximity, layer_graph in enumerate(
            self._iter_graph_layers(requirement=requirement, ctx=ctx)
        ):
            for node in layer_graph.find_nodes(**criteria):
                if node.uid in seen_nodes:
                    continue
                seen_nodes.add(node.uid)
                yield self._build_offer(
                    requirement=requirement,
                    dependency=dependency,
                    node=node,
                    layer_graph=layer_graph,
                    proximity=proximity,
                )

    def _iter_graph_layers(
        self,
        *,
        requirement: Requirement,
        ctx: Context | None,
    ) -> Iterator[Graph]:
        seen: set[UUID] = set()
        ordered: list[Graph] = []

        def add_graph(graph: Graph | None) -> None:
            if graph is None or graph.uid in seen:
                return
            seen.add(graph.uid)
            ordered.append(graph)

        for graph in self.graphs:
            add_graph(graph)
        add_graph(requirement.graph)
        if ctx is not None:
            add_graph(getattr(ctx, "graph", None))

        yield from ordered

    def _build_offer(
        self,
        *,
        requirement: Requirement,
        dependency: Dependency | None,
        node: Node,
        layer_graph: Graph,
        proximity: int,
    ) -> DependencyOffer:
        return DependencyOffer(
            requirement_id=requirement.uid,
            dependency_id=getattr(dependency, "uid", None),
            cost=self._cost_for_layer(proximity),
            operation=ProvisioningPolicy.EXISTING,
            acceptor=self._make_acceptor(node),
            layer_id=layer_graph.uid,
            source_provisioner_id=self.uid,
            proximity=proximity,
        )

    @staticmethod
    def _make_acceptor(node: Node) -> DependencyAcceptor:
        node_ref = node
        node_id = node.uid

        def acceptor(
            *,
            ctx: Context,
            requirement: Requirement,
            dependency: Dependency | None = None,
            **_: object,
        ) -> Node | None:
            if node_ref.graph is ctx.graph:
                return node_ref
            return ctx.graph.get(node_id)

        return acceptor

    @staticmethod
    def _cost_for_layer(proximity: int) -> ProvisionCost:
        return ProvisionCost(weight=1.0 + float(proximity), proximity=proximity)


__all__ = ["GraphProvisioner"]
