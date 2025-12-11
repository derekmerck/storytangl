from __future__ import annotations
from typing import Iterable, Callable, Optional, TYPE_CHECKING
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from tangl.graph.node import NodeRef, Node
from tangl.entity.mixins import StrategicHandler, AvailabilityHandler, Lockable

if TYPE_CHECKING:
    from .graph_traversal import TraversableGraph



class TraversalHandler(StrategicHandler):
    """
    The Node Traversal Handler (NTH) provides nodes with `enter` and `exit` methods that
    can be used by the Graph Traversal Handler (GTH).

    Both methods can be used for traversal bookkeeping (tracking visits, etc), and both
    can optionally return an Edge, indicating that the GTH should either redirect
    or continue updating the cursor rather than awaiting a "follow edge" instruction.

    plugin hooks:  on_enter_node, on_exit_node
    """
    # Wrt story-nodes, only scenes (containers of related blocks), blocks (narrative beats),
    # and actions (edges between beats) are traversable

    @classmethod
    def entry_strategy(cls, func: Callable):
        return cls.strategy(func, strategy_annotation='is_entry_strategy')

    @classmethod
    def enter_strategy(cls, func: Callable):
        return cls.strategy(func, strategy_annotation='is_enter_strategy')

    @classmethod
    def exit_strategy(cls, func: Callable):
        return cls.strategy(func, strategy_annotation='is_exit_strategy')

    @classmethod
    def is_entry(cls, node: Traversable) -> bool:
        res = cls.invoke_strategies(node, strategy_annotation="is_entry_strategy")
        if any(res):
            return True

    @classmethod
    def enter(cls, node: Traversable) -> Optional[Edge]:
        if hasattr(node, 'pm') and node.pm:
            from .plugins import PluginHandler
            if extra_redirect := PluginHandler.on_enter_node( node.pm, node ):
                return extra_redirect
        redirects = cls.invoke_strategies(node, strategy_annotation='is_enter_strategy')  # list of nodes
        # call plugins
        # print( redirects )
        if redirects:
            # should be first valid redirect
            return redirects[0]

    @classmethod
    def exit(cls, node: Traversable) -> Optional[Edge]:
        if hasattr(node, 'pm') and node.pm:
            from .plugins import PluginHandler
            if extra_continue := PluginHandler.on_exit_node( node.pm, node ):
                return extra_continue
        continues = cls.invoke_strategies(node, strategy_annotation='is_exit_strategy')  # list of nodes
        # call plugins
        if continues:
            return continues[0]


class Traversable(BaseModel):

    @TraversalHandler.entry_strategy
    def _check_is_entry(self) -> bool:
        return self.label in ["start", "entry"] or \
            self.has_tags({"is_entry"}) or \
            (hasattr(self, 'locals') and self.locals.get("is_entry"))

    @property
    def is_entry(self):
        return TraversalHandler.is_entry(self)

    # track graph traversal counter when visited
    visits: list = Field(default_factory=list)
    repeatable: bool = False

    @property
    def visited(self) -> bool:
        return len(self.visits) > 0

    @property
    def completed(self) -> bool:
        return self.visited and not self.repeatable

    @property
    def turns_since(self) -> int:
        if not self.visited:
            return -1
        if hasattr(self.graph, "choice_counter"):
            self.graph: TraversableGraph
            self.graph: TraversableGraph
            return self.graph.choice_counter - self.visits[-1]
        return 0

    def visit(self):
        if hasattr(self.graph, "choice_counter"):
            self.graph: TraversableGraph
            self.visits.append(self.graph.choice_counter)
        else:
            self.visits.append(0)

    @AvailabilityHandler.strategy
    def _is_repeatable_or_unvisited(self):
        return self.repeatable or not self.visited

    @property
    def edges(self: Node) -> Iterable[Edge]:
        return self.find_children(Edge)

    @property
    def choices(self: Node) -> Iterable[Edge]:
        trigger_type = Edge.TraversalTrigger.CHOICE
        return filter(lambda x: x.trigger is trigger_type, self.edges)

    @property
    def redirects(self: Node) -> Iterable[Edge]:
        trigger_type = Edge.TraversalTrigger.REDIRECT
        return filter(lambda x: x.trigger is trigger_type, self.edges)

    def redirect_available(self) -> Optional[Edge]:
        candidates = filter(lambda x: x.available(), self.redirects)
        if candidates:
            return next(candidates, None)

    @property
    def continues(self: Node) -> Iterable[Edge]:
        trigger_type = Edge.TraversalTrigger.CONTINUE
        return filter(lambda x: x.trigger is trigger_type, self.edges)

    def continue_available(self) -> Optional[Edge]:
        candidates = filter(lambda x: x.available(), self.continues)
        if candidates:
            return next(candidates, None)

    @TraversalHandler.enter_strategy
    def _redirect_or_enter(self: Node) -> Optional[Edge]:
        if redirect_edge := self.redirect_available():
            return redirect_edge
        # do node setup bookkeeping here
        self.visit()

    # @TraversalHandler.exit_strategy
    # def _exit_and_continue(self: Node) -> Optional[Edge]:
    #     # Do node teardown bookkeeping here
    #     if continue_edge := self.continue_available():
    #         return continue_edge

    def enter(self: Traversable) -> Optional[Edge]:
        return TraversalHandler.enter(self)

    def exit(self: Traversable) -> Optional[Edge]:
        return TraversalHandler.exit(self)

