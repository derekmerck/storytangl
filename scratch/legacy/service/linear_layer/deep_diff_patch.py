# extends linear with graph version history and undo-able state diffs
from deepdiff import DeepDiff, Delta

from tangl.type_hints import UnstructuredData
from tangl.utils.bookmarked_list import BName, BType
from tangl.core.graph import Node, Graph
from tangl.core.fragment import ContentFragment
from .has_linear_layer import HasLinearLayer

class GraphDeltaFragment(ContentFragment):
    # todo: this isn't really a _content_ fragment, it's a different kind of projection
    #       but calling it a content fragment satisfies type checking on linear layer

    graph_delta: Delta

    def apply_graph_delta(self) -> Graph:
        graph_data = self.graph.unstructure()
        graph_data = graph_data + self.graph_delta
        return Graph.structure(graph_data)

    def unapply_graph_delta(self) -> Graph:
        graph_data = self.graph.unstructure()
        graph_data = graph_data - self.graph_delta
        return Graph.structure(graph_data)

    @classmethod
    def from_graph_delta(cls, current_graph: Graph, snapshot: UnstructuredData):
        graph_data = current_graph.unstructure()
        delta = DeepDiff(graph_data, snapshot, bidirectional=True)
        return cls(graph_delta=delta)

class HasLinearHistory(HasLinearLayer):
    # todo: want to tie together with linear content layer updates

    def advance_history(self, snapshot: UnstructuredData, bookmark_name: BName = None, bookmark_type: BType = None, **kwargs) -> None:
        delta_fragment = GraphDeltaFragment.from_graph_delta(self.graph, snapshot)
        self.linear_layer.add_item(delta_fragment, bookmark_name=bookmark_name, bookmark_type=bookmark_type)

    def undo_history(self, *args, **kwargs) -> Graph:
        graph_delta = self.linear_layer.pop()
        return graph_delta.unapply_graph_delta()
