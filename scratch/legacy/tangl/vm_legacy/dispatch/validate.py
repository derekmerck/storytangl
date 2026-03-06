from __future__ import annotations
from functools import partial

from tangl.core import Node
from tangl.core.behavior import HandlerPriority as Prio
from tangl.vm.resolution_phase import ResolutionPhase as P
from .vm_dispatch import vm_dispatch

on_validate = partial(vm_dispatch.register, task=P.VALIDATE)

@on_validate(priority=Prio.EARLY)
def validate_cursor(caller: Node, **kwargs):
    """Basic validation: cursor exists and is a :class:`~tangl.core.graph.Node`."""
    ok = caller is not None and isinstance(caller, Node)
    return ok
