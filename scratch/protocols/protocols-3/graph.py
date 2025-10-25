from __future__ import annotations
from typing import Type, TypeVar, Iterable, Generic, Optional

from .type_hints import Identifier, StringMap
from .entity import Entity, Registry, Singleton, TaskHandler, Criteria, EntityMixin

# -----------------
# Graph/Node-related Type Hints
# -----------------
NodeTemplate = StringMap  # instantiation template

# -----------------
# Graph, Node, Wrapped Singletons
# -----------------
class Graph(Entity):
    nodes: Registry[Node]
    cursor: VisitableNode

class GraphManager(TaskHandler):
    graph: Graph
    def find_nodes(self, **criteria) -> Iterable[Node]: ...
    def find_node(self, **criteria) -> Node: ...

class Node(Entity):
    graph: Graph
    parent: Entity
    children: list[Entity]

class NodeManager(TaskHandler):
    node: Node

    @property
    def root(self) -> Node: ...
    @property
    def ancestors(self) -> Iterable[Node]: ...

    def add_child(self, child: Entity): ...
    def discard_child(self, child: Entity): ...

    def find_children(self, **criteria) -> Iterable[Node]: ...
    def find_child(self, **criteria) -> Node: ...

WST = TypeVar("WST", bound=Singleton)

class WrappedSingletonNode(Node, Generic[WST]):
    wrapped_cls: Type[WST]
    def get_reference_singleton(self) -> WST: ...

# -----------------
# Associations and Edges
# -----------------
NodeMixin = Node

AET = TypeVar("AET", bound=Node)  # Associating entity type

class HasAssociates(NodeMixin, Generic[AET]):
    @property
    def associates(self) -> Iterable[AET]: ...

class AssociationHandler(TaskHandler):
    # May be 1-way or 2-way association, e.g. singleton association with
    # a node is 1-way, node parent/child is 2-way
    # Mostly in-game asset handling and indirect linking like roles

    @classmethod
    def can_associate_with(cls, node: Node, other: AET) -> bool: ...

    @classmethod
    def associate_with(cls, node: Node, other: AET): ...

    @classmethod
    def can_disassociate_from(cls, node: Node, other: AET) -> bool: ...

    @classmethod
    def disassociate_from(cls, node: Node, other: AET): ...

class DynamicallyAssociatingEntity(EntityMixin, Generic[AET]):
    # May be 1-way or 2-way association
    applies_to: Criteria
    def check_applies_to(self, other: AET) -> bool: ...
    auto_attach: bool     # otherwise it must be manually associated
    auto_detach: bool     # otherwise it is permanent until manual disassociation

class HasDynamicAssociates(HasAssociates):
    def update_dynamic_associations(self): ...

ST = TypeVar("ST", bound=HasAssociates)   # successor type

class Edge(Entity, Generic[ST]):
    graph: Graph
    predecessor: Node
    successor: ST

class DynamicEdge(Edge, Generic[ST]):
    successor_identifier: Identifier = None  # get
    successor_criteria: Criteria = None      # find
    successor_template: NodeTemplate = None  # create

    successor: ST = None    # None until resolved

    def resolve_successor(self) -> ST: ...

# -----------------
# Transit Edges and Visitable Nodes
# -----------------
class VisitableNode(NodeMixin):
    @property
    def transits(cls, **criteria) -> Iterable[TransitEdge]: ...

class VisitableNodeHandler(TaskHandler):
    @classmethod
    def enter(cls, node: Node, arrival_edge: TransitEdge = None, **kwargs) -> Optional[TransitEdge]: ...

    @classmethod
    def exit(cls, node: Node, exit_edge: TransitEdge = None, **kwargs) -> Optional[TransitEdge]: ...

class TransitEdge(Edge[VisitableNode]):

    predecessor: VisitableNode
    successor: VisitableNode

class GraphTraversalHandler(TaskHandler):

    @classmethod
    def follow_edge(cls, edge: TransitEdge): ...
    # Attempt to exit predecessor and enter successor, if it returns an edge, follow it

    @classmethod
    def enter_node(cls, node: VisitableNode, arrival_edge: TransitEdge = None) -> Optional[TransitEdge]: ...
    # returns pre-redirects or continues

    @classmethod
    def exit_node(cls, node: VisitableNode, exit_edge: TransitEdge = None) -> Optional[TransitEdge]: ...
    # returns post-redirects
