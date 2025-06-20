from __future__ import annotations
from typing import Optional, Union
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Edge, Graph
from tangl.core.handler import HasEffects, Renderable, HasContext
from . import HasJournal
from .journal import HasJournal as Journal
from .abs_feature_graph import ChoiceEdge, StructureNode, When
from .provisioner import ResoluableNode

class ForwardResolver(Entity):
    """
    Explore a space in a 'feed-forward' manner, incrementally expanding the solution frontier, pruning unreachable states, and logging output to the journal.

    This is in-contrast to 'feed-backward' processes like inferring an untangled lane from an existing graph.
    """
    graph: Graph
    cursor_id: UUID
    journal: Journal = None
    step_counter: int = 0
    # todo: How do we register this solver's context to be included with the node's context?

    cursor_return_stack: list[UUID] = Field(default_factory=list)

    @property
    def cursor(self) -> Union[ StructureNode, HasEffects, Renderable, ResoluableNode ]:
        return self.graph.get(self.cursor_id)

    @cursor.setter
    def cursor(self, cursor: StructureNode) -> None:
        self.cursor_id = cursor.uid

    def _check_choices(self, when: When, *, ctx: StringMap) -> Optional[Edge]:
        for choice in self.cursor.edges(direction="out", choice_type=when, has_cls=ChoiceEdge):
            if (choice.is_resolved() and choice.is_satisfied(ctx=ctx)):
                # Automatically advance frontier
                return choice

    def resolve_choice(self, edge: ChoiceEdge, *, bookmark: str = None):
        # Entry point to iterate over steps
        # Advancing the cursor may return a pre-req or post-req edge
        # todo: tail trampoline for jump and _return_ edges

        while edge is not None:
            edge = self.advance_cursor(edge, bookmark=bookmark)
            bookmark = None

        # if choice.wants_return, push the current cursor onto the return stack
        # if no choices are returned _or_ available for next step, check the return stack and reset the cursor
        # not clear if you reevaluate the entire node on return?
        # I suppose it depends on if it rendered content first or not, but still probably want to restate/include any possible continuation text

    # todo: How do we inject step_count and other vars from solver into node context?
    #       Just do it manually, or register an instance handler for the graph?

    def advance_cursor(self, edge: ChoiceEdge, *, bookmark: str = None) -> Optional[ChoiceEdge]:
        # Take a single step

        # Validate step
        if not isinstance(edge, ChoiceEdge):
            raise TypeError(f"Cannot advance, {edge!r} is not a control edge")
        if edge.src is not self.cursor:
            raise RuntimeError(f"Cannot advance, {edge!r} is not on cursor")
        node = edge.dest
        ctx = self.gather_context(node=node)
        if not node.is_satisfied(ctx=ctx):
            raise RuntimeError(f"Cannot advance, {node!r} is unavailable")

        # Update cursor
        self.cursor = node
        self.step_counter += 1

        # Resolve frontier edges
        self.cursor.provision_dependencies(ctx=ctx, scopes=self.scopes)  # anything this node _needs_
        self.cursor.provision_affordances(ctx=ctx, scopes=self.scopes)   # anything this node can provide
        # todo: Check for critical affordances in the current scopes

        # Check for 'before' auto-advance
        if (next_edge := self._check_choices("before", ctx=ctx)) is not None:
            return next_edge

        # Update context with 'before' effects
        self.cursor.apply_effects(ctx=ctx, scopes=self.scopes, when="before")

        # Generate trace content
        fragments = self.cursor.render_content(ctx=ctx, scopes=self.scopes)
        if self.journal is not None:
            self.journal.add_entry(fragments, bookmark=bookmark)

        # Update context with 'after' effects
        self.cursor.apply_effects(ctx=ctx, scopes=self.scopes, when="after")

        # Check for 'after' auto-advance
        if (next_edge := self._check_choices("after", ctx=ctx)) is not None:
            return next_edge
