from typing import Iterator

from tangl.type_hints import StringMap
from tangl.core import Node, Entity, CallReceipt
from tangl.core.behavior import ContextP
from .core_dispatch import core_dispatch

# todo: possibly layered dispatch should be moved here and this should
#       be integrated with it directly, it does depend on GraphItem to
#       interpret the local layers, but LayeredDispatch also depends on
#       core_dispatch for the default, so maybe it doesn't belong in 'pure'
#       `core.behavior`
def scoped_dispatch(  # Behavior params
                    caller: Node, *,  # Active entity
                    ctx: ContextP,    # Includes get_job_layers
                    with_args: tuple[Entity, ...] = None,  # Other participants
                    with_kwargs: StringMap = None,

                    # Dispatch meta
                    task=None,  # alias for `inline_criteria[has_task]`
                    inline_criteria: StringMap = None,
                    extra_handlers=None,
                    dry_run=False) -> Iterator[CallReceipt]:
    """
    Walks structural layers (ancestors) and uses each as caller for dispatch.

    Non-specific application and author level owner handlers may want to
    register with is_instance=Graph rather than is_instance=Node, so they
    are only included once at the top.
    """
    for inst in (caller, *caller.ancestors(), caller.graph):
        yield from core_dispatch.dispatch(
                    # behavior ctx
                    caller=inst,
                    ctx=ctx,  # Need context to get APP, AUTHOR layers
                    with_args=with_args,
                    with_kwargs=with_kwargs,

                    # dispatch meta
                    task=task,
                    extra_handlers=extra_handlers,
                    inline_criteria=inline_criteria,
                    dry_run=dry_run
            )

