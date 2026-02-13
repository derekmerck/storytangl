# everything for resolving a single traversal step on a graph
# frames are ephemeral, their output is strictly reproducible tho

from dataclasses import dataclass, field
from functools import cached_property
from typing import Optional, TypeAlias, Mapping, Any, Callable, Iterable
from random import Random
from uuid import UUID
from contextlib import contextmanager
from copy import copy

from tangl.core38 import Graph, OrderedRegistry, CallReceipt, Node, Behavior, BehaviorRegistry
from tangl.vm38.dispatch import dispatch as vm_dispatch, do_validate, do_provision, do_prereqs, do_update, do_journal, do_finalize, do_postreqs
from tangl.vm38.traversal import TraversableNode, TraversableEdge, AnonymousEdge
from .resolution_phase import ResolutionPhase

TraversableEdge: TypeAlias = TraversableEdge | AnonymousEdge
NS: TypeAlias = Mapping[str, Any]

@dataclass
class PhaseCtx:
    # Phase-specific ctx
    graph: Graph
    cursor_id: UUID

    @cached_property
    def cursor(self) -> TraversableNode:
        # we want to _get_ any node we need so we can potentially wrap it with an observer
        return self.graph.get(self.cursor_id)

    current_phase: ResolutionPhase
    receipts: list[CallReceipt] = field(default_factory=list)

    @contextmanager
    def with_fresh_receipts(self):
        # for sub-dispatches
        receipts = copy(self.receipts)  # do we need to copy, or can we just grab the ptr?
        self.receipts = []
        yield self
        self.receipts = receipts

    _ns_cache: dict[UUID, NS] = field(default_factory=dict)

    def get_ns(self, node: Node) -> NS:
        if node.uid not in self._ns_cache:
            # compute ns
            ...
        return self._ns_cache[node.uid]

    def get_entities(self):
        return self.graph.values()         # want to group these wrt distance from caller

    def get_templates(self):
        return self.graph.world.templates  # want to group these wrt scope-dist from caller

    # Dispatch ctx
    def get_dispatches(self) -> Iterable[BehaviorRegistry]:
        return [vm_dispatch]

    inline_behaviors: list[Callable | Behavior] = field(default_factory=list)

    def get_inline_behaviors(self) -> list[Callable | Behavior]:
        return self.inline_behaviors

    random: Random = field(default_factory=Random)

    def get_random(self) -> Random:
        return self.random

@dataclass
class Frame:

    graph: Graph
    cursor: TraversableNode
    output_stream: OrderedRegistry
    return_stack: list[TraversableEdge] = field(default_factory=list)

    cursor_steps: int = 0

    @cached_property
    def frame_random(self) -> Random:
        seed = self.graph.value_hash
        return Random(seed)

    @cached_property
    def frame_ctx(self, phase: ResolutionPhase) -> PhaseCtx:
        # create your frame context as desired
        return PhaseCtx(
            random=self.frame_random,
            graph=self.graph,
            cursor=self.cursor,
            current_phase=phase,
        )

        # - include get_entity_groups() and get_template_groups() for resolver


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
                # stash this edge so we can return later
                # the return_phase determines whether we should reenter at
                # the beginning or end of the phase base
                self.return_stack.append(edge)

        if self.return_stack:
            # resolve last return recursively
            # todo: add a recursion guard for unbounded recursion errors, like
            #       follow keeps returning the same edge.
            edge = self.return_stack.pop()
            return_edge = edge.get_return_edge()
            self.resolve_choice(return_edge)
