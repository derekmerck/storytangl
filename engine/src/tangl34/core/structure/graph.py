from typing import Union, List, Literal, Iterator

from ..entity import Registry
from .node import Node
from .edge import Edge, EdgeKind

class Graph(Registry[Union[Node, Edge]]):

    def find_edges(self,
                   node: Node,
                   direction: Literal["in", "out"] = None,
                   edge_kind: EdgeKind = None,
                   **criteria
                   ) -> Iterator[Edge]:

        criteria.setdefault("obj_cls", Edge)
        if direction == "in":
            criteria.setdefault('dst_id', node.uid)
        elif direction == "out":
            criteria.setdefault('src_id', node.uid)
        if edge_kind is not None:
            criteria.setdefault('edge_kind', edge_kind)

        return (v for v in self if v.match(**criteria))
