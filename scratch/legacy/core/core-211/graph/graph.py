from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Type, Callable, Iterable, Optional
from uuid import UUID
from typing import TypeVar
import functools
from logging import getLogger

from pydantic import Field

from tangl.type_hints import UniqueLabel, Tags
from tangl.entity import Entity
from tangl.utils.is_valid_uuid import is_valid_uuid

if TYPE_CHECKING:
    from .node import Node, NodeType
    from .factory import GraphFactory

logger = getLogger("tangl.graph")
logger.setLevel(logging.WARNING)

# Side note, the 'Graph' class was originally called 'Context' and was derived from
# the context manager directly.  This functionality was factored out into the service
# layer after 2.3.

class Graph(Entity):
    """
    Acts as the central repository for all nodes within a story, mapping unique identifiers to node instances.

    Attributes:
      - `nodes`: A dictionary that maps UUIDs to Nodes, forming the backbone of the narrative structure.

    Methods:
      - `add_node`: Incorporates nodes into the graph, underpinning the dynamic expansion of the narrative.
      - `_nodes_by_path`: A cached property that facilitates lookup by nested labels, enhancing the ability to trace narrative threads and relationships.
      - `get_node`, `find_nodes`, `find_node`: Provide robust search and retrieval functionalities, crucial for navigating and manipulating the narrative structure.
    """

    nodes: dict[UUID, Node] = Field(default_factory=dict)
    factory: GraphFactory = None

    def add_node(self, node: NodeType):
        if node.uid not in self.nodes:
            if hasattr(node, "graph"):
                setattr(node, "graph", self)
            self.nodes[node.uid] = node
            # invalidate cache
            if hasattr(self, "_nodes_by_path"):
                delattr(self, "_nodes_by_path")

    def remove_node(self, node: NodeType):
        """
        This is not guaranteed to find all references nor to preserve references
        to children with multiple associations.

        It is provided purely for completeness and testing purposes.
        """
        # recursively unlink children
        for child in node.children:
            self.remove_child(child)
        # unlink from parent node
        if node.parent is not None:
            node.parent.remove_child(node)
        # unlink self
        del self.nodes[node.uid]

    @functools.cached_property
    def _nodes_by_path(self) -> dict[UniqueLabel, NodeType]:
        return {n.path if hasattr(n, "path") else n.label: n for n in self.nodes.values()}

    def get_node(self, key: UUID | UniqueLabel) -> NodeType:
        if isinstance(key, str) and is_valid_uuid(key):
            key = UUID(key)
        if isinstance(key, UUID):
            return self.nodes[key]
        elif isinstance(key, str):
            if key not in self._nodes_by_path:
                logger.debug(f"Unregistered key: '{key}' in {list(self._nodes_by_path.keys())}")
                raise KeyError(key)
            logger.debug(f"Found key: '{key}' in {list(self._nodes_by_path.keys())}")
            return self._nodes_by_path[key]
        raise TypeError(f"Unknown key type {type(key)} for {key}")

    # Alternate implementation for get/get_node
    # def __missing__(self, key: str | UUID ) -> Node:
    #     if key in self.nodes_by_path():
    #         return self.nodes_by_path()[key]
    #     raise KeyError(f'Key {key} not found in node registry')

    def __contains__(self, item):
        if isinstance(item, str) and is_valid_uuid(item):
            item = UUID(item)
        if isinstance(item, Entity):
            return item in self.nodes.values()
        elif isinstance(item, UUID):
            return item in self.nodes
        elif isinstance(item, str):
            return item in self._nodes_by_path
        raise TypeError(f"Unknown key type {type(item)} for {item}")

    @classmethod
    def _find_nodes(cls,
                    nodes: Iterable[NodeType],
                    node_cls: Type[NodeType] = None,
                    filt: Callable = None,
                    has_tags: Tags = None) -> list[NodeType]:

        def filt_(x) -> bool:
            if node_cls and not isinstance(x, node_cls):
                return False
            if filt and not filt(x):
                return False
            if has_tags and not x.has_tags(*has_tags):
                return False
            return True

        res = filter(filt_, nodes)
        res = list(res)
        return res

    def find_nodes(self,
                   node_cls: Type[NodeType] = None,
                   filt: Callable = None,
                   has_tags: Tags = None) -> list[NodeType]:
        """
        Filter nodes based on various conditions:

        :param node_cls: Tuple of Node subtypes to find, e.g. Renderables | Edges
        :param filt: Callable test for a specific criteria, e.g. lambda x: x.has_tag('important')
        :param has_tags: Iterable to tags thaat should pe present in the  node namespace
        :param conditions: List of condition strings that should be satisfied by the node namespace
        :return: List of Nodes matching the given conditions or all Nodes if no conditions are given
        """
        return self._find_nodes(self.nodes.values(), node_cls=node_cls, filt=filt, has_tags=has_tags)

    def find_node(self,
                  node_cls: Type[NodeType] = None,
                  filt: Callable = None,
                  has_tags: Tags = None) -> NodeType:
        res = self._find_nodes(self.nodes.values(), node_cls=node_cls, filt=filt, has_tags=has_tags)
        if res:
            return res[0]

    factory: Entity = None   # type: GraphFactory


GraphType = TypeVar("GraphType", bound=Graph)
