# minimal phase handlers for testing
# note, the `register` decorator wraps the output in a JobReceipt

from tangl.core import Node, global_domain, Graph
from tangl.vm.frame import ResolutionPhase as P, NS, ChoiceEdge
from tangl.vm.planning import Dependency, Provisioner

@global_domain.handlers.register(phase=P.VALIDATE, priority=0)
def validate_cursor(ns: NS):
    # cursor exists and is a Node; extend with additional preconditions as needed
    ok = ns["cursor"] is not None and isinstance(ns["cursor"], Node)
    return ok

@global_domain.handlers.register(phase=P.PLANNING, priority=50)
def plan_provision(ns: NS):
    # satisfy open Dependency edges out of the cursor
    g: Graph = ns["cursor"].graph
    made = 0
    for e in list(ns["cursor"].edges_out(is_instance=Dependency)):  # freeze the edge list
        req = e.requirement
        if not req.satisfied and not req.is_unresolvable:
            # Search in graph (and optionally other registries)
            prov = Provisioner(requirement=req, registries=[g])
            if prov.resolve():
                made += 1
    return made

@global_domain.handlers.register(phase=P.PREREQS, priority=50)
def prereq_redirect(ns: NS):
    # follow the first auto-triggering ChoiceEdge if any
    cur: Node = ns["cursor"]
    for e in cur.edges_out(is_instance=ChoiceEdge, trigger_phase=P.PREREQS):
        if e.available(ns):
            return e

@global_domain.handlers.register(phase=P.UPDATE, priority=50)
def update_noop(ns: NS):
    pass

@global_domain.handlers.register(phase=P.JOURNAL, priority=50)
def journal_line(ns: NS):
    cur: Node = ns["cursor"]
    line = f"[step {ns['step']:03d}] {cur.label or cur.short_uid()}"
    return line

@global_domain.handlers.register(phase=P.FINALIZE, priority=50)
def finalize_noop(ns: NS):
    # collapse-to-patch can go here later
    pass

@global_domain.handlers.register(phase=P.POSTREQS, priority=50)
def postreq_redirect(ns: NS):
    cur: Node = ns["cursor"]
    for e in cur.edges_out(is_instance=ChoiceEdge, trigger_phase=P.POSTREQS):
        if e.available(ns):
            return e
