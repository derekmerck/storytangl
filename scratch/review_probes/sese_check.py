"""Do the demo worlds obey the stated container contract?

VM_DESIGN: "Edges into the container target the container itself; edges out
of the container originate from the sink."  For every container, count
traversable edges that leave it from a member other than its sink, and edges
that enter it at a member other than through the container.
"""
import sys, logging
from pathlib import Path
logging.disable(logging.CRITICAL)
from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import InitMode
from tangl.vm.traversable import TraversableEdge, TraversableNode

tot = dict(containers=0, exits=0, exits_not_sink=0, entries=0, entries_not_container=0)
for root in sorted(p for p in Path("worlds").iterdir() if (p / "world.yaml").exists()):
    try:
        world = WorldCompiler().compile(WorldBundle.load(root))
        g = world.create_story(root.name + "_demo", init_mode=InitMode.EAGER).graph
    except Exception as exc:
        print(f"{root.name:26s} skipped ({type(exc).__name__})"); continue
    nodes = [n for n in g.values() if isinstance(n, TraversableNode)]
    edges = [e for e in g.values() if isinstance(e, TraversableEdge) and e.predecessor is not None and e.successor is not None]
    row = dict(containers=0, exits=0, exits_not_sink=0, entries=0, entries_not_container=0)
    for c in (n for n in nodes if n.is_container):
        row["containers"] += 1
        anc = lambda m: {a.uid for a in (m.ancestors() if callable(m.ancestors) else m.ancestors)}
        inside = {m.uid for m in nodes if m is not c and c.uid in anc(m)}
        for e in edges:
            a, b = e.predecessor.uid in inside, e.successor.uid in inside
            if a and not b and e.successor is not c:
                row["exits"] += 1
                if e.predecessor.uid != c.sink_id: row["exits_not_sink"] += 1
            if b and not a and e.predecessor is not c:
                row["entries"] += 1; row["entries_not_container"] += 1
            if e.successor is c and not a:
                row["entries"] += 1
    for k in tot: tot[k] += row[k]
    print(f"{root.name:26s} containers={row['containers']:2d} exits={row['exits']:3d} (not from sink {row['exits_not_sink']:3d})  entries={row['entries']:3d} (bypassing the container {row['entries_not_container']:3d})")
print("TOTAL", tot)
