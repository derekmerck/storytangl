from __future__ import annotations
from typing import Optional, Any
from pydantic import Field
import re

from tangl.type_hints import StringMap
from ..task_handler import HandlerPriority
from tangl.core.graph import Node, Graph
from ..entity_handlers import HasContext, on_gather_context

class HasScopedContext(HasContext):
    """
    An entity that supports generating or inheriting a contextual
    dictionary. This class registers an extra handler with the global
    :func:`on_gather_context` pipeline:

      1. :meth:`_provide_parent_context` (EARLY priority): If this entity
         is a :class:`~tangl.core.Node`, it attempts to gather context from
         the parent or (if no parent) from the containing graph.  Because it
         triggers early, keys may be overwritten by local scope on this entity.

    Calling :meth:`gather_context` executes the pipeline, merging all
    returned dicts if they share the same type. The final result is
    typically a single combined context dictionary.
    """

    @on_gather_context.register(priority=HandlerPriority.EARLY)
    def _provide_parent_context(self, **context) -> Optional[StringMap]:
        """
        If this entity is a Node, gather context from its parent if
        that parent also implements :class:`HasContext`. If there's
        no parent, attempt to gather from the `graph` (if it's a
        :class:`HasContext`). Returns None if no context is found.

        :return: The parent's or graph's context, or None if not available.
        :rtype: dict[str, Any] | None
        """
        if self.parent is not None and isinstance(self.parent, HasContext):
            return self.parent.gather_context()
        elif self.parent is None and isinstance(self.graph, HasContext):
            return self.graph.gather_context()

    @on_gather_context.register(caller_cls=Graph)
    def _provide_items_by_path(self: Graph) -> StringMap:
        return self.nodes_by_path
