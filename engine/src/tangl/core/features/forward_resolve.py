from __future__ import annotations
from typing import Optional, Literal

Scope = dict

from tangl.type_hints import StringMap
from tangl.core.entity import Node, Edge, Graph
from tangl.core.handler import BaseHandler, HandlerRegistry, availability_handler, context_handler, effect_handler
from .journal import HasJournal as Journal, render_handler
from .feature_nodes import ChoiceEdge, When
from .provisioner import provision_handler

# todo: need a "scoped context handler" that does chaining

class ForwardResolver:

    graph: Graph
    cursor: Node
    journal: Journal
    scopes: list[Scope]

    def _check_choices(self, when: When, *, ctx: StringMap) -> Optional[Edge]:
        for choice in self.cursor.edges(direction="out", has_cls=ChoiceEdge):
            if choice.is_resolved() and choice.control_trigger == when and not choice.is_gated(ctx=ctx):
                # Automatically advance frontier
                return choice

    def resolve_choice(self, edge: ChoiceEdge, *, bookmark: str = None):
        # Entry point to iterate over steps

        while edge is not None:
            edge = self.advance_cursor(edge, bookmark=bookmark)
            bookmark = None

    def advance_cursor(self, edge: ChoiceEdge, *, bookmark: str = None) -> Optional[ChoiceEdge]:
        # Take a single step

        # Validate step
        if not isinstance(edge, ChoiceEdge):
            raise RuntimeError(f"Cannot advance, {edge} is not a control edge")
        if edge.src is not self.cursor:
            raise RuntimeError(f"Cannot advance, {edge} is not on cursor")
        node = edge.dest
        ctx = context_handler.execute_all(node, *self.scopes)
        if node.is_gated(*self.scopes, ctx=ctx):
            raise RuntimeError(f"Cannot advance, {node} is unavailable")

        # Update cursor
        self.cursor = node

        # Resolve frontier edges
        provision_handler.provision_node(node, ctx=ctx)
        # # Resolve requirements
        # # Adds edges with open source to the frontier
        # ProvisionHandler.link_requirements(node, ctx=ctx)

        # Check for auto-advance
        if (next_edge := self._check_choices("before", ctx=ctx)) is not None:
            return next_edge

        # Update context
        effect_handler.apply_effects(self.cursor, self.graph, *self.scopes, ctx=ctx, when="before")

        # Generate trace content
        fragments = render_handler.render_content(self.cursor, self.graph, *self.scopes, ctx=ctx)
        self.journal.add_entry(fragments, bookmark=bookmark)

        effect_handler.apply_effects( self.cursor, self.graph, *self.scopes, ctx=ctx, when="after")

        # Check for auto-advance
        if (next_edge := self._check_choices("after", ctx=ctx)) is not None:
            return next_edge
