from __future__ import annotations
from typing import Any, Optional, Iterator, Callable, TypeVar, TYPE_CHECKING, Self
from uuid import UUID
import functools
from collections import deque
import logging

from pydantic import Field, BaseModel, model_validator, field_validator

from tangl.utils.is_valid_uuid import is_valid_uuid
from tangl.type_hints import UniqueLabel
from tangl.core import Entity, Registry
from .graph import Graph

if TYPE_CHECKING:
    from .edge import Edge

PATH_SEPARATOR = "/"
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

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
    * :class:`Token<~tangl.core.graph.Token>` wraps a singleton with unique local vars and parent/children relationships.
    * :class:`~tangl.story.StoryNode` provides a common basis for all Story-related object.
    """
    graph: Graph = Field(None,
                         repr=False,
                         exclude=True,
                         json_schema_extra={'cmp': False})
    """The Graph object collection that contains this node.  Omitted from serialization and comparison to prevent recursion issues."""

    anon: bool = False  # do not register with the graph, transient node that can be garbage collected

    @model_validator(mode="after")
    def _setup_graph_and_register(self):
        # Create default graph for non-anonymous nodes if needed
        if self.graph is None and not self.anon:
            self.graph = Graph()

        # Only register non-anonymous nodes with the graph
        if self.graph is not None and not self.anon:
            self.graph.add(self)
        return self

    # @model_validator(mode="after")
    # def _set_anon_label(self):
    #     if self.anon:
    #         # label should be set by now
    #         self.label = f"anon-{self.label}"
    #     return self

    parent_id: UUID = None

    @model_validator(mode="after")
    def _add_self_to_parent(self):
        """If parent is passed in as an argument."""
        logger.debug(f"Checking {self.label} is parented by {self.parent_id} in graph {self.graph}")
        if self.graph is not None and self.parent_id is not None and self.parent_id in self.graph:
            logger.debug(f"Adding {self.label} to parent")
            self.parent.add_child(self)
        return self

    @property
    def parent(self) -> Optional[Node]:
        """Link to this node's parent or None if the parent is None or not in the graph yet."""
        # This guardrail `get` is primarily to catch attempting to recurse ancestors to get
        # path before a graph is completely reassembled during deserialization
        return self.graph.get(self.parent_id)

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
        while root.parent_id:
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

    def add_child(self, child: Node, as_parent: bool = True):
        """
        Cases:
        1. Error cases (fast fail):
           - child has a different non-empty graph than parent
           - adding child would create a cycle

        2. Graph assignment:
           - if child has no graph, assign parent's graph
           - if child has same graph as parent, ensure it's registered

        3. Parent-child relationship:
           - if as_parent=True, set child.parent_id = self.uid
           - add child.uid to self.children_ids if not already there
        """
        # Error case: different non-trivial graphs
        has_trivial_graph = child.graph and child.graph is not self.graph and len(child.graph) <= 1
        logger.debug(f"Child trivial graph: {has_trivial_graph}")

        if child.graph and child.graph is not self.graph and not has_trivial_graph:
            raise ValueError("Cannot add a node from a different non-trivial graph.")

        # Graph assignment - respect anonymity
        if child.graph is None or has_trivial_graph:
            # Set graph reference, but only register if not anonymous
            child.graph = self.graph
            if not child.anon:
                self.graph.add(child)
        elif not child.anon and child not in self.graph:
            # Ensure non-anonymous child is registered
            self.graph.add(child)

        # Skip if already a child
        if child.uid in self.children_ids:
            logger.warning("Tried to re-add a child node")
            return

        # Set parent reference if requested
        orig_child_parent_id = child.parent_id
        if as_parent:
            child.parent_id = self.uid

        # Check for cycles before finalizing
        if child.detect_cycle():
            # Undo parent assignment if we made it
            if as_parent:
                child.parent_id = orig_child_parent_id
            raise ValueError("Adding this node would create a cycle")

        # Add to children list
        self.children_ids.append(child.uid)

    # def add_child(self, child: Self, as_parent: bool = True):
    #     """
    #     cases:
    #     1. skip:
    #        - child has graph, it's the same as parent and child is already in it
    #     2. add to parent graph if:
    #        - child has no graph
    #        - child has same graph as parent but NOT in parent.graph already
    #     2. raise if:
    #        - child has a graph that is not the same as the parent graph and not empty
    #     """
    #
    #     if not child.graph or child not in self.graph:
    #
    #         if child.graph is self.graph and child not in self.graph:
    #             self.graph.add(child)
    #         elif child.graph is not self.graph and len(child.graph) > 1:
    #             raise ValueError("Cannot add a node from a different working graph.")
    #     else:
    #         self.graph.add(child)  # this will replace an empty child graph
    #     if child.uid not in self.children_ids:
    #         if as_parent:
    #             # Allow adding links as peers
    #             child.parent_id = self.uid
    #         # check for cycles
    #         if child.detect_cycle():
    #             raise ValueError("Adding this node would create a cycle")
    #         self.children_ids.append(child.uid)
    #         return
    #     logger.warning("Tried to re-add a child node")

    def remove_child(self, child: Self, unlink: bool = False):
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
            from .edge import Edge
            if isinstance(child, Edge):
                child = child.successor
            return child
        return super().__getattr__(name)

    def __contains__(self, item):
        """
        Support `<child_id> in Node()`.

        This can be extended by other classes that want to add their own attributes to `__contains__`.
        """
        # If it's a node, uid, or string-like uid check the children array
        if isinstance(item, Node):
            if item in self.children:
                return True
            return False
        if isinstance(item, str) and is_valid_uuid(item):
            item = UUID(item)
        if isinstance(item, UUID):
            if item in self.children_ids:
                return True
            return False
        # If it's a regular string, check if it's a label or pass it on
        if isinstance(item, str) and item in [ch.label for ch in self.children]:
            return True
            # Pass string to super() and see if it matches
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

    def traverse_dfs(self) -> Iterator[Self]:
        """Depth-first traversal of node tree"""
        yield self
        for child in self.children:
            yield from child.traverse_dfs()

    def traverse_bfs(self) -> Iterator[Self]:
        """Breadth-first traversal of node tree"""
        queue = deque([self])
        while queue:
            node = queue.popleft()
            yield node
            queue.extend(node.children)

    def visit(self, visitor: Callable[[Self], None]) -> None:
        """Apply visitor function to this node and all children"""
        visitor(self)
        for child in self.children:
            child.visit(visitor)

    def move_to(self, new_parent: Self, index: int = None) -> None:
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
    def siblings(self) -> list[Self]:
        """Get all siblings of this node"""
        if not self.parent:
            return []
        return [child for child in self.parent.children if child != self]

    @property
    def leaf_nodes(self) -> list[Self]:
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
