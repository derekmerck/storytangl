from __future__ import annotations
from typing import Any, Optional, Generic, Iterator, Callable, TypeVar
from uuid import UUID
import functools
from collections import deque
import logging

from pydantic import Field, BaseModel, model_validator

from tangl.utils.is_valid_uuid import is_valid_uuid
from tangl.type_hints import UniqueLabel
from tangl.core import Entity, Registry

PATH_SEPARATOR = "/"
logger = logging.getLogger(__name__)

NodeT = TypeVar('NodeT', bound='Node')

class Node(Entity):
    """
    Nodes are the basic building blocks of the story structure in StoryTangl. They extend the
    :class:`~tangl.core.entity.Entity` class, adding hierarchical relationship capabilities and
    graph association.

    Key Features
    ------------
    * **Parent-Child Relationships**: Nodes can have bidirectional relationships with both parent and children nodes.
    * Graph Association: Each node is associated with a :class:`~tangl.core.graph.Graph` for efficient traversal and querying.
    * Path Generation: Nodes generate a unique :attr:`path` based on the node's position in the graphh hierarchy.
    * Dynamic Child Management: Methods for adding, removing, and finding child nodes.

    Usage
    -----
    .. code-block:: python

        from tangl.core.graph import Node, Graph

        # Create a graph and nodes
        graph = Graph()
        root = Node(label="root", graph=graph)
        child1 = Node(label="child1")
        child2 = Node(label="child2")

        # Build hierarchy
        root.add_child(child1)
        root.add_child(child2)

        # Access hierarchy
        print(child1.parent == root)  # True
        print(root.children)  # [child1, child2]
        print(child1.path)  # "root/child1"

    Mixin Classes
    -------------
    Like its base-class, Entity, Node is designed to be extended with various mixin-classes.
    These mixins add graph-related functionality to the Node, trading, and traversal.

    * :class:`~tangl.core.graph.handlers.HasScopedContext`: Adds cascading namespaces from parents.
    * :class:`~tangl.core.graph.handlers.Associating`: Adds transient connections the Node.
    * :class:`Traversable<tangl.core.graph.handlers.TraversableNode>`: Adds graph traversal functionality.

    Like Entity, they can self-cast by using the reserved kwarg :attr:`obj_cls` to reference any
    subclass of Node.

    Related Concepts
    ----------------
    * :class:`~tangl.core.graph.Edge` can be used to dynamically connect a node to another by reference.
    * :class:`SingletonNode<~tangl.core.graph.SingletonNode>` wraps a singleton with unique local vars and parent/children relationships.
    * :class:`~tangl.story.StoryNode` provides a common basis for all Story-related object.
    """
    graph: Graph = Field(None,       # default_factory=Graph,
                         repr=False,
                         exclude=True,
                         json_schema_extra={'cmp': False})
    """The Graph object collection that contains this node.  Omitted from serialization and comparison to prevent recursion issues."""

    anon: bool = False  # do not register with the graph

    @model_validator(mode="after")
    def _register_self(self):
        """If graph is passed in as an argument."""
        logger.debug(f"Checking {self!r} in graph {self.graph!r}")
        if self.graph is not None:
            if self.anon:
                logger.debug(f'Declining to register self {self!r}')
            else:
                self.graph.add(self)
                logger.debug(f'Registering self {self!r}')
        return self

    @model_validator(mode="after")
    def _set_anon_label(self):
        if self.anon:
            # label should be set by now
            self.label = f"anon-{self.label}"
        return self

    parent_id: UUID = None

    @model_validator(mode="after")
    def _add_self_to_parent(self):
        """If parent is passed in as an argument."""
        logger.debug(f"Checking {self.label} is parented by {self.parent_id} in graph {self.graph}")
        if self.parent_id is not None and self.graph is not None:
            logger.debug(f"Adding {self.label} to parent")
            self.parent.add_child(self)
        return self

    @property
    def parent(self) -> Optional[Node]:
        """Link to this node's parent."""
        if self.parent_id:
            return self.graph[self.parent_id]
        return None

    # @parent.setter
    # def parent(self, node: Node | UUID):
    #     if isinstance(node, UUID):
    #         # Passed UUID
    #         node = self.graph.get_node(node)
    #     if node and not isinstance(node, Node):
    #         # Bad type
    #         raise TypeError("Tried to set parent to non-node!")
    #     if node is self.parent:
    #         # Noop
    #         return
    #     # it's a valid new node
    #     if self.parent_id:
    #         # This sets self.parent = None as a side-effect
    #         self.parent.remove_child(self)
    #     if node and not self.anon:
    #         node.add_child(self)

    @property
    def ancestors(self) -> list[Node]:
        root = self
        res = [ root ]
        while root.parent:
            root = root.parent
            res.append(root)
        return [ *reversed(res) ]  # Reverse list so it starts from root

    @property
    def path(self) -> UniqueLabel:
        return PATH_SEPARATOR.join([ a.label for a in self.ancestors ])

    @property
    def root(self):
        root = self
        while root.parent:
            root = root.parent
        return root

    children_ids: list[UUID] = Field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return [ self.graph[v] for v in self.children_ids ]

    def add_child(self, child: NodeT, as_parent: bool = True):
        if child.graph and child.graph is not self.graph:
            raise ValueError("Cannot add a node from a different graph.")
        elif not child.graph:
            self.graph.add(child)
        if child.uid not in self.children_ids:
            if as_parent:
                # Allow adding links as peers
                child.parent_id = self.uid
            # check for cycles
            if child.detect_cycle():
                raise ValueError("Adding this node would create a cycle")
            self.children_ids.append(child.uid)
            return
        logger.warning("Tried to re-add a child node")

    def remove_child(self, child: NodeT, unlink: bool = False):
        if self.anon:
            raise RuntimeError('Cannot remove child from anonymous node!')
        if child.uid in self.children_ids:
            if child.parent_id is self.uid:
                # Child was associated hierarchically, remove self as parent.
                # If it still had its own parent, leave it alone.
                child.parent_id = None
            self.children_ids.remove(child.uid)
            if unlink:
                # Use this cautiously -- there is no link counting, so if the child is
                # referenced by multiple nodes, they will error when trying to access it.
                # This also unlinks held references (i.e. grandchildren) recursively.
                child.graph.remove(child)
        else:
            logger.warning("Tried to remove a non-child node")

    def remove_children(self, unlink: bool = False):
        for child in self.children:
            self.remove_child(child, unlink=unlink)

    def find_children(self, **criteria) -> list[Node]:
        logger.debug(f"Finding children in {self.children} matching {criteria}")
        return self.filter_by_criteria(self.children, **criteria)

    def find_child(self, **criteria) -> Optional[Node]:
        # possibly want a flag to shuffle if we find more than one?
        logger.debug(f"Finding first child in {self.children} matching {criteria}")
        return self.filter_by_criteria(self.children, return_first=True, **criteria)

    def __getattr__(self, name):
        # provide accessors for 'dot' addressing children by label
        child_map = { k.label: k for k in self.children }
        if name in child_map:
            child = child_map[name]
            if isinstance(child, Edge):
                child = child.successor
            return child
        return super().__getattr__(name)

    def __contains__(self, item):
        """
        Support `<tag> in Node()` or `<child_id> in Node()`.

        This can be extended by other classes that want to add their own attributes to `__contains__`.
        """
        if isinstance(item, str) and is_valid_uuid(item):
            item = UUID(item)
        if isinstance(item, str) and self.has_tags(item):
            return True
        if isinstance(item, UUID) and item in self.children_ids:
            return True
        if isinstance(item, str) and item in [ch.label for ch in self.children]:
            return True
        return super().__contains__(item)

    def detect_cycle(self) -> bool:
        """Detect if adding this node would create a cycle"""
        current = self
        visited = {self.uid}
        while current.parent:
            current = current.parent
            if current.uid in visited:
                return True
            visited.add(current.uid)
        return False

    def traverse_dfs(self) -> Iterator[NodeT]:
        """Depth-first traversal of node tree"""
        yield self
        for child in self.children:
            yield from child.traverse_dfs()

    def traverse_bfs(self) -> Iterator[NodeT]:
        """Breadth-first traversal of node tree"""
        queue = deque([self])
        while queue:
            node = queue.popleft()
            yield node
            queue.extend(node.children)

    def visit(self, visitor: Callable[[NodeT], None]) -> None:
        """Apply visitor function to this node and all children"""
        visitor(self)
        for child in self.children:
            child.visit(visitor)

    def move_to(self, new_parent: NodeT, index: int = None) -> None:
        """
        Move this node and its subtree to a new parent.
        Optionally specify insertion index.
        """
        if self.detect_cycle():
            raise ValueError("Moving node would create cycle")

        old_parent = self.parent
        if old_parent:
            old_parent.remove_child(self)

        if index is None:
            new_parent.add_child(self)
        else:
            new_parent.children_ids.insert(index, self.uid)
            self.parent_id = new_parent.uid
            self.graph = new_parent.graph

    @property
    def siblings(self) -> list[NodeT]:
        """Get all siblings of this node"""
        if not self.parent:
            return []
        return [child for child in self.parent.children if child != self]

    @property
    def leaf_nodes(self) -> list[NodeT]:
        """Get all leaf nodes in subtree"""
        leaves = []
        for node in self.traverse_dfs():
            if not node.children:
                leaves.append(node)
        return leaves

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault("exclude", set())
        kwargs['exclude'].add('graph')  # avoid recursion
        return super().model_dump(*args, **kwargs)


