import logging
from typing import TypeAlias, Any
from functools import partial
from collections import ChainMap

from tangl.core import Entity, Node
from tangl.core.behavior import HandlerPriority as Prio, CallReceipt, ContextP
from tangl.core.dispatch.scoped_dispatch import scoped_dispatch
from .vm_dispatch import vm_dispatch

Namespace: TypeAlias = ChainMap[str, Any]
NS = Namespace

# system level task, specific to vm and applications that vm might use
on_get_ns = partial(vm_dispatch.register, task="get_ns")

logger = logging.getLogger(__name__)

# No need for a HasNs mixin, assume anything with 'locals' wants to contribute.
@on_get_ns(priority=Prio.LATE)
def _contribute_locals_to_ns(caller: Entity, *_, **__):
    if hasattr(caller, "locals"):
        return caller.locals

@on_get_ns()
def _contribute_deps_to_ns(caller: Node, *_, **__):
    from tangl.vm.provision import Dependency, Affordance
    reqs = caller.edges_out(is_instance=(Dependency, Affordance), satisfied=True)
    return { r.get_label(): r.destination for r in reqs }

def do_get_ns(anchor: Node, *, ctx: ContextP, extra_handlers=None, **kwargs) -> ChainMap[str, Any]:
    """
    Walks local layers (ancestors) and gathers relevant object names.

    Non-specific application and author level owner handlers may want to
    register with is_instance=Graph rather than is_instance=Node, so they
    are only included once at the top.


    Warning
    -------
    Handlers must not call ctx.get_ns() for the same node, as this will
    cause infinite recursion. If you need access to other namespace vars,
    use a two-phase approach with EARLY and LATE priorities.
    """
    receipts = scoped_dispatch(
        # behavior ctx
        caller=anchor,
        ctx=ctx,  # Need context to get APP, AUTHOR layers
        with_kwargs=kwargs,

        # dispatch meta
        task="get_ns",
        extra_handlers=extra_handlers
    )
    receipts = list(receipts)
    logger.debug([r.result for r in receipts])
    return CallReceipt.merge_results(*receipts)

