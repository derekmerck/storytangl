# tangl/vm/open_edge.py
from typing import Generic

from tangl.core.graph import Edge, Graph
from .requirement import Requirement, NodeT

# Provides the carrier mechanism to map requirements into the graph-topology.
# Alternatively, they could be represented as control-Nodes that weld together
# ingoing and outgoing edges under a given name.

# These are dynamic edges that can provoke a topological update via an 'update' event
# on their requirement component.  Need to be careful to watch that.

class Dependency(Edge, Generic[NodeT]):
    """
    Dependencies are edges with defined sources and open destinations.  For example, a
    node might _require_ a green friend node before it can be used.

    Open/unresolved dependencies at the solution frontier will be provisioned, if possible,
    by the resolver.

    Dependencies may be hard (default, node is unsatisfied if they cannot be resolved) or soft
    (provide if possible), and they may be restricted to only existing nodes, or using indirect
    providers to create and introduce a new node.

    Hard dependencies may also carry their own fallback builder or waiver for when no
    satisfactory pre-existing direct or indirect provider is available.
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


class Affordance(Edge, Generic[NodeT]):
    """
    Affordances are edges with defined destinations and open sources.  For example, a node may
    be available from any other node that has a green friend node available.

    Affordances are the inverse of a dependency.  A _satisfied_ dependency of node becomes a
    _satisfied_ affordance for the destination, and vice versa.

    Affordances represent nodes that become available whenever conditions are met.

    Like dependencies, they can be marked soft (default, provide if possible) or hard (critical,
    paths will be unavailable if resources cannot be created or linked).

    _All_ affordances in the scope (i.e., visible to this node) will be tested _against_ the
    frontier to see if they can be linked. This is usually to present choices or resources that
    follow an entity, like a character avatar that is always available in that character's dialogs,
    or choices that become active whenever specific conditions are met.

    Hard affordances in the scope with a satisfied indirect provider (i.e., a new source
    resource can be immediately linked) may also pre-create a source that will have priority
    when linked later.  For example, to pre-cast a particular character that will be available
    everywhere in a scene.
    """
    # affordances project into the ns of the **destination** as {self.label: self.source}

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
