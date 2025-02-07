from __future__ import annotations
from typing import Optional, Self, Any

from tangl.core.graph import Node, Edge
from tangl.core.entity.handlers import HasContext, Renderable, on_render, HasEffects, on_apply_effects
from tangl.core.task_handler import TaskHandler, TaskPipeline, HandlerPriority, PipelineStrategy

on_enter = TaskPipeline[Node, Optional[Edge]](label="on_enter", pipeline_strategy=PipelineStrategy.FIRST)

on_exit = TaskPipeline[Edge, Any](label="on_exit", pipeline_strategy=PipelineStrategy.GATHER)


class Traversable(HasContext, Node):
    """
    Traversable Nodes are connected to other traversable nodes by edges.

    Upon entering a traversable node, we call several other pipelines.

    - check for redirects
    - check for available
    - apply effects
    - generate content
    - check for continues

    If a redirect or continue is found, it is returned and the logic should immediately attempt to exit via that edge and enter the successor node.
    If we attempt to enter an unavailable node, an access error is raised.
    Generated content must be stashed somewhere, like in a journal rather than passed through the enter pipeline.
    If the logic stalls, the cursor is updated to the current node, and we await user input selecting the next exit edge.
    """

    continues: list[Edge] = None
    redirects: list[Edge] = None
    visited = False

    @on_enter.register(priority=HandlerPriority.FIRST)
    def _check_for_redirects(self, **context) -> Optional[Edge]:
        for edge in self.redirects or []:
            if edge.available(**context):
                return edge

    @on_enter.register(priority=HandlerPriority.EARLY, caller_cls=HasEffects)
    def _apply_effects(self: HasEffects, **context):
        on_apply_effects.execute(self, **context)

    @on_enter.register(priority=HandlerPriority.NORMAL, caller_cls=Renderable)
    def _create_content(self: Renderable, **context):
        content = on_render.execute(self, **context)
        # todo: stash it in the journal or somewhere...

    @on_enter.register(priority=HandlerPriority.LAST)
    def _check_for_continues(self, **context) -> Optional[Edge]:
        for edge in self.continues or []:
            if edge.available(**context):
                return edge

    def enter(self, **context) -> Optional[Self]:
        context = context or self.gather_context()
        return on_enter.execute(self, **context)

    @on_exit.register(priority=HandlerPriority.LAST, caller_cls=Renderable)
    def _return_successor(self, edge: Edge, **context):
        return edge.successor

    def exit(self, *, edge: Edge, **context) -> Self:
        context = context or self.gather_context()
        return on_exit.execute(self, edge=edge, **context)

# todo: need a graph manager or plugin that orchestrates traversal updates
