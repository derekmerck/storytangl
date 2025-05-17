from typing import Union

from ..entity import Registry
from .node import Node
from .edge import Edge

class Graph(Registry[Union[Node, Edge]]):
    ...
