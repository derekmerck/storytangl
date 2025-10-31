from __future__ import annotations
from functools import partial
from typing import Iterator

from tangl.core import Node
from tangl.core.behavior import HandlerPriority as Prio, CallReceipt
from tangl.vm import ResolutionPhase as P
from tangl.vm.dispatch import vm_dispatch

on_planning = partial(vm_dispatch.register, task=P.PLANNING)

@on_planning(priority=Prio.EARLY)
def _get_offers(c, *, ctx):
    # stash offers per dep in context.results or context.offers, like journal
    ctx.results = [1, 2, 3]
    return None

@on_planning(priority=Prio.LATE)
def _accept_offers(c, *, ctx) -> CallReceipt:
    # review offers and accept for each dep/affordance
    offers = ctx.results
    return offers.accept()

# vm system-level dispatch
def do_planning(caller: Node, *args, ctx, extra_handlers=None, **kwargs) -> Iterator[CallReceipt]:
    return vm_dispatch.dispatch(
        caller=caller,
        ctx=ctx,
        with_args=args,
        with_kwargs=kwargs,
        task=P.PLANNING,
        extra_handlers=extra_handlers,
    )
