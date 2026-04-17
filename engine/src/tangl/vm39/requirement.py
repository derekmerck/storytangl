from __future__ import annotations
from uuid import UUID
from typing import Optional

from tangl.core39 import Selector, Node, Graph, Edge

##############################
# REQUIREMENTS
##############################

class Requirement(Selector):

    provider_id: UUID = None

    def set_provider(self, node: Node):
        self.provider_id = node.uid

    def get_provider(self, graph: Graph) -> Optional[Node]:
        return graph.get(self.provider_id)

    def satisfied_by(self, node: Node) -> bool:
        return self.match(node)

    @property
    def satisfied(self) -> bool:
        return self.provider_id is not None

class Dependency(Requirement, Edge):
    # pull node

    @property
    def successor(self) -> Optional[Node]:
        return self.get_provider(self.graph)

    @successor.setter
    def successor(self, value: Node):
        self.set_provider(value)

    def attach(self, node: Node):
        # edge belongs to the pred, can just attach succ
        self.successor = node

    hard: bool = False  # blocks if unresolved

class Affordance(Requirement, Edge):
    # push node

    @property
    def predecessor(self) -> Optional[Node]:
        return self.get_provider(self.graph)

    @predecessor.setter
    def predecessor(self, value: Node):
        self.set_provider(value)

    def attach(self, node: Node):
        # create a new edge, ref edge belongs to succ, create a new edge and attach to pred
        affordance = self.clone()
        self.graph.add(affordance)
        affordance.predecessor = node
