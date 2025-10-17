# tangl/vm/simple_handlers.py
"""
Reference phase handlers for validation, redirects, and journaling.

These handlers provide a minimal end-to-end pipeline suitable for tests and
examples. Real applications can register additional handlers in their domains.
"""
# - the `register` decorator wraps the output in a JobReceipt
# - the phase runner appends the job receipt to the receipt stack in ctx
# - the full call sig currently is `h(cursor: Node, *, ctx: Context)`;
#   handlers that need a namespace can call ``ctx.get_ns()`` directly

import logging

from collections.abc import Iterable
from typing import Any

from tangl.core import BaseFragment, Node, global_domain
from tangl.vm.context import Context
from tangl.vm.frame import ResolutionPhase as P, ChoiceEdge

logger = logging.getLogger(__name__)

# ------- VALIDATION ---------

@global_domain.handlers.register(phase=P.VALIDATE, priority=0)
def validate_cursor(cursor: Node, **kwargs):
    """Basic validation: cursor exists and is a :class:`~tangl.core.graph.Node`."""
    ok = cursor is not None and isinstance(cursor, Node)
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

@global_domain.handlers.register(phase=P.PREREQS, priority=50)
def prereq_redirect(cursor: Node, *, ctx: Context, **kwargs):
    """Follow auto-triggering :class:`~tangl.vm.frame.ChoiceEdge` redirects for PREREQS."""

    ns = ctx.get_ns()

    current_domain = ctx.get_traversable_domain_for_node(cursor)

    if current_domain is not None:
        if cursor.uid == current_domain.source.uid:
            for edge in cursor.edges_out(is_instance=ChoiceEdge, trigger_phase=P.PREREQS):
                destination = edge.destination
                if destination is None:
                    continue
                if edge.available(ns):
                    logger.debug(
                        "Domain entry: %s source -> %s", current_domain.label, destination.label
                    )
                    return edge

        if cursor.uid == current_domain.sink.uid:
            for edge in cursor.edges_out(is_instance=ChoiceEdge, trigger_phase=P.PREREQS):
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

    for edge in cursor.edges_out(is_instance=ChoiceEdge, trigger_phase=P.PREREQS):
        if edge.available(ns):
            return edge

@global_domain.handlers.register(phase=P.POSTREQS, priority=50)
def postreq_redirect(cursor: Node, *, ctx: Context, **kwargs):
    """Follow the first auto-triggering :class:`~tangl.vm.frame.ChoiceEdge` in POSTREQS."""
    ns = ctx.get_ns()

    for e in cursor.edges_out(is_instance=ChoiceEdge, trigger_phase=P.POSTREQS):
        if e.available(ns):
            return e

# ------- UPDATE/FINALIZE ---------

@global_domain.handlers.register(phase=P.UPDATE, priority=50)
def update_noop(*args, **kwargs):
    pass

@global_domain.handlers.register(phase=P.FINALIZE, priority=50)
def finalize_noop(*args, **kwargs):
    # collapse-to-patch can go here later
    pass

# ------- JOURNAL ---------

# todo: we can move this to journal/io when that gets implemented
@global_domain.handlers.register(phase=P.JOURNAL, priority=50)
def journal_line(cursor: Node, *, ctx: Context, **kwargs):
    """Emit a simple textual line describing the current step/cursor (reference output)."""
    step = ctx.step
    line = f"[step {step:04d}]: cursor at {cursor.get_label()}"
    logger.debug(f"JOURNAL: Outputting journal line: {line}")
    return line

@global_domain.handlers.register(phase=P.JOURNAL, priority=100)
def coerce_to_fragments(*args, ctx: Context, **kwargs):
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
            for item in value:
                _extend(item)
            return
        fragments.append(BaseFragment(content=str(value)))

    for receipt in ctx.job_receipts:
        _extend(receipt.result)
    logger.debug(f"JOURNAL: Outputting fragments: {fragments}")
    return fragments
