from typing import TYPE_CHECKING

from ..entity import Singleton

if TYPE_CHECKING:
    from .graph import Graph

class Domain(Singleton):
    # broadest scope, graphs are provided by a domain

    def create_graph(self) -> Graph: ...
