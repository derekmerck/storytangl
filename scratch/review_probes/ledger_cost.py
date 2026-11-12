"""Measure what one choice costs the ledger: time, stream growth, and id stability."""
import json, sys, time
from collections import Counter
from pathlib import Path

from tangl.core import Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.story import Action, InitMode
from tangl.vm import Ledger

root = Path(sys.argv[1])
world = WorldCompiler().compile(WorldBundle.load(root))


def size(obj) -> int:
    return len(json.dumps(obj, default=str))


def play(n: int):
    result = world.create_story(root.name + "_demo", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    rows, picked = [], []
    for _ in range(n):
        actions = sorted(
            ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)),
            key=lambda a: a.label or "",
        )
        actions = [a for a in actions if a.successor is not None] or actions
        if not actions:
            break
        action = actions[0]
        picked.append((action.label, action.uid, sorted(str(a.uid) for a in actions)))
        t = time.perf_counter()
        ledger.resolve_choice(action.uid)
        dt = time.perf_counter() - t
        kinds = Counter(type(r).__name__ for r in ledger.output_stream.values())
        rows.append((dt, len(ledger.graph.members), size(ledger.graph.unstructure()),
                     size(ledger.output_stream.unstructure()), dict(kinds)))
    return ledger, rows, picked


ledger, rows, picked = play(int(sys.argv[2]))
print("world", root.name, "choices", len(rows))
for i, (dt, members, gsize, ssize, kinds) in enumerate(rows):
    print(f"{i:2d} {dt*1000:7.1f} ms  members={members:4d} graph={gsize//1024:5d}K stream={ssize//1024:6d}K")
print("stream kinds:", rows[-1][4])
ck = sum(size(r.unstructure()) for r in ledger.output_stream.values() if type(r).__name__ == "CheckpointRecord")
print("checkpoint share of stream: %.0f%%" % (100 * ck / max(rows[-1][3], 1)))

_, _, picked2 = play(len(rows))
same_chosen = sum(a[1] == b[1] for a, b in zip(picked, picked2))
same_menu = sum(a[2] == b[2] for a, b in zip(picked, picked2))
print(f"second run, same labels picked: {[a[0] for a in picked] == [b[0] for b in picked2]}")
print(f"chosen edge ids identical: {same_chosen}/{len(picked)}; offered id sets identical: {same_menu}/{len(picked)}")
