# tangl/core/dispatch/handler.py
"""Dispatch version 37.1 - deprecated"""
from __future__ import annotations
import functools
from enum import Enum
from typing import Any, Optional
import logging

from pydantic import ConfigDict

from tangl.utils.func_info import HandlerFunc
from tangl.utils.base_model_plus import HasSeq
from tangl.core.entity import Entity, Selectable, is_identifier
from .call_receipt import CallReceipt
from .behavior import HandlerPriority

logger = logging.getLogger(__name__)

@functools.total_ordering
class Handler(HasSeq, Selectable, Entity):
    """
    Handler(func: ~typing.Callable[[Entity, ...], typing.Any], priority: int)

    Wrapper around a callable behavior.

    Why
    ----
    Encapsulates a function and metadata so it can be ordered, filtered, and
    invoked within a resolution context. Every call yields a :class:`CallReceipt`.

    Key Features
    ------------
    * **Prioritized** – order by priority then registration order.
    * **Selectable** – declare criteria for when the handler applies.
    * **Auditable** – returns a receipt linking result to originating entity.

    API
    ---
    - :meth:`__call__(caller, *entities, ctx=None, ns=None, **params)<__call__>` – invoke with caller and other participating entities, params, and an optional execution context and namespace (ns)
    - :meth:`get_label` – derive label from func name

    .. admonition:: Reserved Keywords

       `ns` and `ctx` are reserved keyword arguments on the called function signature.  They may be added or manipulated during handler :meth:`__call__` invocation.

    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    func: HandlerFunc
    priority: HandlerPriority | int = HandlerPriority.NORMAL
    result_type: Optional[Enum | str] = None  # No need to enumerate this yet

    def has_func_name(self, value: str) -> bool:
        # for matching
        return self.func.__name__ == value

    @is_identifier
    def get_label(self) -> str:
        return self.label or self.func.__name__

    # todo: model validator that confirms user didn't try to bind ctx or ns positionally?

    def __call__(self,
                 caller: Entity,
                 *others: Entity,
                 ctx: Optional[Any] = None,
                 ns: Optional[dict] = None,
                 **params: Any) -> CallReceipt:

        # todo: could check what's named by the handler sig, otherwise
        #       just consume unnecessary args in phase handlers.

        # get ns from ctx.get_ns if possible, expose ctx for funcs that want to
        # access frame step variables see tangl.vm.context and tangl.vm.frame
        if ctx is not None:
            params.setdefault("ctx", ctx)
        if ns is None and ctx and hasattr(ctx, 'get_ns'):
            ns = ctx.get_ns()
        if ns is not None:
            params.setdefault("ns", ns)

        receipt_kwargs = dict()
        if hasattr(caller, 'uid'):
            receipt_kwargs["caller_id"] = caller.uid
        other_ids = [o.uid for o in others if hasattr(o, 'uid')]
        if other_ids:
            receipt_kwargs["other_ids"] = other_ids
        if params:
            receipt_kwargs["params"] = params

        result = self.func(caller, *others, **params)

        # todo: type check that receipts aren't returned and re-wrapped?  What
        #       if a handler invokes another dispatch as a subroutine?

        return CallReceipt(behavior_id=self.uid,
                          result=result,
                          result_type=self.result_type,
                          **receipt_kwargs)

    def __lt__(self, other) -> bool:
        # order by priority, then seq (uncorrelated if handlers are from classes with
        # their own seq), then uid as a final (non-deterministic) tie-breaker
        return (self.priority, self.seq, self.uid) < (other.priority, other.seq, other.uid)
