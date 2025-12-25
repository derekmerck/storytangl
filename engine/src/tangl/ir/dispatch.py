from functools import partial
from typing import Iterator

from tangl.core.behavior import LayeredDispatch, HandlerLayer as L, HandlerPriority as Prio, ContextP, CallReceipt
from tangl.ir.core_ir import BaseScriptItem

script_dispatch = LayeredDispatch(label="script.dispatch", handler_layer=L.APPLICATION)

on_materialize = partial(script_dispatch.register, task="materialize")

@on_materialize(priority=Prio.EARLY)
def _update_obj_cls(caller, *, ctx, **_):
    ...

@on_materialize(priority=Prio.EARLY)
def _update_data(caller, *, ctx, **_):
    ...

@on_materialize(priority=Prio.NORMAL)
def _structure_item(caller, *, ctx, **_):
    ...

@on_materialize(priority=Prio.LATE)
def _post_process_item(caller, *, data, ctx, **_):
    ...

# story application-level dispatch
def do_materialize(script_item: BaseScriptItem, *,
                   ctx: ContextP,
                   extra_handlers=None,
                   **kwargs) -> Iterator[CallReceipt]:
    # todo: create an execution context for this
    return script_dispatch.dispatch(
        script_item,
        ctx=ctx,
        task="materialize",
        extra_handlers=extra_handlers,
        **kwargs
    )
    # todo: could auto-aggregate to last..?
