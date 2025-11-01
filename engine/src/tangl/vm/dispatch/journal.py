from __future__ import annotations
from typing import TYPE_CHECKING, Iterable
from functools import partial
import logging

from tangl.core import Node, BaseFragment
from tangl.core.behavior import HandlerPriority as Prio
from tangl.vm.resolution_phase import ResolutionPhase as P
from .vm_dispatch import vm_dispatch

if TYPE_CHECKING:
    from tangl.vm.context import Context

logger = logging.getLogger(__name__)

on_journal  = partial(vm_dispatch.register, task=P.JOURNAL)


@on_journal()
# todo: we can move this to journal/io when that gets implemented
def journal_line(cursor: Node, *, ctx: Context, **kwargs):
    """Emit a simple textual line describing the current step/cursor (reference output)."""
    step = ctx.step
    line = f"[step {step:04d}]: cursor at {cursor.get_label()}"
    logger.debug(f"JOURNAL: Outputting journal line: {line}")
    return line

@on_journal(priority=Prio.LAST)
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
