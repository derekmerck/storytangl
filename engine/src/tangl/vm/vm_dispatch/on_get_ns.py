import logging
from typing import Iterable, TypeAlias, Any
from functools import partial
from collections import ChainMap

from tangl.core import Entity, Node, BehaviorRegistry
from tangl.core.dispatch import HandlerLayer as L, HandlerPriority as Prio, CallReceipt, ContextP, LayeredDispatch
from tangl.vm.vm_dispatch.vm_dispatch import vm_dispatch

NS: TypeAlias = ChainMap[str, Any]

# system level task, specific to vm and applications that vm might use
on_get_ns = partial(vm_dispatch.register, task="get_ns")

logger = logging.getLogger(__name__)

# No need for a HasNs mixin, assume anything with 'locals' wants to contribute.
@on_get_ns(priority=Prio.LATE)
def _contribute_locals_to_ns(caller: Entity, *_, **__):
    if hasattr(caller, "locals"):
        return caller.locals

def do_get_ns(anchor: Node, *, ctx: ContextP, extra_handlers=None, **kwargs) -> ChainMap[str, Any]:
    # Walks local layers (ancestors) and gathers relevant object names

    # Non-specific application and author level owner handlers may want to
    # register with is_instance=Graph rather than is_instance=Node, so they
    # are only included once at the top.

    receipts = []
    for node in (anchor, *anchor.ancestors(), anchor.graph):
        receipts.extend(
            vm_dispatch.dispatch(
                # behavior ctx
                caller=node,
                ctx=ctx,  # Need context to get SYS, AUTHOR layers
                with_kwargs=kwargs,

                # dispatch meta
                task="get_ns",
                extra_handlers=extra_handlers,
            )
        )
    return CallReceipt.merge_results(*receipts)
