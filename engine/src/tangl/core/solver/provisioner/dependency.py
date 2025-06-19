from typing import Generic, TypeVar, Optional
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap, Identifier
from tangl.core.entity import Edge, Node
from tangl.core.handler import Satisfiable
from tangl.core.handler import Predicate


##### OPEN EDGES ####

NodeT = TypeVar('NodeT', bound=Node)

class DependencyEdge(Satisfiable, Edge[Node, Optional[NodeT]], Generic[NodeT]):
    # dynamic link concepts, green
    """
    Dependencies are edges with defined sources and open destinations.  For example, a
    node might _require_ a green friend node before it can be used.

    Open/unresolved dependencies at the solution frontier will be provisioned, if possible,
    by the resolver.

    Dependencies may be hard (default, node is unsatisfied if they cannot be resolved) or soft
    (provide if possible), and they may be restricted to only existing nodes, or using indirect
    providers to create and introduce a new node.

    Hard dependencies may also carry their own fallback builder for when no satisfactory
    pre-existing direct or indirect provider is available.
    """
    dest_id: Optional[UUID] = Field(None)  # Optional now
    dest_ref: Optional[Identifier] = None  # sugar for criteria={'alias': ref}
    dest_criteria: StringMap = Field(default_factory=dict)
    dest_predicate: Predicate = None
    is_unresolvable: bool = False  # tried to resolve but failed

    # hard_requirement: bool = True
    # fallback_builder: Handler = None

    def is_satisfied_by(self, provider: Node) -> bool:
        # todo: annotate for candidate.has_cls(NodeT), probably like with wrapped singleton
        return provider.matches(has_cls=NodeT, **self.dest_criteria)

    @property
    def is_resolved(self) -> bool:
        return self.dest is not None

class AffordanceEdge(Satisfiable, Edge[Optional[NodeT], Node], Generic[NodeT]):
    """
    Affordances are edges with defined destinations and open sources.  For example, a node may
    be available from any other node that has a green friend node available.

    Affordances are the inverse of a dependency.  A _satisfied_ dependency of node becomes a
    _satisfied_ affordance for the destination, and vice versa.

    Affordances represent nodes that can be made available whenever conditions are met.

    Like dependencies, they can be marked soft (default, provide if possible) or hard (critical,
    paths will be unavailable if they cannot be provided).

    Open affordances at the frontier will be provisioned, if possible.  _All_ affordances in
    the scope (i.e., visible to this node) will be tested _against_ the frontier to see if
    they can be linked. This is usually to present a flexible choice or introduce a resource
    asap.  Hard affordances in the scope with a satisfied indirect provider (i.e., a new source
    resource can be immediately linked) may also create and link a new source.
    """
    # open source
    source_id: Optional[UUID] = Field(None)  # Optional now
    source_ref: Optional[Identifier] = None  # sugar for criteria={'alias': ref}
    source_criteria: StringMap = Field(default_factory=dict)
    source_predicate: Predicate = None
    is_unresolvable: bool = False  # tried to resolve but failed

    def is_satisfied_by(self, provider: Node) -> bool:
        # todo: how do we annotate for candidate.has_cls(NodeT)
        return provider.matches(has_cls=NodeT, **self.source_criteria)

    @property
    def is_resolved(self) -> bool:
        return self.source is not None

    @property
    def is_resolvable(self):
        return True
