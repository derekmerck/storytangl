
from tangl.core import Node
from tangl.core.dispatch import CallReceipt, HandlerPriority as Prio
# we want a better contextP here, that includes get_ns()
from tangl.core.dispatch.core_dispatch import ContextP
from tangl.vm.vm_dispatch.vm_dispatch import vm_dispatch, on_planning


@on_planning(priority=Prio.EARLY)
def _get_offers(c, *, ctx) -> 'Offers':
    # stash offers per dep in context
    ...

@on_planning(priority=Prio.LATE)
def _accept_offers(c, *, ctx) -> CallReceipt:
    # review offers and accept for each dep
    ...

# vm system-level dispatch
def do_planning(cursor: Node, *, ctx: ContextP, extra_handlers=None, **kwargs) -> Iterator[CallReceipt]:
    return vm_dispatch.dispatch(
        cursor,
        ctx=ctx,
        task=P.PLANNING,
        extra_handlers=extra_handlers,
        **kwargs
    )
