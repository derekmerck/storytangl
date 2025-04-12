from __future__ import annotations
from typing import Optional, List, Union
import logging
from enum import IntEnum
from uuid import UUID
import sys

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel
from tangl.core.handler import BaseHandler, Priority
from tangl.core.entity.handlers import *
from tangl.core.graph import Graph, Node, EdgeProtocol, SimpleEdge, Edge

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class TraversalHandler(BaseHandler):

    # @BaseHandler.task_signature
    # def on_enter(node: TraversableNode, **kwargs) -> Optional[EdgeProtocol]:
    #     """
    #     Called when the graph cursor tries to arrive at a new node.  This
    #     may happen automatically according to activation directives, or be
    #     triggered manually by selecting an edge with no activation rule.
    #
    #     If an Edge node is returned, it is assumed to be a _redirect_ or
    #     _continue_ directive, and the traversal handler will attempt to
    #     follow it.
    #
    #     Redirects activate FIRST, _before_ any node update logic.  Continues
    #     activate LAST, _after_ the node update is complete.
    #
    #     If no continue is provided, the graph cursor "settles" on the last
    #     entered node and waits for a manual selection.
    #     """
    #     # todo: this is just jump, for now, need a flag and stack for jump and return (jnr) could be implemented as a dynamically created continue edge back to the prior current_node at the end of enter.
    #     ...

    # @BaseHandler.task_signature
    # def on_exit(node, **kwargs):
    #     """
    #     Called on the predecessor for clean-up when the graph cursor follows an edge.
    #     """
    #     ...

    # @BaseHandler.task_signature
    # def on_enter_graph(graph: Graph, **kwargs):
    #     ...

    # @BaseHandler.task_signature
    # def on_exit_graph(graph: Graph, **kwargs):
    #     ...

    @classmethod
    def enter_strategy(cls, task_id: UniqueLabel = "on_enter",
                       domain: UniqueLabel = "global",
                       priority: int = Priority.NORMAL ):
        return super().strategy(task_id, domain, priority)

    @classmethod
    def exit_strategy(cls, task_id: UniqueLabel = "on_exit",
                      domain: UniqueLabel = "global",
                      priority: int = Priority.NORMAL ):
        return super().strategy(task_id, domain, priority)


    # todo: ignore edges can't work like this, it also should to change the mode from "first" to "all" or something?  Should it process everything, or just discard any edge returned?
    @classmethod
    def enter_node(cls, node: TraversableNode, ignore_redirects=False, **kwargs) -> TraversableNode:
        """
        Recursively follows edges and returns the final node.

        If jumping directly to an unrelated node, the prior node's exit status cannot be
        updated here, as there is no notion of _where_ the cursor came from.  Use a temporary
        edge object and following it.
        """
        logger.debug(f"Entering {node!r}")
        current_node = node
        try:
            next_edge = cls.execute_task(current_node, "on_enter", result_mode="first", **kwargs)
        except Exception as e:
            logger.error(f"Failed to enter node {node!r}", exc_info=e)
            raise e
        logger.debug(f"Got next edge: {next_edge!r}")
        if next_edge and not ignore_redirects:
            logger.debug(f"Redirecting via {next_edge!r}")
            current_node = cls.follow_edge(next_edge, **kwargs)
        return current_node

    @classmethod
    def exit_node(cls, node: TraversableNode, **kwargs):
        """Clean up and do post-visit bookkeeping"""
        logger.debug(f"Exiting {node!r}")
        try:
            cls.execute_task(node, "on_exit", **kwargs)
        except Exception as e:
            logger.error(f"Failed to exit node {node!r}", exc_info=e)
            raise e

    @classmethod
    def _find_common_ancestor(cls, predecessor: TraversableNode, successor: TraversableNode) -> Optional[TraversableNode]:
        """
        This approach should support popping out of and pushing into dynamic contexts,
        where traversable nodes may change parentage, for example.
        """
        if not predecessor or not successor:
            return

        logger.debug("Finding common ancestor")

        predecessor_ancestors = predecessor.ancestors()
        logger.debug(f'predecessor ancestors: {[x.label for x in predecessor_ancestors]}')
        successor_ancestors = successor.ancestors()
        logger.debug(f'successor ancestors: {[x.label for x in successor_ancestors]}')

        shared_ancestors = []
        while predecessor_ancestors:
            a = predecessor_ancestors.pop(0)  # order is [me ... root]
            if a is predecessor:
                logger.debug(f'ignoring predecessor {a!r}')
                shared_ancestors.append(a)
                continue
            if a not in successor_ancestors:
                if a.wants_exit:
                    logger.debug(f'exiting and discarding ancestor {a!r}')
                    cls.exit_node(a)
                else:
                    logger.debug(f'discarding ancestor {a!r}')
                    continue
            else:
                logger.debug(f'ignoring ancestor {a!r}')
                shared_ancestors.append(a)

        while successor_ancestors:
            a = successor_ancestors.pop()  # have to pop off the right side [ target, parent, grandparent ]
            if a is successor or a in shared_ancestors:
                # ignore our shared ancestors, which have presumably already been entered
                logger.debug(f'not entering ancestor {a!r}')
                continue
            else:
                logger.debug(f'entering ancestor {a!r}')
                """
                todo: this needs to properly follow the edge if it's going to redirect...
                      like a scene with a pre-roll block before any block renders
                      and needs a test case
                """
                cls.enter_node(a)
            # if next_edge := cls.enter_node(a):
            #     logger.debug(f'redirecting to {next_edge!r} upon entering parent {a!r}')
            #     return cls.follow_edge(next_edge)

    @classmethod
    def follow_edge(cls, edge: EdgeProtocol, **kwargs) -> TraversableNode:
        logger.debug(f"Following edge {edge!r}, ref count: {sys.getrefcount(edge)}")
        # If we redirected before processing, do not mark this node as visited
        if getattr(edge.predecessor, "wants_exit", False):
            cls.exit_node(edge.predecessor)
        # Edges can define "on_enter" and "on_exit" tasks, but they will not
        # invoke the TraversableNode pipeline unless it is explicitly mixed-in.
        # And in no case can an Edge redirect other than by indicating its
        # successor node.
        cls.enter_node(edge, ignore_redirects=True, **kwargs)
        cls.exit_node(edge, **kwargs)
        if new_node := cls._find_common_ancestor(edge.predecessor, edge.successor):
            return new_node
        return cls.enter_node(edge.successor)

    @classmethod
    def goto_node(cls, graph: TraversableGraph, new_cursor: TraversableNode, **kwargs) -> TraversableNode:
        if graph.cursor:
            # Create an implicit edge and rectify the context
            edge = SimpleEdge(predecessor=graph.cursor, successor=new_cursor)
            new_cursor = TraversalHandler.follow_edge(edge, **kwargs)
        else:
            # No context to rectify, so we can just go there
            new_cursor = TraversalHandler.enter_node(new_cursor, **kwargs)
        graph.cursor = new_cursor
        return graph.cursor

    @classmethod
    def find_entry_node(cls,
                        nodes: list[TraversableNode],
                        node_cls = None,
                        filt=None,
                        has_tags = None) -> TraversableNode:

        # todo: eval node_cls if it's a ClassName/str

        def filt_(x):
            nonlocal node_cls, filt, has_tags
            logger.debug(f"Checking {x!r} for entry")
            if not getattr(x, "is_entry", False):
                logger.debug("is not entry")
                return False
            if hasattr(x, "available") and not x.available():
                logger.debug("is not available")
                return False
            if node_cls and not isinstance(x, node_cls):
                return False
            if filt and not filt(x):
                return False
            if has_tags and not x.has_tags(*has_tags):
                return False
            return True

        candidates = list(filter(filt_, nodes))
        if candidates:
            entry_node = candidates[0]
            if redirect_entry_node := entry_node.find_entry_node():
                # Default mechanism checks for children tagged as entry
                return redirect_entry_node
            return entry_node


