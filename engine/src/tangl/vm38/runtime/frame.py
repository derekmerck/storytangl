# everything for resolving a single traversal step on a graph
# frames are ephemeral, their output is strictly reproducible tho

from dataclasses import dataclass, field
from functools import cached_property
from typing import Optional, TypeAlias

from tangl.core38 import Graph, OrderedRegistry
from tangl.vm38.dispatch import do_validate, do_provision, do_prereqs, do_update, do_journal, do_finalize, do_postreqs
from tangl.vm38.traversal import TraversableNode, TraversableEdge, AnonymousEdge
from .resolution_phase import ResolutionPhase

TraversableEdge: TypeAlias = TraversableEdge | AnonymousEdge

@dataclass
class Frame:

    graph: Graph
    cursor: TraversableNode
    output_stream: OrderedRegistry
    return_stack: list[TraversableEdge] = field(default_factory=list)

    cursor_steps: int = 0

    @cached_property
    def frame_ctx(self):
        # create your frame context as desired
        # - include get_entity_groups() and get_template_groups() for resolver
        ...

    def goto_node(self, node: TraversableNode, force=False):
        do_provision(node, ctx=self.frame_ctx, force=force)  # force resolution if necessary
        # jump and skip validation
        edge = AnonymousEdge(successor=node, entry_phase=ResolutionPhase.PLANNING)
        self.resolve_choice(edge)

    def follow_edge(self, edge: TraversableEdge) -> Optional[TraversableEdge]:

        entry_phase = edge.entry_phase or ResolutionPhase.VALIDATE

        if entry_phase <= ResolutionPhase.VALIDATE:
            if not do_validate(edge, ctx=self.frame_ctx):
                raise ValueError('Invalid edge')

        # update the cursor
        self.cursor = edge.successor
        self.cursor_steps += 1

        if entry_phase <= ResolutionPhase.PLANNING:
            # we _know_ that cursor is already planned, it has successors
            frontier = self.cursor.successors(has_kind=TraversableNode)
            for node in frontier:
                # try to provision it
                do_provision(node, ctx=self.frame_ctx)  # plan nodes reachable from the cursor

        if entry_phase <= ResolutionPhase.PREREQS:
            if prereq := do_prereqs(self.cursor, ctx=self.frame_ctx):
                # type will be edge with return phase PREREQ
                return prereq

        if entry_phase <= ResolutionPhase.UPDATE:
            do_update(self.cursor, ctx=self.frame_ctx)

        if entry_phase <= ResolutionPhase.JOURNAL:
            fragments = do_journal(self.cursor, ctx=self.frame_ctx)
            if fragments:
                self.output_stream.extend(fragments)

        if entry_phase <= ResolutionPhase.FINALIZE:
            patch = do_finalize(self.cursor, ctx=self.frame_ctx)
            if patch:
                self.output_stream.append(patch)

        if entry_phase <= ResolutionPhase.POSTREQS:
            if postreq := do_postreqs(self.cursor, ctx=self.frame_ctx):
                # type will be edge with return phase POSTREQ
                return postreq

    def resolve_choice(self, edge: TraversableEdge):

        while edge is not None:
            edge = self.follow_edge(edge)
            if edge and edge.return_phase is not None:
                self.return_stack.append(edge)

        if self.return_stack:
            # resolve last return recursively
            # todo: add a recursion guard for unbounded recursion errors, like
            #       follow keeps returning the same edge.
            edge = self.return_stack.pop()
            return_edge = edge.get_return_edge()
            self.resolve_choice(return_edge)
