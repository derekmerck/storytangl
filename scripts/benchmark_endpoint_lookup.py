"""Compare endpoint lookup at a matched scale across two checkouts.

Run each checkout in a separate process using the same installed dependencies::

    poetry run python scripts/benchmark_endpoint_lookup.py CHECKOUT 3000

Results are five-run medians; timings are observations, not CI assertions.
"""

from __future__ import annotations

import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

sys.path.insert(0, str(Path(sys.argv[1]).resolve() / "engine/src"))

from tangl.core.ctx import Ctx
from tangl.core.graph import Edge, Graph, Node


def measure(size: int) -> dict[str, int | float]:
    results = []
    for _ in range(5):
        start = perf_counter()
        graph = Graph()
        hub = Node(registry=graph)
        target = Node(registry=graph)
        ctx = Ctx()
        for index in range(size + 8):
            source = hub if index < 8 else Node(registry=graph)
            graph.add(Edge(predecessor_id=source.uid, successor_id=target.uid), _ctx=ctx)
        built = perf_counter()
        for _ in range(200):
            assert len(list(hub.edges_out())) == 8
        queried = perf_counter()
        edges = list(hub.edges_out())
        maintenance_start = perf_counter()
        for edge in edges:
            edge.set_successor(hub)
            edge.set_successor(target)
        maintained = perf_counter()
        results.append((built - start, queried - built, maintained - maintenance_start))
    return {
        "unrelated_edges": size,
        "members": len(graph),
        "queries": 200,
        "build_median_s": statistics.median(row[0] for row in results),
        "queries_median_s": statistics.median(row[1] for row in results),
        "rewire_median_s": statistics.median(row[2] for row in results),
    }


if __name__ == "__main__":
    print(json.dumps(measure(int(sys.argv[2]))))
