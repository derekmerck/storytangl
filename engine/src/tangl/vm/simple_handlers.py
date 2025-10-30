# tangl/vm/simple_handlers.py
"""
Reference phase handlers for validation, redirects, and journaling.

These handlers provide a minimal end-to-end pipeline suitable for tests and
examples. Real applications can register additional handlers in their domains.
"""
# - the `register` decorator wraps the output in a CallReceipt
# - the phase runner appends the job receipt to the receipt stack in ctx
# - the full call sig currently is `h(cursor: Node, *, ns: NS, ctx: Context)`,
#   be sure to use the correct sig or ignore/consume unnecessary args/kwargs

import logging

from collections.abc import Iterable

from tangl.core import BaseFragment, Node, global_domain
from tangl.core.domain import NS
from tangl.vm.context import Context
from tangl.vm.frame import ResolutionPhase as P, ChoiceEdge

logger = logging.getLogger(__name__)

from functools import partial
from tangl.core.dispatch import HandlerPriority as Prio
from .vm_dispatch.vm_dispatch import vm_dispatch

# vm phase dispatch registration hooks
# We can use enums for tasks since we have them
on_validate = partial(vm_dispatch.register, task=P.VALIDATE)
on_prereq   = partial(vm_dispatch.register, task=P.PREREQS)
on_update   = partial(vm_dispatch.register, task=P.UPDATE)
on_journal  = partial(vm_dispatch.register, task=P.JOURNAL)
on_finalize = partial(vm_dispatch.register, task=P.FINALIZE)
on_postreq  = partial(vm_dispatch.register, task=P.POSTREQS)

# Lower layer tasks should never invoke the phase dispatch directly, instead
# add an application layer dispatch like "on_story_planning" that indicates
# task "planning", application layer dispatch will be passed in by the phase
# handler.
# ------- VALIDATION ---------

@on_validate(priority=Prio.EARLY)
# @global_domain.handlers.register(phase=P.VALIDATE, priority=0)
def validate_cursor(caller: Node, **kwargs):
    """Basic validation: cursor exists and is a :class:`~tangl.core.graph.Node`."""
    ok = caller is not None and isinstance(caller, Node)
    return ok

# ------- PLANNING ---------

# register planning handlers
from .planning import simple_planning_handlers

# @global_domain.handlers.register(phase=P.PLANNING, priority=50)
# def plan_provision(cursor: Node, **kwargs):
#     # satisfy open Dependency edges out of the cursor
#     g: Graph = cursor.graph
#     made = 0
#     for e in list(cursor.edges_out(is_instance=Dependency)):  # freeze the edge list
#         req = e.requirement
#         if not req.satisfied and not req.is_unresolvable:
#             # Search in graph (and optionally other registries)
#             prov = Provisioner(requirement=req, registries=[g])
#             if prov.resolve():
#                 made += 1
#     return made

# ------- PRE/POST REDIRECTS ---------

@on_prereq(priority=Prio.LATE)
# @global_domain.handlers.register(phase=P.PREREQS, priority=50)
def prereq_redirect(caller: Node, *, ctx: Context, **kwargs):
    """Follow auto-triggering :class:`~tangl.vm.frame.ChoiceEdge` redirects for PREREQS."""

    current_domain = ctx.get_traversable_domain_for_node(caller)
    ns = ctx.get_ns()

    if current_domain is not None:
        if caller.uid == current_domain.source.uid:
            for edge in caller.edges_out(is_instance=ChoiceEdge, trigger_phase=P.PREREQS):
                destination = edge.destination
                if destination is None:
                    continue
                if edge.available(ns):
                    logger.debug(
                        "Domain entry: %s source -> %s", current_domain.label, destination.label
                    )
                    return edge

        if caller.uid == current_domain.sink.uid:
            for edge in caller.edges_out(is_instance=ChoiceEdge, trigger_phase=P.PREREQS):
                destination = edge.destination
                if destination is None:
                    continue
                if destination.uid in current_domain.member_ids:
                    continue
                if edge.available(ns):
                    logger.debug(
                        "Domain exit: %s sink -> %s", current_domain.label, destination.label
                    )
                    return edge

    for edge in caller.edges_out(is_instance=ChoiceEdge, trigger_phase=P.PREREQS):
        if edge.available(ns):
            return edge

@on_postreq(priority=Prio.LATE)
# @global_domain.handlers.register(phase=P.POSTREQS, priority=50)
def postreq_redirect(cursor: Node, *, ctx: Context, **kwargs):
    """Follow the first auto-triggering :class:`~tangl.vm.frame.ChoiceEdge` in POSTREQS."""
    ns = ctx.get_ns()
    for e in cursor.edges_out(is_instance=ChoiceEdge, trigger_phase=P.POSTREQS):
        if e.available(ns):
            return e

# ------- UPDATE/FINALIZE ---------

@on_update()
# @global_domain.handlers.register(phase=P.UPDATE, priority=50)
def update_noop(*args, **kwargs):
    pass

@on_finalize()
# @global_domain.handlers.register(phase=P.FINALIZE, priority=50)
def finalize_noop(*args, **kwargs):
    # collapse-to-patch can go here later
    pass

# ------- JOURNAL ---------

@on_journal()
# todo: we can move this to journal/io when that gets implemented
# @global_domain.handlers.register(phase=P.JOURNAL, priority=50)
def journal_line(cursor: Node, *, ctx: Context, **kwargs):
    """Emit a simple textual line describing the current step/cursor (reference output)."""
    step = ctx.step
    line = f"[step {step:04d}]: cursor at {cursor.get_label()}"
    logger.debug(f"JOURNAL: Outputting journal line: {line}")
    return line

@on_journal(priority=Prio.LAST)
# @global_domain.handlers.register(phase=P.JOURNAL, priority=100)
def coerce_to_fragments(*_, ctx: Context, **__):
    """Coerce mixed handler outputs into a list of :class:`~tangl.core.fragment.BaseFragment`.  Runs LAST."""
    fragments: list[BaseFragment] = []

    def _extend(value: object) -> None:
        if value is None:
            return
        if isinstance(value, BaseFragment):
            fragments.append(value)
            return
        if isinstance(value, str):
            fragments.append(BaseFragment(content=value))
            return
        if isinstance(value, Iterable):
            logger.debug(f"recursing on {value}")
            for item in value:
                _extend(item)
            return
        fragments.append(BaseFragment(content=str(value)))

    for receipt in ctx.call_receipts:
        _extend(receipt.result)
    logger.debug(f"JOURNAL: Outputting fragments: {fragments}")
    return fragments
