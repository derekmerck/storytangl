"""
Subroutine call/return behavior patterns.

These handlers implement return semantics using the call stack. They can be
registered on nodes that serve as sinks for callable subgraphs to trigger an
automatic jump back to the caller.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from tangl.core import Node

logger = logging.getLogger(__name__)


def auto_return_from_subgraph(node: Node, *, ctx, **kwargs):
    """
    Pop the call stack and jump back to the caller.

    Parameters
    ----------
    node:
        The sink node where control returns from the subgraph.
    ctx:
        Execution context carrying the current :class:`~tangl.vm.Frame`.

    Returns
    -------
    None
        Always returns ``None``; :meth:`~tangl.vm.Frame.jump_to_node` advances
        execution when a frame is available.
    """
    frame = getattr(ctx, "_frame", None)

    if frame is None:
        logger.debug("Context missing frame; cannot return from %s", node)
        return None

    if not frame.call_stack:
        logger.debug("No call stack at %s; skipping return", getattr(node, "label", node))
        return None

    top = frame.call_stack.pop()
    frame._last_returned_to = top.return_cursor_id

    logger.debug(
        "Auto-returning from %s to %s (call_type=%s)",
        getattr(node, "label", node),
        top.call_site_label,
        top.call_type,
    )

    frame.jump_to_node(top.return_cursor_id, include_postreq=False)
    return None


def conditional_return(node: Node, *, ctx, call_type: str | None = None, **kwargs):
    """
    Return to the caller only when the top frame matches ``call_type``.

    Parameters
    ----------
    node:
        Node acting as the subgraph sink.
    ctx:
        Execution context carrying the current :class:`~tangl.vm.Frame`.
    call_type:
        Required :attr:`~tangl.vm.frame.StackFrame.call_type` value for the
        return to trigger.

    Returns
    -------
    None
    """
    frame = getattr(ctx, "_frame", None)

    if frame is None or not frame.call_stack:
        return None

    top = frame.call_stack[-1]

    if call_type is not None and top.call_type != call_type:
        logger.debug(
            "Not returning from %s: call_type %s != %s",
            getattr(node, "label", node),
            top.call_type,
            call_type,
        )
        return None

    return auto_return_from_subgraph(node, ctx=ctx)
