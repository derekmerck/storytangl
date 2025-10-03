# minimal phase handlers for testing

# - the `register` decorator wraps the output in a JobReceipt
# - the phase runner appends the job receipt to the receipt stack in ctx
# - the full call sig currently is `h(cursor: Node, *, ns: NS, ctx: Context)`,
#   be sure to use the correct sig or ignore/consume unnecessary args/kwargs

import logging

from tangl.core import Node, global_domain, Graph, BaseFragment
from tangl.vm.context import Context
from tangl.vm.frame import ResolutionPhase as P, NS, ChoiceEdge, ResolutionPhase
from tangl.vm.planning import Dependency, Provisioner

logger = logging.getLogger(__name__)

@global_domain.handlers.register(phase=P.VALIDATE, priority=0)
def validate_cursor(cursor: Node, **kwargs):
    # cursor exists and is a Node; extend with additional preconditions as needed
    ok = cursor is not None and isinstance(cursor, Node)
    return ok

@global_domain.handlers.register(phase=P.PLANNING, priority=50)
def plan_provision(cursor: Node, **kwargs):
    # satisfy open Dependency edges out of the cursor
    g: Graph = cursor.graph
    made = 0
    for e in list(cursor.edges_out(is_instance=Dependency)):  # freeze the edge list
        req = e.requirement
        if not req.satisfied and not req.is_unresolvable:
            # Search in graph (and optionally other registries)
            prov = Provisioner(requirement=req, registries=[g])
            if prov.resolve():
                made += 1
    return made

@global_domain.handlers.register(phase=P.PREREQS, priority=50)
def prereq_redirect(cursor: Node, *, ns: NS, **kwargs):
    # follow the first auto-triggering ChoiceEdge if any
    for e in cursor.edges_out(is_instance=ChoiceEdge, trigger_phase=P.PREREQS):
        if e.available(ns):
            return e

@global_domain.handlers.register(phase=P.UPDATE, priority=50)
def update_noop(*args, **kwargs):
    pass

@global_domain.handlers.register(phase=P.JOURNAL, priority=50)
def journal_line(cursor: Node, *, ctx: Context, **kwargs):
    step = ctx.step
    line = f"[step {step:04d}]: cursor at {cursor.get_label()}"
    logger.debug(f"JOURNAL: Outputting journal line: {line}")
    return line

@global_domain.handlers.register(phase=P.JOURNAL, priority=100)
def coerce_to_fragments(*args, ctx: Context, **kwargs):
    # Simple compositor, runs _LAST_ to coerce to proper format
    fragments = []
    for receipt in ctx.job_receipts:
        result = receipt.result
        if isinstance(result, BaseFragment):
            fragments.append(result)
        else:
            f = BaseFragment(content=result)
            fragments.append(f)
    logger.debug(f"JOURNAL: Outputting fragments: {fragments}")
    return fragments

@global_domain.handlers.register(phase=P.FINALIZE, priority=50)
def finalize_noop(*args, **kwargs):
    # collapse-to-patch can go here later
    pass

@global_domain.handlers.register(phase=P.POSTREQS, priority=50)
def postreq_redirect(cursor: Node, *, ns: NS, **kwargs):
    for e in cursor.edges_out(is_instance=ChoiceEdge, trigger_phase=P.POSTREQS):
        if e.available(ns):
            return e
