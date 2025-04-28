from __future__ import annotations
from typing import Optional, Literal, Any
from uuid import UUID

# from ..entity import Entity
from ..graph import Graph, Node, Edge, SimpleEdge
from ..task_handler import HandlerPriority
from ..handler_pipeline import HandlerPipeline, PipelineStrategy
from ..entity_handlers import HasContext, Renderable, on_render, HasEffects, Available, HasConditions

on_enter = HandlerPipeline[Node, Optional[Edge]](label="on_enter", pipeline_strategy=PipelineStrategy.FIRST)
on_follow_edge = HandlerPipeline[Graph, Any](label="on_follow_edge", pipeline_strategy=PipelineStrategy.GATHER)

class TraversableEdge(Available, HasConditions, Edge):
    """
    * **Availability Inheritance**: Edge availability depends on the successor's availability.
    * **Activation Modes**: Supports 'first' (redirect), 'last' (continue), or None (manual) activation.  The activation mode determines when the TraversalHandler interacts with the edge.
    * **Traversal Role**:  Edges may define "on_enter" and "on_exit" tasks, but cannot redirect or continue themselves.
    """
    activation_mode: Literal["before", "after", "block"] = "block"


class TraversableNode(Node):
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

    @property
    def redirects(self) -> list[TraversableEdge]:
        return self.find_children(has_cls=TraversableEdge, trigger="before")

    @property
    def continues(self) -> list[TraversableEdge]:
        return self.find_children(has_cls=TraversableEdge, trigger="after")

    @property
    def choices(self) -> list[TraversableEdge]:
        return self.find_children(has_cls=TraversableEdge, trigger="block")

    @on_enter.register(priority=HandlerPriority.FIRST)
    def _check_for_redirects(self, **context) -> Optional[Edge]:
        # want r to check availability in the successors context, so don't pass this one
        return next(r for r in self.redirects if r.avail())

    @on_enter.register(priority=HandlerPriority.FIRST, caller_cls=Available)
    def _confirm_available(self, **context):
        if not self.avail(**context):
            raise RuntimeError(f"Node {self.label} cannot be entered bc it is not available!")

    @on_enter.register(priority=HandlerPriority.NORMAL, caller_cls=HasEffects)
    def _apply_effects(self, **context):
        self._apply_effects(**context)

    @on_render.register()
    def _include_choices(self, **context):
        # want r to check availability in the successors context, so don't pass this one
        return {'choices': [r.render(**context) for r in self.choices if r.avail()]}

    @on_enter.register(priority=HandlerPriority.LATE, caller_cls=Renderable)
    def _create_content(self, journal = None, **context):
        # Resolve journal with explicit precedence
        journal = journal or getattr(self.graph, "journal", None)
        if journal:
            rendered_content = self.render(**context)
            journal.add(rendered_content)

    @on_enter.register(priority=HandlerPriority.LAST)
    def _check_for_continues(self, **context) -> Optional[Edge]:
        # want r to check availability in the successors context, so don't pass this one
        return next(r for r in self.continues if r.avail())

    def enter(self, **context) -> Optional[TraversableEdge]:
        """
        - Check for redirects, early return result
        - Check avail
        - Apply effects
        - Create journal entry/content
        - Check for continues, return result
        - Return None
        """
        if isinstance(self, HasContext):
            context = context or self.gather_context()
        return on_enter.execute(self, **context)

    # todo: consider nodes with traversable children, that is, nodes that represent
    #       subgraphs -- how do we enter and exit them or jump between subgraphs?



class TraversableGraph(Graph):

    cursor_id: UUID = None

    @property
    def cursor(self) -> TraversableNode:
        return self.graph[self.cursor_id]

    @cursor.setter
    def cursor(self, value: TraversableNode):
        self.cursor_id = value.uid

    @on_follow_edge.register(priority=HandlerPriority.FIRST)
    def _update_cursor(self, *, edge: EdgeP[TraversableNode], **context):
        self.cursor = edge.successor

    @on_follow_edge.register(priority=HandlerPriority.LAST)
    def _enter_cursor(self, **context):
        if next_edge := self.cursor.enter(**context):
            self.follow_edge(next_edge, **context)

    def follow_edge(self, *, edge: TraversableEdge | EdgeP[TraversableNode], **context):
        if isinstance(self, HasContext):
            context = context or self.gather_context()
        on_follow_edge.execute(self, edge=edge, **context)

    # todo: deal with entering graphs and setting the initial cursor
    def enter(self, **context):
        entry_point = self.entry_point  # type: TraversableNode
        entry_edge = SimpleEdge(successor=entry_point)
        self.follow_edge(edge=entry_edge)

    def find_entry_point(self) -> Optional[TraversableEdge]:
        # Nodes and graphs with traversable children provide a context and need a default entry point
        return self.find_child(
            has_cls=TraversableNode,
            is_entry_point=True)  # type: TraversableNode

    @property
    def is_entry_point(self) -> bool:
        return "is_entry" in self.tags or \
               self.label in ["entry", "start"]