class Edge(Node):

    parent_id: UUID = Field(..., alias="predecessor_id")  # required now
    successor_id: UUID = None

    @property
    def predecessor(self) -> Node:
        return self.parent

    @property
    def successor(self) -> Optional[Node]:
        return self.graph.get(self.successor_id, None)

# Side note, the 'Graph' class was originally called 'Context' and was derived from
# the context manager directly.  This functionality was factored out into the service
# layer after 2.3.

class Graph(Registry[NodeT], Generic[NodeT]):
    """
        The Graph class serves as a central repository for all :class:`Nodes<tangl.core.graph.node.Node>`
        within a story. It manages the relationships between nodes and provides methods for efficient
        node retrieval and traversal.

        Key Features
        ------------
        * **Node Registry**: The Graph maintains a flat dictionary of nodes and has methods for adding, removing, and retrieving items.  Nodes added to the graph must have unique UUIDs and paths.
        * **Efficient Lookup**: Supports lookup by UUID, label, or path.
        * **Filtering**: Ability to find nodes based on various criteria like class type or tags.
        * **Traversal Support**: Provides the foundation for story traversal mechanics.

        Usage
        -----
        .. code-block:: python

            from tangl.core.graph import Graph, Node

            # Create a graph
            graph = Graph()

            # Add nodes to the graph
            root = Node(label="root", graph=graph)
            child1 = Node(label="child1")
            child2 = Node(label="child2")

            root.add_child(child1)
            root.add_child(child2)

            # Retrieve nodes
            retrieved_node = graph.get(child1.uid)
            print(retrieved_node == child1)  # True

            # Find nodes
            special_nodes = graph.find(tags={"special"})

        Mixin Classes
        -------------
        The Graph class is designed to be extended for specific story management needs.

        * :class:`Traversable<tangl.core.graph.handlers.TraversableGraph>`: Adds graph traversal functionality.
        """

    def add(self, node: NodeT, **kwargs):
        if getattr(node, "anon", False):
            # anonymous nodes don't get added to the graph
            return
        node.graph = self
        super().add(node, **kwargs)
        self.invalidate_by_path_cache()
        # this will throw an exception if trying to re-add but node.graph is not already set to self

    def remove(self, value: NodeT):
        """
        This is _not_ guaranteed to find all references nor to preserve references
        to children with multiple associations.

        It is provided purely for completeness and testing purposes.
        """
        # recursively unlink children
        for child in value.children:
            value.remove_child(child, unlink=True)
        # unlink from parent node
        if value.parent is not None:
            value.parent.remove_child(value)
        # unlink from self
        super().remove(value)
        self.invalidate_by_path_cache()

    def __getitem__(self, key: UUID | UniqueLabel):
        if isinstance(key, UniqueLabel):
            if x := self.find_one(path=key):
                return x
            # We don't want to fallback on search by label in super(), as label is not guaranteed unique
            raise KeyError(f"Key {key} is not a registered unique path in {self}")
        return super().__getitem__(key)

    def __contains__(self, item: Entity | UUID | UniqueLabel) -> bool:
        if isinstance(item, str) and is_valid_uuid(item):
            item = UUID(item)
        if isinstance(item, UniqueLabel):
            return item in self.nodes_by_path
        return super().__contains__(item)

    @functools.cached_property
    def nodes_by_path(self) -> dict[str, NodeT]:
        return { v.path: v for v in self.values() }

    def invalidate_by_path_cache(self):
        if hasattr(self, "nodes_by_path"):
            delattr(self, "nodes_by_path")