class TraversableGraph(BaseModel):

    cursor_id: UUID = None

    @property
    def cursor(self) -> TraversableNode:
        return self.get_node(self.cursor_id)

    @cursor.setter
    def cursor(self, value: TraversableNode | UUID):
        if value:
            if isinstance(value, UUID):
                self.cursor_id = value
            elif isinstance(value, Node):
                self.cursor_id = value.uid

    def follow_edge(self, edge: EdgeProtocol, **kwargs):
        # sets cursor
        self.cursor = TraversalHandler.follow_edge(edge, **kwargs)

    def goto_node(self, new_cursor: TraversableNode, **kwargs):
        # sets cursor
        self.cursor = TraversalHandler.goto_node(self, new_cursor, **kwargs)

    def find_entry_node(self: Graph) -> TraversableNode:
        return TraversalHandler.find_entry_node(self.nodes.values())

    # todo: Trigger on enter graph, on exit graph
    def enter(self: Graph, **kwargs):
        if self.cursor is not None:
            raise RuntimeError("Graph has already been entered!")
        entry_node = self.find_entry_node()
        if entry_node is None:
            raise RuntimeError("No entry node defined!")
        self.goto_node(entry_node, **kwargs)

    def exit(self: Graph, **kwargs):
        TraversalHandler.exit_node(self, **kwargs)


