"""
has_context.py

Defines and exposes a singleton pipeline (:func:`on_gather_context`)
used to collect local or inherited context data for entities.
This is typically a dictionary of variables or configuration
objects that other handler pipelines may depend on.
"""

from __future__ import annotations
from typing import Mapping, Optional
from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.graph import Node
from tangl.core.task_handler import TaskPipeline, HandlerPriority, PipelineStrategy

def setup_on_context_pipeline() -> TaskPipeline[HasContext, StringMap]:
    """
    Retrieve (or create) a singleton TaskPipeline for the 'on_gather_context'
    label. By default, it uses the ``GATHER`` strategy, meaning all non-None
    dict results from handlers will be merged (if they share the same type).

    :return: The singleton pipeline for context gathering.
    :rtype: TaskPipeline[HasContext, Mapping[str, Any]]
    """
    # Attempt to look up an existing pipeline by label
    pipeline = TaskPipeline.get_instance(label="on_gather_context")
    if pipeline is None:
        # Create a new pipeline with the desired label + strategy
        pipeline = TaskPipeline(
            label="on_gather_context",
            pipeline_strategy=PipelineStrategy.GATHER
        )
    return pipeline

# Expose this pipeline for decorating methods that supply context
on_gather_context = setup_on_context_pipeline()
"""
The global pipeline for supplying context. Handlers for context gathering
should decorate methods with ``@on_gather_conext.register(...)``.
"""

class HasContext(Entity):
    """
    An entity that supports generating or inheriting a contextual
    dictionary. This class registers two handlers with the global
    :func:`on_gather_context` pipeline:

      1. :meth:`_provide_parent_context` (EARLY priority): If this entity
         is a :class:`~tangl.core.Node`, it attempts to gather context from
         the parent or (if no parent) from the containing graph.  Because it
         triggers early, keys may be overwritten by local scope on this entity.
      2. :meth:`_provide_locals` (LATE priority): Always returns this
         entity's local dictionary.  Because it triggers late, keys from
         this entity's locals will usually overwrite other scoped sources.

    Calling :meth:`gather_context` executes the pipeline, merging all
    returned dicts if they share the same type. The final result is
    typically a single combined context dictionary.

    :ivar locals: A dictionary of local context variables.
    :type locals: StringMap
    """
    locals: StringMap = Field(default_factory=dict)

    @on_gather_context.register(priority=HandlerPriority.LATE)
    def _provide_locals(self) -> StringMap:
        """
        Provide this entity's local dictionary of context variables.

        :return: The local context dictionary.
        :rtype: dict[str, Any]
        """
        return self.locals

    @on_gather_context.register(priority=HandlerPriority.EARLY, caller_cls=Node)
    def _provide_parent_context(self: Node) -> Optional[StringMap]:
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

    def gather_context(self) -> StringMap:
        """
        Execute the :func:`on_gather_context` pipeline for this entity,
        collecting or merging all applicable context dictionaries.

        :return: A merged dictionary of all non-None context data returned
                 by the handlers, or None if no handlers returned anything.
        :rtype: dict[str, Any] | None
        """
        return on_gather_context.execute(self)
