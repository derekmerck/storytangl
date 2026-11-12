"""Two small experiments on calls, at the VM level only.

A. A call whose callee jumps away: is the call frame left on the stack, and
   where does it pop?
B. A no-choice interjection called at POSTREQS: how often does the sender
   render?
"""
from collections import Counter
from tangl.core import Graph, Record
from tangl.vm import Ledger, ResolutionPhase as P, on_journal
from tangl.vm.traversable import TraversableEdge, TraversableNode

rendered = []

@on_journal
def note(*, caller, ctx, **kw):
    rendered.append(caller.label)
    return None

def node(g, label):
    return TraversableNode(label=label, registry=g)

def edge(g, a, b, **kw):
    return TraversableEdge(registry=g, predecessor_id=a.uid, successor_id=b.uid, **kw)

print("A. callee jumps away")
g = Graph()
hub, shop, alley, street, dead_end = (node(g, n) for n in ("hub", "shop", "alley", "street", "dead_end"))
call = edge(g, hub, shop, return_phase=P.PLANNING)        # hub calls shop, expects it back
leave = edge(g, shop, alley)                               # an ordinary choice out of the callee
onward = edge(g, alley, street)
last = edge(g, street, dead_end)
ledger = Ledger.from_graph(g, entry_id=hub.uid)
for e in (call, leave, onward, last):
    rendered.clear()
    ledger.resolve_choice(e.uid)
    print(f"  chose {e.predecessor.label}->{e.successor.label}: cursor={ledger.cursor.label:9s} "
          f"stack={[g.get(i).predecessor.label + '->' + g.get(i).successor.label for i in ledger.call_stack_ids]} rendered={rendered}")

print("B. interjection after content, before choices")
g = Graph()
start, scene, aria, a, b = (node(g, n) for n in ("start", "scene", "aria_says", "option_a", "option_b"))
go = edge(g, start, scene)
edge(g, scene, aria, trigger_phase=P.POSTREQS, return_phase=P.PLANNING, once=True)
edge(g, scene, a); edge(g, scene, b)
ledger = Ledger.from_graph(g, entry_id=start.uid)
rendered.clear()
ledger.resolve_choice(go.uid)
print(f"  cursor={ledger.cursor.label} stack={len(ledger.call_stack_ids)} rendered={rendered} counts={dict(Counter(rendered))}")
print(f"  scene _visit_count={scene.locals.get('_visit_count')}  history={[g.get(i).label for i in ledger.cursor_history]}")
