from __future__ import annotations
from uuid import UUID
from typing import Callable, Type, TypeVar, Self, Optional, TYPE_CHECKING
import logging

import pydantic
from pydantic import Field

from tangl.type_hints import UniqueLabel, Tags, Uid
from ..entity import Entity
from .graph import Graph, GraphType

if TYPE_CHECKING:
    from .factory import GraphFactory

logger = logging.getLogger('tangl.node')
logger.setLevel(logging.WARNING)

class Node(Entity):
    """
    The Node class represents a basic building block of a story or scene tree.
    Nodes represent narrative beats, characters, locations, etc.
    Each node is inherently part of a graph, which is leveraged to provide a central index for all node relationships.

    Each Node has a unique identifier (uid), a public name (label), an optional parent Node and can have multiple child Nodes.

    :Attributes:
      :ivar UUID uid: A unique identifier for this Node.
      :ivar str label: A short identifier derived from a template name or its guid.
      :ivar Node parent: The parent Node of this Node.
      :ivar Node root: The root Node of this Node's tree.
      :ivar str path: The path from the root Node to this Node (used as a unique label).
      :ivar Graph Graph: The Graph object collection that contains this Node.  Omitted from serialization to prevent recursion issues.
      :ivar set tags: String or Enum tags associated with the Node.
      :ivar set children: A list of child Nodes.
      :ivar: UUID parent_id children_ids: Enable tree-like structuring within the graph by tracking relationships through identifiers rather than direct references, simplifying serialization.

    :Methods:
      - `add_child`, `remove_child`: Manage hierarchical relationships, facilitating dynamic narrative branching.
      - `find_children`, `find_child`: Offer search capabilities within a node's descendants, supporting complex narrative logic.
      - `ancestors`, `path`: Provide navigation and lookup capabilities within the graph's structure, essential for tracing narrative paths and relationships.

    :Mixin Classes:

    Like its base-class, Entity, Node is designed to be extended with various mixin-classes. These mixins add graph-related functionality to the Node, trading, and traversal.

    - :class:`~tangl.graph.mixins.Associating`: Adds transient connections the Node.
    - :class:`~tangl.graph.mixins.Trader`: Adds Node-trading functionality to the Node.
    - :class:`~tangl.graph.mixins.Traversable`: Adds graph traversal functionality to the Node.
    - :class:`~tangl.graph.mixins.Plugins`: Adds plugin hooks to various Entity and Node features.

    Nodes can be factoried from various representations with a GraphFactory.  Like Entity, they
    can self-cast by using the reserved kwarg 'obj_cls' to reference any subclass of Node.

    Relies on Pydantic initialization for serialization and deserialization.

    :Example:

    >>> root = Node(label="root")
    >>> child1 = Node(label="child1")
    >>> root.add_child(child1)
    """
    # :raises **KeyError**: On creation, if a child with the same uid already exists in the children dictionary.
    # :raises **AttributeError**: On creation, if the source dict contains keys that are not mappable to Node attributes

    graph: GraphType = Field(default_factory=Graph,
                             repr=False,
                             exclude=True,
                             json_schema_extra={'cmp': False})

    @pydantic.model_validator(mode='after')
    def _register_self_with_graph(self):
        if self.graph:
            logger.debug(f'registering self {self.label, self.__class__}')
            self.graph.add_node(self)
        return self

    parent_id: Optional[UUID] = None
    @property
    def parent(self) -> Node:
        if self.parent_id:
            return self.graph.get_node(self.parent_id)

    @parent.setter
    def parent(self, node: Node | UUID):
        if isinstance(node, UUID):
            # Passed UUID
            node = self.graph.get_node(node)
        if node and not isinstance(node, Node):
            # Bad type
            raise TypeError("Tried to set parent to non-node!")
        if node is self.parent:
            # Noop
            return
        # it's a valid new node
        if self.parent_id:
            # This sets self.parent = None as a side-effect
            self.parent.remove_child(self)
        if node:
            node.add_child(self)

    # todo: does this need to be a list to allow indexing by order?
    children_ids: set[UUID] = Field(default_factory=set)
    @property
    def children(self) -> list[Node]:
        return list(self.graph.get_node(node_id) for node_id in self.children_ids)

    def add_child(self, node: NodeType, as_parent: bool = True):
        if as_parent:
            node.parent_id = self.uid
        self.children_ids.add(node.uid)
        self.graph.add_node(node)

    def remove_child(self, node: NodeType, delete_node: bool = False):
        if node.uid not in self.children_ids:
            print( node.uid, self.children_ids )
            raise ValueError("Improper attempt to remove non-child node")
        self.children_ids.remove(node.uid)
        if hasattr(node, "parent_id") and node.parent_id and self.uid == node.parent_id:
            node.parent_id = None
        if delete_node:
            self.graph.remove_node(node)

    def find_children(self,
                      node_cls: Type[NodeType] = None,
                      filt: Callable = None,
                      has_tags: Tags = None,
                      sort_key: str = None) -> list[NodeType]:
        children = self.graph._find_nodes(self.children,
                                          node_cls=node_cls,
                                          filt=filt,
                                          has_tags=has_tags)
        if sort_key:
            children.sort(key=lambda x: getattr(x, sort_key))
        return children

    def discard_children(self,
                         node_cls: Type[NodeType] = None,
                         filt: Callable = None,
                         has_tags: Tags = None,
                         delete_node: bool = False):
        children = self.graph._find_nodes(self.children,
                                          node_cls=node_cls,
                                          filt=filt,
                                          has_tags=has_tags)
        for child_node in children:
            self.remove_child(child_node, delete_node=delete_node)

    def find_child(self,
                   node_cls: Type[NodeType] = None,
                   filt: Callable = None,
                   has_tags: Tags = None,
                   sort_key: str = None) -> NodeType:
        res = self.find_children(node_cls=node_cls,
                                 filt=filt,
                                 has_tags=has_tags,
                                 sort_key=sort_key)
        if res:
            return res[0]

    def get_child(self, key: UniqueLabel | UUID):
        for ch in self.children:
            if ch.label == key or ch.uid == key:
                return ch
        return None

    @property
    def root(self) -> NodeType | None:
        node = self
        while node.parent:
            node = node.parent
        return node

    def ancestors(self):
        node = self
        ancestors = [node]
        while node.parent:
            node = node.parent
            ancestors.append(node)
        return ancestors

    @property
    def path(self) -> UniqueLabel:
        labels = [a.label for a in reversed( self.ancestors() ) ]
        return "/".join(labels)

    @property
    def factory(self) -> GraphFactory:
        return self.graph.factory

    def __contains__(self, item):
        """
        Support `<tag> in Node()` or `<child_id> in Node()`.

        This can be extended by other classes that want to add their own attributes to `__contains__`.
        """
        if isinstance(item, str) and self.has_tags(item):
            return True
        if isinstance(item, Uid) and item in self.children_ids:
            return True
        if isinstance(item, str) and item in [ ch.label for ch in self.children ]:
            return True
        return super().__contains__(item)

NodeType = TypeVar("NodeType", bound=Node)
