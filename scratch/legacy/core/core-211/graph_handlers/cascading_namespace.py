from ..node import NodeType
from tangl.entity.mixins import NamespaceHandler, HasNamespace, AvailabilityHandler

class HasCascadingNamespace(HasNamespace):
    """
    A specialized NamespaceHandler for nodes builds a cascaded namespace from
    the node's ancestor chain and graph, if available.
    """

    @NamespaceHandler.strategy
    def _include_parent_and_graph_ns(self: NodeType):
        if self.parent and hasattr(self.parent, "get_namespace"):
            return self.parent.get_namespace()
        elif hasattr(self.graph, "get_namespace"):
            # Only once, when root is reached
            return self.graph.get_namespace()

    @AvailabilityHandler.strategy
    def _include_parent_available(self: NodeType):
        if self.parent and hasattr(self.parent, "available"):
            return self.parent.available()