DefaultTraversableGraph = type('SimpleTraversableGraph',  (TraversableGraph, Graph), {} )

class TraversalStage(IntEnum):
    REDIRECTION = Priority.FIRST        # check for override edges
    VALIDATION  = Priority.EARLY        # confirm availability
    BOOK_KEEPING = Priority.EARLY + 10  # update ledgers (enter and exit)
    UPDATING    = Priority.NORMAL       # update the graph state
    PROCESSING  = Priority.LATE         # any user processes
    CLEAN_UP     = Priority.LAST - 10   # tear down processing
    CONTINUING  = Priority.LAST         # check for automatic next edges


class TraversableNode(BaseModel):
    """
    All nodes may have parent and child relationships, but not all nodes are
    "Traversable" within the "story-as-graph" metaphor.

    Only nodes that help direct the narrative from the beginning of a scene to
    the end of a scene are considered "Traversable". These nodes are generally
    individual narrative passages ("Blocks"), collections of related passages
    ("Scenes"), or connections between passages ("Actions").

    Action edges may be explicit -- a choice the player must actively  make, or
    implicit, as in an automatic redirection prior to or after a narrative event.

    Moving the graph cursor to a new node uses two task callbacks: "on_enter",
    and "on_exit".  Both can be broken down to priority-ordered stages.

    Exit:
    - Bookkeeping (Priority.EARLY) -- note updates and process outputs
    - Clean up (Priority.NORMAL)

    Enter:
    - Redirection (Priority.FIRST) -- check if the node wants to refer the cursor
      to somewhere else prior to handling the node (jump or jnr without exit)
    - Validation (Priority.EARLY) -- double-check that the node admits entry given
      the current graph state
    - Update (Priority.NORMAL) -- execute state updates
    - Processing (Priority.LATE) -- handle any dynamic behaviors assigned to the node
    - Continues (Priority.LAST) -- check if the node wants to refer the cursor to
      somewhere else after handling the node (jump or jnr with exit)
    """
    visited: bool = False     # Has _ever_ been visited
    wants_exit: bool = False  # Currently being processed

    graph: TraversableGraph = Field(default_factory=DefaultTraversableGraph, json_schema_extra={'cmp': False})

    @property
    def edges(self: Node) -> List[Edge]:
        return self.find_children(Edge)

    @property
    def redirects(self: Node) -> list[Edge]:
        return self.find_children(Edge, lambda x: x.activation == "first")

    @property
    def continues(self: Node) -> list[Edge]:
        return self.find_children(Edge, lambda x: x.activation == "last")

    def enter(self, **kwargs):
        return TraversalHandler.enter_node(self, **kwargs)

    def exit(self, **kwargs):
        return TraversalHandler.exit_node(self, **kwargs)

    @TraversalHandler.enter_strategy(priority=TraversalStage.REDIRECTION)
    def _check_for_redirect(self: TraversableNode, **kwargs) -> Optional[EdgeProtocol]:
        for edge in self.redirects:
            if isinstance(edge, Lockable) and edge.available(**kwargs):
                return edge

    @TraversalHandler.enter_strategy(priority=TraversalStage.VALIDATION)
    def _check_availability(self: TraversableNode, **kwargs):
        if isinstance(self, Lockable) and not self.available(**kwargs):
            raise RuntimeError

    @TraversalHandler.enter_strategy(priority=TraversalStage.BOOK_KEEPING)
    def _arrival_bookkeeping(self: TraversableNode, **kwargs):
        # passed availability, we can arrive, but not visited until exit
        self.wants_exit = True

    @TraversalHandler.enter_strategy(priority=TraversalStage.UPDATING)
    def _apply_effects(self: TraversableNode, **kwargs):
        if isinstance(self, HasEffects):
            self.apply_effects(**kwargs)

    @TraversalHandler.enter_strategy(priority=TraversalStage.CONTINUING)
    def _check_for_continue(self: TraversableNode, **kwargs) -> Optional[EdgeProtocol]:
        for edge in self.continues:
            if isinstance(edge, Lockable) and edge.available(**kwargs):
                return edge

    @TraversalHandler.exit_strategy(priority=TraversalStage.BOOK_KEEPING)
    def _departure_bookkeeping(self: TraversableNode, **kwargs):
        self.wants_exit = False
        self.visited = True

    def find_entry_node(self: TraversableNode) -> TraversableNode:
        return TraversalHandler.find_entry_node(self.children)

    @property
    def is_entry(self) -> bool:
        return self.has_tags("is_entry") or self.label == "start"
