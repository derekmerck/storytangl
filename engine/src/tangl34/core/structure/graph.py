from typing import Union, List, Literal, Iterator
import logging

from ..entity import Registry
from .node import Node
from .edge import Edge, EdgeKind

logger = logging.getLogger(__name__)

class Graph(Registry[Union[Node, Edge]]):

    def add_edge(self, src: Node, dst: Edge, edge_kind: EdgeKind = None) -> Edge:
        e = Edge(src_id=src.uid, dst_id=dst.uid, edge_kind=edge_kind)
        self.add(e)
        return e

    def find_edges(self,
                   node: Node,
                   direction: Literal["in", "out"] = None,
                   edge_kind: EdgeKind = None,
                   **criteria
                   ) -> Iterator[Edge]:

        criteria.setdefault("has_cls", Edge)
        if direction == "in":
            criteria.setdefault('dst_id', node.uid)
        elif direction == "out":
            criteria.setdefault('src_id', node.uid)
        if edge_kind is not None:
            criteria.setdefault('edge_kind', edge_kind)

        logger.debug(criteria)
        logger.debug(list(self))

        return (v for v in self if v.match(**criteria))
