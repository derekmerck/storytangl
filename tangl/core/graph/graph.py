from __future__ import annotations
from typing import Any, Optional, Generic, Iterator, Callable, TypeVar
from uuid import UUID
import functools
from collections import deque
import logging

from pydantic import Field, BaseModel

from tangl.type_hints import UniqueLabel
from tangl.core.entity import Entity, Registry

PATH_SEPARATOR = "/"
logger = logging.getLogger(__name__)

NodeT = TypeVar('NodeT', bound='Node')

class Node(Entity):
    """
    Nodes are Entities that keep links to their graph (Registry), and to their
    parent and children Nodes.

    Node-links are kept as _uuid references_ to avoid recursion issues and simplify
    serialization.

    Nodes may be used as sub-graph containers for other nodes.
    """
    graph: Graph = Field(None, json_schema_extra={'cmp': False})
    parent_id: UUID = None

    @property
    def parent(self) -> Optional[Node]:
        if self.parent_id:
            return self.graph[self.parent_id]
        return None

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
    def children(self):
        return [ self.graph[v] for v in self.children_ids ]

    def add_child(self, child: NodeT):
        if child.graph and child.graph is not self.graph:
            raise ValueError("Cannot add a node from a different graph.")
        if child.uid not in self.children_ids:
            self.graph.add(child)
            child.parent_id = self.uid
            # check for cycles
            if child.detect_cycle():
                raise ValueError("Adding this node would create a cycle")
            self.children_ids.append(child.uid)
            return
        logger.warning("Tried to re-add a child node")

    def remove_child(self, child: NodeT, unlink: bool = False):
        if child.uid in self.children_ids:
            child.parent_id = None
            self.children_ids.remove(child.uid)
            if unlink:
                # Use this cautiously -- there is no link counting, so if the child is
                # referenced by multiple nodes, they will error when trying to access it.
                # This also unlinks held references (i.e. grandchildren) recursively.
                child.graph.remove(child)
        else:
            logger.warning("Tried to remove a non-child node")

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

class Graph(Registry[NodeT], Generic[NodeT]):

    def add(self, node: NodeT, **kwargs):
        if node.graph is self:
            return
        node.graph = self
        super().add(node, **kwargs)
        # this will throw if trying to re-add but node.graph is not already set to self

    def remove(self, value: NodeT):
        for child in value.children:
            value.remove_child(child, unlink=True)
        super().remove(value)

    def __getitem__(self, key: UUID | UniqueLabel):
        if isinstance(key, UniqueLabel):
            if x := self.find_one(path=key):
                return x
        return super().__getitem__(key)
