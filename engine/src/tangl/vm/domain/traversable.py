"""Canonical traversal domains for VM resolution flow."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field, PrivateAttr, model_validator

from tangl.core import Graph, Node
from tangl.core.domain import DomainSubgraph
from tangl.vm.frame import ChoiceEdge, ResolutionPhase as P

__all__ = ["TraversableDomain"]


class TraversableDomain(DomainSubgraph):
    """TraversableDomain(label: str, member_ids: list[UUID], entry_ids: list[UUID] | None = None, exit_ids: list[UUID] | None = None)

    Structural domain that exposes a canonical source/sink for resolution flow.

    Why
    ----
    Frame traversal needs well-defined entry/exit anchors so bounded sections can
    detect forward progress and softlocks deterministically. ``TraversableDomain``
    wires hidden source/sink nodes to the supplied members, ensuring that every
    bounded section presents a single inbound edge and a single outbound edge.

    Key Features
    ------------
    * **Canonical wiring** – introduces hidden ``SOURCE``/``SINK`` nodes and
      links entries/exits with :class:`~tangl.vm.frame.ChoiceEdge` instances.
    * **Reachability checks** – :meth:`has_forward_progress` verifies that the
      sink is reachable from a given node using only satisfied choice edges.
    * **Composable sections** – the synthetic nodes let nested domains connect
      without rewriting member graphs.

    API
    ---
    - :attr:`entry_node_ids` / :attr:`exit_node_ids` – real nodes used as entry
      and exit points.
    - :meth:`source` / :meth:`sink` – synthetic nodes that anchor traversal.
    - :meth:`has_forward_progress` – detect whether the sink is reachable from a
      given node.
    """

    model_config = ConfigDict(populate_by_name=True)

    entry_node_ids: list[UUID] = Field(default_factory=list, alias="entry_ids")
    exit_node_ids: list[UUID] = Field(default_factory=list, alias="exit_ids")
    _source_id: UUID | None = PrivateAttr(default=None)
    _sink_id: UUID | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _initialize_canonical_wiring(self) -> "TraversableDomain":
        if not self.entry_node_ids and self.member_ids:
            self.entry_node_ids = [self.member_ids[0]]
        if not self.exit_node_ids and self.member_ids:
            self.exit_node_ids = [self.member_ids[-1]]
        self._create_source_sink()
        return self

    @property
    def source(self) -> Node:
        """Return the synthetic entry node."""

        if self._source_id is None:
            raise RuntimeError(f"Domain {self.label!r} has no source node")
        source = self.graph.get(self._source_id)
        if source is None:
            raise RuntimeError(f"Domain {self.label!r} lost its source node")
        return source

    @property
    def sink(self) -> Node:
        """Return the synthetic exit node."""

        if self._sink_id is None:
            raise RuntimeError(f"Domain {self.label!r} has no sink node")
        sink = self.graph.get(self._sink_id)
        if sink is None:
            raise RuntimeError(f"Domain {self.label!r} lost its sink node")
        return sink

    def has_forward_progress(self, from_node: Node, *, ns: Mapping[str, Any] | None = None) -> bool:
        """Return ``True`` when the sink is reachable from ``from_node``.

        The traversal only considers destination nodes that remain within the
        domain's membership (plus the synthetic source/sink) and ignores
        :class:`ChoiceEdge` instances that are unavailable or marked as
        unsatisfied. This keeps reachability checks deterministic and scoped to
        the bounded section represented by the domain.
        """

        if from_node.graph is not self.graph:
            raise ValueError("Node does not belong to this domain's graph")

        allowed: set[UUID] = set(self.member_ids)
        if self._source_id is not None:
            allowed.add(self._source_id)
        if self._sink_id is not None:
            allowed.add(self._sink_id)

        if from_node.uid not in allowed:
            raise ValueError("Node is not a member of this traversable domain")

        visited: set[UUID] = set()
        queue = deque([from_node])

        while queue:
            current = queue.popleft()
            if current.uid in visited:
                continue
            visited.add(current.uid)

            if current.uid == self._sink_id:
                return True

            for edge in current.edges_out(is_instance=ChoiceEdge):
                destination = edge.destination
                if destination is None or destination.uid not in allowed:
                    continue
                if ns is not None and not edge.available(ns):
                    continue
                if not getattr(edge, "satisfied", True):
                    continue
                queue.append(destination)

        return False

    def _create_source_sink(self) -> None:
        if self.graph is None:
            return

        source_label = f"{self.label}__SOURCE"
        sink_label = f"{self.label}__SINK"

        source = self.graph.find_node(label=source_label)
        if source is None:
            source = self.graph.add_node(
                label=source_label,
                tags=["abstract", "source", "hidden"],
            )

        sink = self.graph.find_node(label=sink_label)
        if sink is None:
            sink = self.graph.add_node(
                label=sink_label,
                tags=["abstract", "sink", "hidden"],
            )

        self._source_id = source.uid
        self._sink_id = sink.uid

        if source.uid not in self.member_ids:
            self.add_member(source)
        if sink.uid not in self.member_ids:
            self.add_member(sink)

        for entry_id in self.entry_node_ids:
            entry = self.graph.get(entry_id)
            if entry is None:
                continue
            if self.graph.find_edge(
                source=source,
                destination=entry,
                is_instance=ChoiceEdge,
            ) is None:
                ChoiceEdge(
                    graph=self.graph,
                    source_id=source.uid,
                    destination_id=entry.uid,
                    label=f"enter_{self.label}",
                    trigger_phase=P.PREREQS,
                )

        for exit_id in self.exit_node_ids:
            exit_node = self.graph.get(exit_id)
            if exit_node is None:
                continue
            if self.graph.find_edge(
                source=exit_node,
                destination=sink,
                is_instance=ChoiceEdge,
            ) is None:
                ChoiceEdge(
                    graph=self.graph,
                    source_id=exit_node.uid,
                    destination_id=sink.uid,
                    label=f"exit_{self.label}",
                    trigger_phase=P.POSTREQS,
                )
