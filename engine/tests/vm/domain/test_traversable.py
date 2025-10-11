"""Tests for :mod:`tangl.vm.domain.traversable`."""

from __future__ import annotations

from tangl.core import Graph
from tangl.vm.domain import TraversableDomain
from tangl.vm.frame import ChoiceEdge, ResolutionPhase as P


class TestTraversableDomain:
    """Behavioural coverage for :class:`TraversableDomain`."""

    def test_creates_source_and_sink_nodes(self) -> None:
        graph = Graph(label="test")
        first = graph.add_node(label="first")
        second = graph.add_node(label="second")

        domain = TraversableDomain(
            graph=graph,
            label="section",
            member_ids=[first.uid, second.uid],
        )

        assert graph.get(domain.source.uid) is domain.source
        assert graph.get(domain.sink.uid) is domain.sink
        assert "SOURCE" in domain.source.label
        assert "SINK" in domain.sink.label
        assert {"abstract", "source", "hidden"}.issubset(set(domain.source.tags))
        assert {"abstract", "sink", "hidden"}.issubset(set(domain.sink.tags))

    def test_source_links_to_entry_nodes(self) -> None:
        graph = Graph(label="test")
        entry_a = graph.add_node(label="entry_a")
        entry_b = graph.add_node(label="entry_b")
        middle = graph.add_node(label="middle")

        domain = TraversableDomain(
            graph=graph,
            label="section",
            member_ids=[entry_a.uid, entry_b.uid, middle.uid],
            entry_ids=[entry_a.uid, entry_b.uid],
        )

        destinations = {
            edge.destination.uid
            for edge in domain.source.edges_out(is_instance=ChoiceEdge)
            if edge.destination is not None
        }
        assert entry_a.uid in destinations
        assert entry_b.uid in destinations
        assert middle.uid not in destinations

        phases = {
            edge.trigger_phase
            for edge in domain.source.edges_out(is_instance=ChoiceEdge)
        }
        assert phases == {P.PREREQS}

    def test_exit_nodes_link_to_sink(self) -> None:
        graph = Graph(label="test")
        middle = graph.add_node(label="middle")
        exit_a = graph.add_node(label="exit_a")
        exit_b = graph.add_node(label="exit_b")

        domain = TraversableDomain(
            graph=graph,
            label="section",
            member_ids=[middle.uid, exit_a.uid, exit_b.uid],
            exit_ids=[exit_a.uid, exit_b.uid],
        )

        for node in (exit_a, exit_b):
            destinations = {
                edge.destination.uid
                for edge in node.edges_out(is_instance=ChoiceEdge)
                if edge.destination is not None
            }
            assert domain.sink.uid in destinations

            triggers = {
                edge.trigger_phase
                for edge in node.edges_out(is_instance=ChoiceEdge)
            }
            assert triggers == {P.POSTREQS}

    def test_defaults_entry_and_exit_nodes(self) -> None:
        graph = Graph(label="test")
        first = graph.add_node(label="first")
        middle = graph.add_node(label="middle")
        last = graph.add_node(label="last")

        domain = TraversableDomain(
            graph=graph,
            label="section",
            member_ids=[first.uid, middle.uid, last.uid],
        )

        assert domain.entry_node_ids == [first.uid]
        assert domain.exit_node_ids == [last.uid]

        destinations = {
            edge.destination.uid for edge in domain.source.edges_out(is_instance=ChoiceEdge)
        }
        assert first.uid in destinations

        exit_destinations = {
            edge.destination.uid for edge in last.edges_out(is_instance=ChoiceEdge)
        }
        assert domain.sink.uid in exit_destinations

    def test_has_forward_progress_when_path_exists(self) -> None:
        graph = Graph(label="test")
        start = graph.add_node(label="start")
        middle = graph.add_node(label="middle")
        end = graph.add_node(label="end")

        ChoiceEdge(graph=graph, source_id=start.uid, destination_id=middle.uid)
        ChoiceEdge(graph=graph, source_id=middle.uid, destination_id=end.uid)

        domain = TraversableDomain(
            graph=graph,
            label="section",
            member_ids=[start.uid, middle.uid, end.uid],
            entry_ids=[start.uid],
            exit_ids=[end.uid],
        )

        assert domain.has_forward_progress(start) is True
        assert domain.has_forward_progress(middle) is True
        assert domain.has_forward_progress(end) is True

    def test_has_forward_progress_detects_softlock(self) -> None:
        graph = Graph(label="test")
        start = graph.add_node(label="start")
        dead_end = graph.add_node(label="dead_end")
        exit_node = graph.add_node(label="exit")

        ChoiceEdge(graph=graph, source_id=start.uid, destination_id=dead_end.uid)

        domain = TraversableDomain(
            graph=graph,
            label="section",
            member_ids=[start.uid, dead_end.uid, exit_node.uid],
            entry_ids=[start.uid],
            exit_ids=[exit_node.uid],
        )

        assert domain.has_forward_progress(dead_end) is False

    def test_has_forward_progress_respects_namespace(self) -> None:
        graph = Graph(label="test")
        start = graph.add_node(label="start")
        gate = graph.add_node(label="gate")
        exit_node = graph.add_node(label="exit")

        locked_edge = ChoiceEdge(
            graph=graph,
            source_id=start.uid,
            destination_id=gate.uid,
            predicate=lambda ns: ns.get("has_key", False),
        )
        ChoiceEdge(graph=graph, source_id=gate.uid, destination_id=exit_node.uid)

        domain = TraversableDomain(
            graph=graph,
            label="section",
            member_ids=[start.uid, gate.uid, exit_node.uid],
            entry_ids=[start.uid],
            exit_ids=[exit_node.uid],
        )

        assert domain.has_forward_progress(start, ns={"has_key": False}) is False
        assert domain.has_forward_progress(start, ns={"has_key": True}) is True

    def test_has_forward_progress_ignores_unsatisfied_edges(self) -> None:
        graph = Graph(label="test")
        start = graph.add_node(label="start")
        gate = graph.add_node(label="gate")
        exit_node = graph.add_node(label="exit")

        edge_to_gate = ChoiceEdge(graph=graph, source_id=start.uid, destination_id=gate.uid)
        ChoiceEdge(graph=graph, source_id=gate.uid, destination_id=exit_node.uid)

        domain = TraversableDomain(
            graph=graph,
            label="section",
            member_ids=[start.uid, gate.uid, exit_node.uid],
            entry_ids=[start.uid],
            exit_ids=[exit_node.uid],
        )

        object.__setattr__(edge_to_gate, "satisfied", False)
        assert domain.has_forward_progress(start) is False

        object.__setattr__(edge_to_gate, "satisfied", True)
        assert domain.has_forward_progress(start) is True

    def test_rejects_nodes_outside_domain(self) -> None:
        graph = Graph(label="test")
        first = graph.add_node(label="first")
        second = graph.add_node(label="second")
        outsider = graph.add_node(label="outsider")

        domain = TraversableDomain(
            graph=graph,
            label="section",
            member_ids=[first.uid, second.uid],
        )

        try:
            domain.has_forward_progress(outsider)
        except ValueError:
            pass
        else:  # pragma: no cover - defensive assertion
            raise AssertionError("Expected ValueError for node outside domain")
