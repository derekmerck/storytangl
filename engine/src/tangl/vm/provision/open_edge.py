# tangl/vm/open_edge.py
"""
Open edges: Dependencies and Affordances.

These edge types carry a :class:`~tangl.vm.planning.requirement.Requirement`
instead of a fixed endpoint, allowing the planner to *provision* structure
on demand at the frontier.

- :class:`Dependency` has a fixed **source** and an open **destination**.
- :class:`Affordance` has an open **source** and a fixed **destination**.
"""
from typing import Generic

from pydantic import Field, model_validator

from tangl.type_hints import StringMap, Identifier
from tangl.core.graph import Edge, Graph, Node
from .requirement import Requirement, NodeT, ProvisioningPolicy


# Provides the carrier mechanism to map requirements into the graph-topology.
# Alternatively, they could be represented as control-Nodes that weld together
# ingoing and outgoing edges under a given name.

# These are dynamic edges that can provoke a topological update via an 'update' event
# on their requirement component.  Need to be careful to watch that.

class Dependency(Edge, Generic[NodeT]):
    """
    Dependency(source: Node, requirement: Requirement)

    Why
    ----
    Represents a structural requirement flowing *out of* a node. The planner attempts
    to bind a provider node (destination) that satisfies the attached
    :class:`~tangl.vm.planning.requirement.Requirement`.

    Key Features
    ------------
    * **Open destination** – :attr:`source` is fixed, :attr:`destination` resolved dynamically.
    * **Requirement projection** – exposes requirement into the source namespace.
    * **Hard vs soft** – hard dependencies must be satisfied, soft ones may be waived.
    * **Provisioning** – unresolved dependencies at the frontier may trigger creation of new nodes.

    API
    ---
    - :attr:`requirement` – :class:`~tangl.vm.planning.requirement.Requirement` for the target node.
    - :attr:`destination` – bound provider node, or ``None`` until resolved.
    - :attr:`satisfied` – True if bound or soft.

    Notes
    -----
    Hard dependencies may include a fallback builder or waiver when no provider is available.
    """
    # dependencies project into the ns of their **source** as {self.label: self.destination}
    requirement: Requirement[NodeT]

    @property
    def destination(self) -> NodeT:
        return self.requirement.provider

    @destination.setter
    def destination(self, value: NodeT) -> None:
        self.requirement.provider = value

    @property
    def satisfied(self):
        return self.requirement.satisfied

    def get_selection_criteria(self):
        return self.requirement.get_selection_criteria()

    def satisfied_by(self, other: NodeT) -> bool:
        return self.requirement.satisfied_by(other)

    @classmethod
    def get_dependencies(cls, node: Node, **criteria):
        # subgraphs don't have edges_out
        return node.graph.find_edges(is_instance=cls, source=node, **criteria)
        return node.edges_out(is_instance=Dependency, **criteria)


class Affordance(Edge, Generic[NodeT]):
    """
    Affordance(destination: Node, requirement: Requirement)

    Why
    ----
    The inverse of :class:`Dependency`. Affordances make a destination node *available*
    whenever conditions are met, optionally pre‑creating a preferred source provider.

    Key Features
    ------------
    * **Open source** – :attr:`destination` is fixed, :attr:`source` resolved dynamically.
    * **Requirement projection** – exposes requirement into the destination namespace.
    * **Soft by default** – missing sources do not block resolution unless marked hard.
    * **Pre‑creation** – hard affordances may pre‑instantiate sources that will later link.

    API
    ---
    - :attr:`requirement` – :class:`~tangl.vm.planning.requirement.Requirement` describing the provider.
    - :attr:`source` – bound provider node, or ``None`` until resolved.
    - :attr:`satisfied` – True if bound or soft.

    Notes
    -----
    Affordances are tested against the frontier to reveal available resources or choices
    (e.g., characters, items, or conditional dialog options).
    """
    # affordances project into the ns of the **source** as {self.label: self.destination}

    requirement: Requirement[NodeT]
    # note, default `hard_requirement` should be False

    @property
    def source(self) -> NodeT:
        return self.requirement.provider

    @source.setter
    def source(self, value: NodeT) -> None:
        self.requirement.provider = value

    @property
    def satisfied(self):
        return self.requirement.satisfied

    def get_selection_criteria(self):
        return self.requirement.get_selection_criteria()

    def satisfied_by(self, other: NodeT) -> bool:
        return self.requirement.satisfied_by(other)
