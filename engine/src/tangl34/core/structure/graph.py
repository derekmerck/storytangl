from typing import Union, List, Literal, Iterator

from ..entity import Registry
from .node import Node
from .edge import Edge

class Graph(Registry[Union[Node, Edge]]):

    def find_edges(self,
                   node: Node,
                   direction: Literal["in", "out"] = None,
                   **criteria
                   ) -> Iterator[Edge]:

        if direction == "in":
            criteria['dst_id'] == node.uid
        elif direction == "out":
            criteria['src_id'] == node.uid

        return (v for v in self if v.match(obj_cls=Edge, **criteria))
