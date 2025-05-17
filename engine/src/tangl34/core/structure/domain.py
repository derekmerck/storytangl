from typing import TYPE_CHECKING

from ..entity import Singleton

if TYPE_CHECKING:
    from .graph import Graph

class Domain(Singleton):
    # Broadest scope, provides story templates

    def create_graph(self) -> Graph: ...
