from __future__ import annotations
from typing import Optional
from uuid import UUID

from pydantic import Field, PrivateAttr

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Edge, Graph, Node
from .abs_feature_graph import ChoiceEdge, StructureNode, When
from .provisioner import Resolvable
from .journal import HasJournal as Journal
from .solver_services import SolverServices


class ForwardResolver(Entity):
    """
    Explore a space in a 'feed-forward' manner, incrementally expanding the solution frontier, pruning unreachable states, and logging output to the journal.

    This is in-contrast to 'feed-backward' processes like inferring an untangled lane from an existing graph.
    """
    graph: Graph
    journal: Journal = None

    cursor_id: UUID
    step_counter: int = 0
    # todo: How do we register this solver's context to be included with the node's context?

    cursor_return_stack: list[UUID] = Field(default_factory=list)

    _s: SolverServices = PrivateAttr(default_factory=SolverServices)

    @property
    def cursor(self) -> StructureNode:
        return self._s.graph.get(self.graph, self.cursor_id)

    @cursor.setter
    def cursor(self, cursor: StructureNode) -> None:
        self.cursor_id = cursor.uid

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
    
    def _check_for_active_choice(self, node: StructureNode, *, ctx: StringMap,
                                 when: When = None) -> Optional[Edge]:

        for choice in self._s.graph.find_edges(node, direction="out", choice_type=when, has_cls=ChoiceEdge):
            if self._s.prov.is_resolved(choice) and \
               self._s.pred.is_satisfied(choice, ctx=ctx):
                # Automatically advance frontier
                return choice

    def advance_cursor(self, edge: ChoiceEdge, *, bookmark: str = None) -> Optional[ChoiceEdge]:
        # Take a single step

        # Validate step
        if not isinstance(edge, ChoiceEdge):
            raise TypeError(f"Cannot advance, {edge!r} is not a control edge")
        if edge.src is not self.cursor:
            raise RuntimeError(f"Cannot advance, {edge!r} is not on cursor")
        node = edge.dest

        ctx = self._s.ctx.gather_context(node)

        if not self._s.pred.is_satisfied(node, ctx=ctx):
            raise RuntimeError(f"Cannot advance, {node!r} is unavailable")

        # Commit cursor update
        self.cursor = node
        self.step_counter += 1

        # Resolve frontier edges
        self._s.prov.provision_dependencies(node, ctx=ctx)  # anything this node _needs_
        self._s.prov.discover_affordances(node, ctx=ctx)    # anything the graph can provide for it
        # todo: Check for critical affordances in the current scopes, things this node needs to provide

        # Check for 'before' auto-advance
        if (next_edge := self._check_for_active_choice(node, ctx=ctx, when="before")) is not None:
            return next_edge

        # Update context with 'before' effects
        self._s.effect.apply_effects(node, ctx=ctx, when="before")

        # Generate trace content
        fragments = self._s.render.render_content(node, ctx=ctx)
        self._s.journal.add_entry(self.journal, fragments, bookmark=bookmark)

        # Update context with 'after' effects
        self._s.effect.apply_effects(node, ctx=ctx, when="after")

        # Check for 'after' auto-advance
        if (next_edge := self._check_for_active_choice(node, ctx=ctx, when="after")) is not None:
            return next_edge

        # todo: confirm there is a live choice to block on
