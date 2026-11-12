"""Prototype of Derek's resume rule, outside the engine.

On return, re-enter the caller at the phase the call fired in, walk its edges
in order, discard everything up to and including the call edge that was taken,
and evaluate from the next one.

Done here with an edge subclass so no engine file changes: the return edge
remembers which call it came from, and an edge at or before that call reports
itself unavailable for that one evaluation.
"""
from tangl.core import Graph
from tangl.vm import Ledger, ResolutionPhase as P, on_journal, on_update
from tangl.vm.traversable import TraversableEdge, TraversableNode

log = []
@on_journal
def j(*, caller, ctx, **kw): log.append("journal:" + caller.label)
@on_update
def u(*, caller, ctx, **kw): log.append("update:" + caller.label)

class E(TraversableEdge):
    def get_return_edge(self):
        ret = super().get_return_edge()
        ret.resume_after = self.uid
        return ret

    def available(self, *, ctx=None, ns=None):
        taken = getattr(getattr(ctx, "incoming_edge", None), "resume_after", None)
        if taken is not None and self.predecessor is not None:
            order = [e.uid for e in self.predecessor.edges_out() if isinstance(e, TraversableEdge)]
            if taken in order and order.index(self.uid) <= order.index(taken):
                return False
        return super().available(ctx=ctx, ns=ns)

def run(title, nodes, edges, first):
    g = Graph()
    n = {k: TraversableNode(label=k, registry=g) for k in nodes}
    made = [E(registry=g, predecessor_id=n[a].uid, successor_id=n[b].uid, **kw) for a, b, kw in edges]
    ledger = Ledger.from_graph(g, entry_id=n[nodes[0]].uid)
    log.clear()
    try:
        ledger.resolve_choice(made[first].uid)
        end = f"cursor={ledger.cursor.label} stack={len(ledger.call_stack_ids)}"
    except RecursionError:
        end = "RecursionError"
    print(f"{title}\n   {' '.join(log)}\n   {end}")

call_last = dict(trigger_phase=P.POSTREQS, return_phase=P.POSTREQS)
call_first = dict(trigger_phase=P.PREREQS, return_phase=P.PREREQS)
run("1. shared outro, then the scene's own exit",
    ["start", "exit_block", "theater_cleanup", "next_scene"],
    [("start", "exit_block", {}), ("exit_block", "theater_cleanup", call_last),
     ("exit_block", "next_scene", dict(trigger_phase=P.POSTREQS))], 0)
run("2. two shared outros in a row, then exit",
    ["start", "exit_block", "cleanup_a", "cleanup_b", "next_scene"],
    [("start", "exit_block", {}), ("exit_block", "cleanup_a", call_last), ("exit_block", "cleanup_b", call_last),
     ("exit_block", "next_scene", dict(trigger_phase=P.POSTREQS))], 0)
run("3. two shared intros before content",
    ["start", "block", "intro_a", "intro_b"],
    [("start", "block", {}), ("block", "intro_a", call_first), ("block", "intro_b", call_first)], 0)

from tangl.vm import on_provision
@on_provision
def pl(*, caller, ctx, **kw): log.append("plan:" + caller.label)

replan_first = dict(trigger_phase=P.PREREQS, return_phase=P.PLANNING)
run("4. hub with two due arrivals; return re-plans the hub but keeps its place",
    ["start", "hub", "arrival_a", "arrival_b"],
    [("start", "hub", {}), ("hub", "arrival_a", replan_first), ("hub", "arrival_b", replan_first)], 0)
replan_last = dict(trigger_phase=P.POSTREQS, return_phase=P.PLANNING)
run("5. outro that returns at PLANNING with the marker (refresh plus place)",
    ["start", "exit_block", "theater_cleanup", "next_scene"],
    [("start", "exit_block", {}), ("exit_block", "theater_cleanup", replan_last),
     ("exit_block", "next_scene", dict(trigger_phase=P.POSTREQS))], 0)
