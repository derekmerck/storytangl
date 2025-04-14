from __future__ import annotations

import logging

from uuid import UUID
from typing import Optional, Literal, Iterable
from logging import getLogger

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel, Uid
from tangl.entity import BaseEntityHandler, Entity
from tangl.entity.mixins import Lockable, AvailabilityHandler, NamespaceHandler
from ..node import Node, NodeType

logger = getLogger("tangl.traversal")
logger.setLevel(logging.WARNING)

class TraversalHandler(BaseEntityHandler):
    """
    Orchestrates traversal logic across nodes and graphs, employing strategies to manage entity behaviors during traversal.

    Key Features:
      - **Strategy Management**: Utilizes `strategy`, `enter_strategy`, and `exit_strategy` decorators to define and prioritize traversal behaviors, enabling flexible and context-sensitive interactions.
      - **Traversal Operations**: Facilitates core traversal actions (`enter`, `exit`, `follow`), including strategy invocation for entering/exiting nodes or edges and handling common ancestor finding during transitions.
    """

    # -----------
    # Decorators
    # -----------

    @classmethod
    def enter_strategy(cls, func):
        return cls.strategy(func, strategy_annotation="enter_strategy")

    @classmethod
    def exit_strategy(cls, func):
        return cls.strategy(func, strategy_annotation="exit_strategy")

    # -----------
    # Interface
    # -----------

    @classmethod
    def enter(cls,
              traversable: TraversableNode | TraversableGraph,
              with_edge: Edge = None) -> Edge:
        logger.debug(f"entering {traversable.label}")
        if next_edge := cls.invoke_strategies(traversable,
                                              with_edge=with_edge,
                                              strategy_annotation="enter_strategy",
                                              result_handler="first"):
            if isinstance(next_edge, Edge):
                logger.debug(f"Following next-edge {next_edge.label}")
                return cls.follow_edge(next_edge)

    @classmethod
    def exit(cls,
             traversable: TraversableNode | TraversableGraph,
             with_edge: Edge = None) -> Edge:
        if next_edge := cls.invoke_strategies(traversable,
                                              with_edge=with_edge,
                                              strategy_annotation="exit_strategy",
                                              result_handler="first"):
            if isinstance(next_edge, Edge):
                return cls.follow_edge(next_edge)

    @classmethod
    def follow_edge(cls, edge: Edge):
        logger.debug(f"in follow-edge {edge.label}")
        if not edge.available():
            raise RuntimeError("Tried to follow unavailable edge!")

        if edge.predecessor:
            if next_edge := cls.exit(edge.predecessor, with_edge=edge):
                logger.debug( f'redirecting on exit {edge.predecessor.label}')
                return cls.follow_edge(next_edge)
            cls._find_common_ancestor(edge.predecessor, edge.successor)

        edge.graph.cursor = edge.successor
        if next_edge := cls.enter(edge.successor, with_edge=edge):
            logger.debug(f'redirecting on enter {edge.successor.label}')
            return cls.follow_edge(next_edge)

    @classmethod
    def goto_node(cls, graph: TraversableGraph, node: TraversableNode):
        # Create a temporary edge from the cursor to the target node to invoke
        # the possible context change on follow rather than directly entering
        # the target
        # todo: test this with various jumps up, peer, and down -- invoking the
        #       context exit can result in a recursion trying to re-enter own parent?
        if graph.cursor:
            cls.exit(graph.cursor)  # don't follow any redirects
            cls._find_common_ancestor(graph.cursor, node)
        graph.cursor = node
        cls.enter(node)             # don't follow any redirects

    @classmethod
    def get_traversal_status(cls, graph: TraversableGraph):
        from .plugins import PluginHandler
        if status_results := PluginHandler.on_get_traversal_status(graph.pm, graph):
            return status_results[-1]
        return [{'key': 'status', 'value': 'unavailable'}]

    # -----------
    # Context Helper
    # -----------

    @classmethod
    def _find_common_ancestor(cls, predecessor: NodeType, successor: NodeType) -> Edge:
        """
        This approach should support popping out of and pushing into dynamic contexts,
        where traversable nodes may change parentage, for example.
        """
        if not predecessor:
            return

        logger.debug("Finding common ancestor")

        predecessor_ancestors = predecessor.ancestors()
        logger.debug(f'predecessor ancestors: f{[x.label for x in predecessor_ancestors]}')
        successor_ancestors = successor.ancestors()
        logger.debug(f'successor ancestors: f{[x.label for x in successor_ancestors]}')

        shared_ancestors = []
        while predecessor_ancestors:
            a = predecessor_ancestors.pop(0)  # order is [me ... root]
            if a is predecessor:
                continue
            if a not in successor_ancestors:
                logger.debug(f'exiting ancestor {a.label}')
                if next_edge := cls.exit(a):
                    logger.debug(f'redirecting to {next_edge.label} on exiting parent {a.label}')
                    return cls.follow_edge(next_edge)
            else:
                logger.debug(f'ignoring ancestor {a.label}')
                shared_ancestors.append(a)

        # new_successor_ancestors = successor_ancestors[:-len(predecessor_ancestors)]
        # ignore our shared ancestors, which have presumably already been entered

        logger.debug(f'revised successor ancestors: f{[x.label for x in successor_ancestors]}')
        while successor_ancestors:
            a = successor_ancestors.pop()
            if a is successor or a in shared_ancestors:
                # we don't need to enter it
                continue
            logger.debug(f'entering ancestor {a.label}')
            if next_edge := cls.enter(a):
                logger.debug(f'redirecting to {next_edge.label} on entering parent {a.label}')
                return cls.follow_edge(next_edge)

    @classmethod
    def find_entry_node(cls, nodes: Iterable[TraversableNode]) -> TraversableNode:
        from tangl.graph import Graph
        entry_node = Graph._find_nodes(
            nodes,
            TraversableNode,
            lambda x: x.is_entry and x.available())
        if not entry_node:
            raise RuntimeError("Unable to infer an entry node for the graph traversal")
        return entry_node[0]


