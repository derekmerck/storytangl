from __future__ import annotations
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Node, Edge, Graph
from tangl.core.handler import BaseHandler, HandlerRegistry, on_check_satisfied, on_gather_context, on_apply_effects, HasEffects
from .journal import HasJournal as Journal, on_render_content
from .feature_nodes import ChoiceEdge, When
from .provisioner import dependency_provisioner

Scope = dict
# todo: need a "scoped context handler" that does chaining

class ForwardResolver(Entity):
    """
    Explore a space in a 'feed-forward' manner, incrementally expanding the solution frontier, pruning unreachable states, and logging output to the journal.

    This is in-contrast to 'feed-backward' processes like inferring an untangled lane from an existing graph.
    """
    model_config = ConfigDict(revalidate_instances="never")
    graph: Graph
    cursor_id: UUID
    journal: Journal
    scopes: list[Scope]

    @property
    def cursor(self) -> Node:
        return self.graph.get(self.cursor_id)

    @cursor.setter
    def cursor(self, cursor: Node) -> None:
        self.cursor_id = cursor.uid

    def _check_choices(self, when: When, *, ctx: StringMap) -> Optional[Edge]:
        for choice in self.cursor.edges(direction="out", choice_type=when, has_cls=ChoiceEdge):
            if choice.is_resolved() and choice.control_trigger == when and choice.is_satisfied(ctx=ctx):
                # Automatically advance frontier
                return choice

    def resolve_choice(self, edge: ChoiceEdge, *, bookmark: str = None):
        # Entry point to iterate over steps
        # Advancing the cursor may return a pre-req or post-req edge
        # todo: jump and _return_ edges

        while edge is not None:
            edge = self.advance_cursor(edge, bookmark=bookmark)
            bookmark = None

    def advance_cursor(self, edge: ChoiceEdge, *, bookmark: str = None) -> Optional[ChoiceEdge]:
        # Take a single step

        # Validate step
        if not isinstance(edge, ChoiceEdge):
            raise TypeError(f"Cannot advance, {edge!r} is not a control edge")
        if edge.src is not self.cursor:
            raise RuntimeError(f"Cannot advance, {edge!r} is not on cursor")
        node = edge.dest
        ctx = on_gather_context.execute_all(node, *self.scopes, ctx=None)
        if not node.is_satisfied(*self.scopes, ctx=ctx):
            raise RuntimeError(f"Cannot advance, {node!r} is unavailable")

        # Update cursor
        self.cursor = node

        # Resolve frontier edges
        # dependency_provisioner.provision_node(node, ctx=ctx)
        # # Resolve requirements
        # # Adds edges with open source to the frontier
        # ProvisionHandler.link_requirements(node, ctx=ctx)

        # Check for 'before' auto-advance
        if (next_edge := self._check_choices("before", ctx=ctx)) is not None:
            return next_edge

        # Update context with 'before' effects
        on_apply_effects.apply_effects(self.cursor, self.graph, *self.scopes, ctx=ctx, when="before")

        # Generate trace content
        fragments = on_render_content.render_content(self.cursor, self.graph, *self.scopes, ctx=ctx)
        self.journal.add_entry(fragments, bookmark=bookmark)

        # Update context with 'after' effects
        on_apply_effects.apply_effects( self.cursor, self.graph, *self.scopes, ctx=ctx, when="after")

        # Check for 'after' auto-advance
        if (next_edge := self._check_choices("after", ctx=ctx)) is not None:
            return next_edge
