from __future__ import annotations
from typing import TYPE_CHECKING
from functools import partial

from tangl.core import Node
from tangl.core.behavior import HandlerPriority as Prio
from tangl.vm.resolution_phase import ResolutionPhase as P
from tangl.vm.frame import ChoiceEdge
from .vm_dispatch import vm_dispatch

on_prereq   = partial(vm_dispatch.register, task=P.PREREQS)
on_postreq  = partial(vm_dispatch.register, task=P.POSTREQS)

if TYPE_CHECKING:
    from tangl.vm.context import Context

@on_prereq(priority=Prio.LATE)
def prereq_redirect(cursor: Node, *, ctx: Context, **kwargs):
    """Follow auto-triggering :class:`~tangl.vm.frame.ChoiceEdge` redirects for PREREQS."""
    ns = ctx.get_ns()
    for e in cursor.edges_out(is_instance=ChoiceEdge, trigger_phase=P.PREREQS):
        if e.available(ns):
            return e

    return
    # todo: implement descend and ascend in regular follow logic

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
def postreq_redirect(cursor: Node, *, ctx: Context, **kwargs):
    """Follow the first auto-triggering :class:`~tangl.vm.frame.ChoiceEdge` in POSTREQS."""
    ns = ctx.get_ns()
    for e in cursor.edges_out(is_instance=ChoiceEdge, trigger_phase=P.POSTREQS):
        if e.available(ns):
            return e