class TraversableGraph(BaseModel):
    """
    Manages a graph of `TraversableNode` instances, facilitating the traversal process through cursor manipulation and step counting.

    - Key Features:
      - **Cursor Management**: Maintains a `cursor` to track the current node in focus, with getter and setter methods for moving the cursor within the graph.
      - **Traversal Progress**: Utilizes `step_count` to monitor traversal steps, aiding in navigation and interaction timing.
      - **Node Navigation**: Implements methods (`enter`, `follow_edge`, `goto_node`, `exit`) to navigate between nodes, invoking `TraversalHandler` strategies for entering, following edges, or exiting nodes.
    """

    cursor_id: UUID = None

    @property
    def cursor(self) -> TraversableNode:
        if self.cursor_id:
            return self.nodes.get(self.cursor_id)

    @cursor.setter
    def cursor(self, value: NodeType):
        if value:
            self.cursor_id = value.uid

    step_count: int = 0

    # -----------
    # Handler Interface
    # -----------

    def enter(self, entry_node: TraversableNode = None):
        if entry_node:
            self.cursor = entry_node
        TraversalHandler.enter(self)

    def follow_edge(self, edge: Edge):
        self.step_count += 1
        TraversalHandler.follow_edge(edge)

    def goto_node(self, node: TraversableNode):
        TraversalHandler.goto_node(self, node)

    def exit(self):
        TraversalHandler.exit(self)

    def get_traversal_status(self):
        return TraversalHandler.get_traversal_status(self)

    # -----------
    # Strategies
    # -----------

    @TraversalHandler.enter_strategy
    def _find_entry_node(self, **kwargs):
        if not self.cursor:
            logger.debug('Trying to find entry node (Graph)')
            self.cursor = TraversalHandler.find_entry_node(self.nodes.values())

