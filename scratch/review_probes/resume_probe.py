"""Can a triggered call resume its caller today by returning at the phase it fired in?"""
from tangl.core import Graph
from tangl.vm import Ledger, ResolutionPhase as P, on_journal, on_update
from tangl.vm.traversable import TraversableEdge, TraversableNode

log = []
@on_journal
def j(*, caller, ctx, **kw): log.append("journal:" + caller.label)
@on_update
def u(*, caller, ctx, **kw): log.append("update:" + caller.label)

def build(return_phase):
    g = Graph()
    n = {k: TraversableNode(label=k, registry=g) for k in ("start", "exit_block", "theater_cleanup", "next_scene")}
    def e(a, b, **kw): return TraversableEdge(registry=g, predecessor_id=n[a].uid, successor_id=n[b].uid, **kw)
    go = e("start", "exit_block")
    e("exit_block", "theater_cleanup", trigger_phase=P.POSTREQS, return_phase=return_phase)   # silent jump and return
    e("exit_block", "next_scene", trigger_phase=P.POSTREQS)                                   # the scene's own way out
    return g, n, go

for rp in (P.PLANNING, P.POSTREQS):
    g, n, go = build(rp)
    ledger = Ledger.from_graph(g, entry_id=n["start"].uid)
    log.clear()
    try:
        ledger.resolve_choice(go.uid)
        print(f"return at {rp.name:9s}: cursor={ledger.cursor.label}")
    except RecursionError as exc:
        print(f"return at {rp.name:9s}: RecursionError ({str(exc)[:60]}...)")
    print("   ", " ".join(log[:14]), "..." if len(log) > 14 else "")
