from __future__ import annotations

from uuid import UUID

from tangl.core import Graph, GraphFactory

from .traversable import TraversableNode, assert_traversal_contracts


class TraversableGraph(Graph):
    """Graph subtype carrying traversal-ready entry metadata.

    ``initial_cursor_id`` is traversal metadata derived from graph shape by the
    VM factory. It is not session state; ``Ledger`` still owns the live cursor.
    """

    initial_cursor_id: UUID | None = None


class TraversableGraphFactory(GraphFactory):
    """Thin VM authority over :class:`tangl.core.GraphFactory`.

    The VM layer adds only two behaviors on top of core eager materialization:
    validate traversal contracts and stamp the default traversal entry cursor.
    """

    graph_type: type[Graph] = TraversableGraph

    def materialize_graph(
        self,
        graph: TraversableGraph | None = None,
        **kwargs,
    ) -> TraversableGraph:
        if graph is not None and not isinstance(graph, TraversableGraph):
            raise TypeError("TraversableGraphFactory requires a TraversableGraph instance")

        materialized = super().materialize_graph(graph=graph, **kwargs)
        if not isinstance(materialized, TraversableGraph):
            raise TypeError("TraversableGraphFactory must materialize a TraversableGraph")

        entry = self.get_entry_cursor(materialized)
        if entry is None:
            raise ValueError("TraversableGraphFactory could not resolve an initial entry cursor")
        if not isinstance(entry, TraversableNode):
            raise TypeError(
                "TraversableGraphFactory entry cursor must be a TraversableNode, "
                f"got {entry.__class__.__name__}",
            )

        materialized.initial_cursor_id = entry.uid
        assert_traversal_contracts(materialized)
        return materialized
