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
logger.setLevel(logging.DEBUG)

on_journal  = partial(vm_dispatch.register, task=P.JOURNAL)


@on_journal(priority=Prio.EARLY)
# todo: we can move this to journal/io when that gets implemented
def journal_line(cursor: Node, *, ctx: Context, **kwargs):
    """Emit a marker fragment for the current step."""

    if cursor.has_tags("domain:local_domain"):
        return None

    step = ctx.step
    line = f"[step {step:04d}]: cursor at {cursor.get_label()}"
    logger.debug(f"JOURNAL: Outputting journal line: {line}")
    return BaseFragment(content=line, fragment_type="marker")

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
            logger.debug(f"Adding str fragment: {value}")
            fragments.append(BaseFragment(content=value, fragment_type="text"))
            return
        if isinstance(value, Iterable):
            logger.debug(f"recursing on {value}")
            for item in value:
                _extend(item)
            return
        fragments.append(BaseFragment(content=str(value), fragment_type="text"))

    receipt_count = len(ctx.call_receipts)

    for receipt in ctx.call_receipts:
        _extend(receipt.result)

    non_marker = [fragment for fragment in fragments if fragment.fragment_type != "marker"]
    explicit_empty = any(receipt.result == [] for receipt in ctx.call_receipts)

    if explicit_empty and not non_marker:
        output: list[BaseFragment] = []
    elif not non_marker and receipt_count > 1:
        output = []
    else:
        output = non_marker or fragments

    logger.debug(f"JOURNAL: Outputting fragments: {output}")
    return output
