from __future__ import annotations
from typing import Mapping
from pydantic import Field

from tangl.core import Entity, Node
from .task_handler import TaskPipeline, PipelineStrategy, HandlerPriority

def setup_on_context_pipeline() -> TaskPipeline[HasContext, Mapping]:
    if pipeline := TaskPipeline.get_instance(label="on_gather_context"):
        pass
    else:
        pipeline = TaskPipeline(label="on_gather_context", pipeline_strategy=PipelineStrategy.GATHER)

    return pipeline

on_gather_context = setup_on_context_pipeline()


class HasContext(Entity):

    locals: dict = Field(default_factory=dict)

    @on_gather_context.register(priority=HandlerPriority.LATE)
    def _provide_locals(self):
        return self.locals

    @on_gather_context.register(priority=HandlerPriority.EARLY, caller_cls=Node)
    def _provide_parent_context(self: Node):
        if self.parent is not None and isinstance(self.parent, HasContext):
            return self.parent.gather_context()
        elif self.parent is None and isinstance(self.graph, HasContext):
            return self.graph.gather_context()

    def gather_context(self):
        return on_gather_context.execute(self)
