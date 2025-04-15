from __future__ import annotations
from typing import Generic, TypeVar
from uuid import UUID
import functools
import logging

from tangl.utils.is_valid_uuid import is_valid_uuid
from tangl.type_hints import UniqueLabel
from tangl.core import Entity, Registry
# from .node import Node

logger = logging.getLogger(__name__)

NodeT = TypeVar('NodeT', bound='Node')

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
        if getattr(node, 'anon', False):
            # Skip registration for anonymous nodes
            logger.debug(f'Declining to register anonymous node {node!r}')
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