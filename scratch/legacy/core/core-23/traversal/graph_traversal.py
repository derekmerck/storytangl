from __future__ import annotations
from typing import Optional, Mapping, Iterable, ClassVar

from pydantic import BaseModel, Field

from tangl.type_hints import Uid, Turn
from tangl.journal import Journal, JournalHandler
from tangl.graph.node import Node, Graph
from tangl.entity.mixins import StrategicHandler
from .traversable import Traversable, Edge, TraversalHandler

class GraphTraversalHandler(StrategicHandler):
    """
    Handles the traversal of nodes within a TraversableGraph. This class is responsible
    for moving the cursor through the graph based on the edges and node availability.

    Methods:
        follow_edge: Follows an edge to update the graph's cursor.
        update_cursor: Updates the cursor to a new node, handling redirections and updates.
        get_traversal_status: Retrieves the current traversal status of the graph.
    """

    @classmethod
    def follow_edge(cls, graph: TraversableGraph, edge: Edge):

        if not edge.available():
            raise RuntimeError(f'Edge {edge} is not available!')

        edge.apply_effects()

        if edge.trigger is Edge.TraversalTrigger.CHOICE:
            # todo, if starting a new scene, push the scene_id as the entry key
            JournalHandler.start_new_entry( graph.journal )
            graph.choice_counter += 1

        cls.update_cursor(graph, edge.successor)

    @classmethod
    def update_cursor(cls,
                      graph: TraversableGraph,
                      next_node: Traversable,
                      allow_redirects: bool = True):
        """
        Steps in updating the graph cursor-node.

        1. Confirm that the next node is available
        2. Check with the next node to see if it wants to redirect the cursor somewhere else (a "redirect" edge)
        3. If so, call "follow edge" on the redirect edge
        4. If not, set the cursor to the next node
        5. Invoke the cursor node's effects
        6. Render the cursor node's journal update i.e., {'text': 'You are standing in front of a white house.'} and addend it to the graph's journal
        7. Check with the cursor node post-update to see if it wants to redirect the cursor somewhere else (a "continue" edge)
        8. If so, call "follow edge" on the continue edge to generate the next update
        9. If not, wait for the next user choice (a follow edge on a "choice" edge)
        """
        # todo: need a recursion sentinel/counter to prevent inf visits
        # todo: if new cursor parent is not in old cursor ancestors, then exit current parent and enter new parent first?

        if not next_node.available():
            raise RuntimeError(f"Node {next_node} unavailable!")

        if allow_redirects and (redirect_edge := next_node.enter()):
            # this is jump, need to handle jnr also
            cls.follow_edge(graph, redirect_edge)

        graph.cursor = next_node

        graph.cursor.apply_effects()

        update = graph.cursor.render()
        JournalHandler.push_update( graph.journal, update )

        if continue_edge := graph.cursor.continue_available():
            # this is jump, need to handle jnr also
            cls.follow_edge(graph, continue_edge)

    @classmethod
    def get_traversal_status(cls, graph: TraversableGraph) -> Mapping | list[Mapping]:
        if hasattr(graph, 'pm') and graph.pm:
            from .plugins import PluginHandler
            if status_results := PluginHandler.on_get_traversal_status(graph.pm, graph):
                return status_results[-1]
        return [{'key': 'status', 'value': 'unavailable'}]

    @classmethod
    def find_entry_node(cls, nodes: Iterable[Traversable]) -> Traversable:
        candidates = list( filter( lambda x: TraversalHandler.is_entry(x), nodes ) )
        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            raise RuntimeError(f'Too many nodes marked as graph entry {[n.label for n in candidates]}, unable to determine entry node!')
        raise RuntimeError('No node marked as graph entry, unable to determine entry node!')

    @classmethod
    def enter(cls, graph: TraversableGraph, entry_node: Node = None) -> Optional[Edge]:
        # No need to call plugin manager b/c we can do state setup in _on_init_graph_
        if not entry_node:
            entry_node = cls.find_entry_node(graph.nodes.values())
        return cls.update_cursor(graph, next_node=entry_node)
        # graph traversal handler should iterate through continues if necessary

    @classmethod
    def exit(cls, graph: TraversableGraph):
        if hasattr(graph, 'pm') and graph.pm:
            from .plugins import PluginHandler
            PluginHandler.on_exit_graph(graph)


class TraversableGraph(BaseModel):
    """
    Represents a graph capable of being traversed in a narrative or game environment.

    Attributes:
        journal: A Journal object that tracks the narrative's progress and events.
        choice_counter: A counter indicating the number of choices made in the traversal.
        cursor_uid: The unique identifier of the current node (cursor) in the graph.

    Properties:
        cursor: Gets or sets the current cursor node in the graph.
    """
    # todo: probably need some kind of scheduler for events (ie, invoke x in 3 turns)
    # todo: probably need some kind of return stack for jnr edges

    journal: Journal = Field(default_factory=Journal)
    choice_counter: Turn = 0

    @property
    def turn(self) -> Turn:
        # alias to 'choice counter'
        return self.choice_counter

    @turn.setter
    def turn(self, value: Turn):
        self.choice_counter = value

    cursor_uid: Uid = None

    @property
    def cursor(self: Graph) -> Optional[Traversable]:
        if self.cursor_uid:
            return self.get_node( self.cursor_uid )

    @cursor.setter
    def cursor(self: Graph, node: Node):
        self.cursor_uid = node.uid

    def enter(self: TraversableGraph, entry_node: Traversable = None):
        return GraphTraversalHandler.enter(self, entry_node)

    def exit(self: TraversableGraph) -> Optional[Edge]:
        return GraphTraversalHandler.exit(self)

# class ContainerNode:
#     pass
#
# class ContainerTraversalHandler(GraphTraversalHandler):
#     """
#     Support for TraversableGraphs with multiple sub-graphs.
#
#     `enter()` requires determining both the default entry container and the entry child.
#
#     For a Story-type graph, the container class is Scene and the contained class is Block.
#
#     Entering the block will automatically enter the parent scene first.
#     """
#
#     container_node_cls: ClassVar[type[ContainerNode]] = ContainerNode
#     contained_node_cls: ClassVar[type[Traversable]] = Traversable
#
#     @classmethod
#     def find_entry_node(cls, graph: TraversableGraph) -> Traversable:
#         candidate_containers = list(
#             graph.find_nodes(cls.container_node_cls, filt=lambda x: TraversalHandler.is_entry(x)))
#         if len(candidate_containers) == 1:
#             entry_container = candidate_containers[0]  # type: ContaainerNode
#             candidate_nodes = list(
#                 entry_container.find_children(Traversable, filt=lambda x: TraversalHandler.is_entry(x)))
#             if len(candidate_nodes) == 1:
#                 return candidate_nodes[0]
#             elif len(candidate_nodes) > 1:
#                 raise RuntimeError(
#                     f'Unable to determine entry node, too many blocks marked as entry in scene! {[n.label for n in candidate_nodes]} in {entry_container.label}')
#             raise RuntimeError(
#                 f'Unable to determine entry node, no block marked as entry in scene {entry_container.label}!')
#         elif len(candidate_containers) > 1:
#             raise RuntimeError(
#                 f'Unable to determine entry node, too many containers marked as entry! {[n.label for n in candidate_containers]}')
#         raise RuntimeError('Unable to determine entry node, no scene marked as entry!')