class TraversableNode(BaseModel):
    """
    Extends `Node` functionality to support graph traversal, including visit tracking, redirection, and content rendering.

    Key Features:
      - **Visit Tracking**: Tracks visits to a node through a `visits` list, allowing for queries on visit history and time since last visit.
      - **Entry and Exit**: Defines entry and exit points within a node, leveraging `TraversalHandler` strategies for behaviors upon entering or exiting.
      - **Redirection and Continuation**: Implements strategies to redirect to other nodes upon entry (`_check_for_redirects`) or continue traversal upon exit (`_check_for_continues`), based on edge availability and activation conditions.
      - **Effect Application and Content Rendering**: Supports applying effects (`_apply_effects`) and rendering node-specific content (`_render_content`), potentially integrating with a journal for tracking narrative progression.
    """

    visits: list[int] = Field(default_factory=list)
    repeatable: bool | int = True

    def visit(self):
        graph = self.graph  # type: TraversableGraph
        if hasattr(graph, 'step_count'):
            self.visits.append(graph.step_count)
        else:
            self.visits.append(1)

    @property
    def num_visits(self):
        return len(self.visits)

    @property
    def visited(self):
        return bool(self.num_visits)

    completed = visited

    def turns_since(self, turn: int = None) -> int:
        if not self.visited or not hasattr(self.graph, 'step_count'):
            return -1
        if turn is None:
            graph = self.graph  # type: TraversableGraph
            turn = graph.step_count
        return turn - self.visits[-1]

    @property
    def is_entry(self: NodeType):
        # look for 'is_entry' or 'start' in tags and locals
        return self.has_tags('is_entry') or self.has_tags("start") or (
               hasattr(self, "locals") and (self.locals.get("is_entry") or
                                            self.locals.get("start"))) or (
            self.label in ['start', 'entry']
        )

    @property
    def edges(self: NodeType) -> list[Edge]:
        return self.find_children(Edge)

    # -----------
    # Handler Interface
    # -----------

    def enter(self):
        return TraversalHandler.enter(self)

    def exit(self):
        return TraversalHandler.exit(self)

    # -----------
    # Strategies
    # -----------

    @NamespaceHandler.strategy
    def _include_traversal_props(self):
        return {
            'visits': self.visits,
            'visited': self.visited,
            'num_visits': self.num_visits,
            'turns_since': self.turns_since  # method
        }

    @TraversalHandler.enter_strategy
    def _check_for_redirects(self: NodeType, **kwargs) -> Edge:
        logger.debug(f"Entering check redirects for {self.label}")
        candidates = list(filter(lambda x: x.activation == "enter" and x.available(), self.edges))
        if candidates:
            logger.debug(f"Found redirect: {candidates[0].label}")
            return candidates[0]
    _check_for_redirects.strategy_priority = 10

    @TraversalHandler.enter_strategy
    def _mark_visited(self: NodeType, **kwargs):
        logger.debug(f"Entering visit for {self.label}")
        self.visit()
    _mark_visited.strategy_priority = 20

    @TraversalHandler.enter_strategy
    def _apply_effects(self: NodeType, **kwargs):
        logger.debug(f"Entering apply effect for {self.label}")
        if hasattr(self, "apply_effects"):
            logger.debug("Found effects attrib")
            self.apply_effects()
            # Don't return anything or it will be interpreted as the next node
    _apply_effects.strategy_priority = 30

    @TraversalHandler.enter_strategy
    def _render_content(self: NodeType, **kwargs):
        logger.debug(f"Entering render for {self.label}")
        if hasattr(self, "render"):
            res = self.render()
            if hasattr(self.graph, "journal"):
                self.graph.journal.push_update(res)
    _render_content.strategy_priority = 80

    @TraversalHandler.enter_strategy
    def _check_for_continues(self, **kwargs) -> Edge:
        logger.debug(f"Entering check continues for {self.label}")
        candidates = list(filter(lambda x: x.activation == "exit" and x.available(), self.edges))
        if candidates:
            logger.debug(f"Found continue: {candidates[0].label}")
            return candidates[0]
    _check_for_continues.strategy_priority = 90


EdgeActivationType = Optional[Literal['enter', 'exit']]

class Edge(Lockable, Node):
    """
    Represents connections between nodes, with support for conditional activation and dynamic linking based on traversal context.

    Key Features:
      - **Conditional Activation**: Includes an `activation` attribute to specify when the edge is active (on entering or exiting a node), affecting traversal flow.
      - **Dynamic Linking**: Allows for setting successor nodes dynamically, accommodating flexible narrative structures where connections may change over time.
      - **Availability Check**: Implements an `avail` method to assess the edge's availability for traversal, considering the successor node's availability.
    """

    activation: EdgeActivationType = None

    @property
    def predecessor(self: NodeType) -> TraversableNode:
        return self.parent

    successor_ref: UniqueLabel | UUID

    @property
    def successor(self: NodeType) -> TraversableNode:
        return self.graph.get_node(self.successor_ref)

    @successor.setter
    def successor(self: NodeType, node: NodeType):
        if node:
            if isinstance(node, (Uid, UniqueLabel)):
                self.successor_ref = node
            elif isinstance(node, Entity):
                self.successor_ref = node.uid

    @AvailabilityHandler.strategy
    def _check_successor(self):
        return self.successor.available()

