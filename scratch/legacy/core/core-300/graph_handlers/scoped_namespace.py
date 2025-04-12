from typing import Mapping, Any

from tangl.type_hints import StringMap
from tangl.core.entity.handlers import NamespaceHandler, HasNamespace, AvailabilityHandler, Lockable

class HasScopedNamespace(HasNamespace):
    """
    A specialized NamespaceHandler for nodes builds a cascaded namespace from
    the node's ancestor chain and graph, if available.
    """

    @NamespaceHandler.strategy()
    def _include_parent_and_graph_ns(self: HasNamespace, **kwargs) -> StringMap:
        if self.parent and hasattr(self.parent, "get_namespace"):
            return self.parent.get_namespace()
        elif hasattr(self.graph, "get_namespace"):
            # Only once, when root is reached (no parent)
            return self.graph.get_namespace()

    @AvailabilityHandler.strategy()
    def _include_parent_available(self: Lockable, **kwargs) -> bool:
        if self.parent and hasattr(self.parent, "available"):
            return self.parent.available()
