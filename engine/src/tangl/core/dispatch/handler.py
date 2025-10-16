# tangl/core/dispatch/handler.py
from __future__ import annotations
import functools
from enum import IntEnum, Enum
from typing import Any, Optional, Protocol, runtime_checkable

from pydantic import ConfigDict

from tangl.utils.base_model_plus import HasSeq
from tangl.core.entity import Entity, Selectable, is_identifier
from .job_receipt import JobReceipt

# todo: - make this look more like v34 dispatch, with a decorator that infers how to call
#         the func by inspecting its signature.
#       - May want 1 or more Entities as args, may want an execution context
#         (namespace, phase, prior results, etc.), may want/admit kwarg params.
#       - infer caller type and result type from function sig?
#       - dynamically modify selection criteria based on expected caller type/return type?

class HandlerPriority(IntEnum):
    """
    Execution priorities for handlers.

    Each Handler is assigned a priority to control high-level ordering.
    The pipeline sorts handlers by these priorities first, with the
    following semantics:

    - :attr:`FIRST` (0) – Runs before all other handlers.
    - :attr:`EARLY` (25) – Runs after FIRST, but before NORMAL.
    - :attr:`NORMAL` (50) – Default middle priority.
    - :attr:`LATE` (75) – Runs after NORMAL, before LAST.
    - :attr:`LAST` (100) – Runs very last in the sequence.

    Users are also free to use any int as a priority. Values lower than 0 will
    run before FIRST, greater than 100 will run after LAST, and other values will
    sort as expected.
    """
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100


# Note this is runtime_checkable so Pydantic will allow it as a type-hint.
# It is not actually validated, so this is purely organizational and the function
# call will actually admit any type *args.
@runtime_checkable
class HandlerFunc(Protocol):
    def __call__(self, caller: Entity, *others: Entity, ctx: Optional[dict] = None, **params: Any) -> Any: ...
    # Variadic args are entities, to support things like __lt__(self, other) or transaction
    # type calls
    # `ctx` is a reserved kw arg for Context objects passed by the resolution frame's phase bus
    # `ns` is also a reserved kw arg for scoped namespace string maps, ns will be pulled from ctx
    # if ns is not provided but ctx is

@functools.total_ordering
class Handler(HasSeq, Selectable, Entity):
    """
    Handler(func: ~typing.Callable[[Entity, ...], typing.Any], priority: int)

    Wrapper around a callable behavior.

    Why
    ----
    Encapsulates a function and metadata so it can be ordered, filtered, and
    invoked within a resolution context. Every call yields a :class:`JobReceipt`.

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
                 **params: Any) -> JobReceipt:

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
        if ctx is not None:
            receipt_kwargs["ctx"] = ctx
        if params:
            receipt_kwargs["params"] = params

        result = self.func(caller, *others, **params)

        # todo: type check that receipts aren't returned and re-wrapped?  What
        #       if a handler invokes another dispatch as a subroutine?

        return JobReceipt(blame_id=self.uid,
                          result=result,
                          result_type=self.result_type,
                          **receipt_kwargs)

    def __lt__(self, other) -> bool:
        # order by priority, then seq (uncorrelated if handlers are from classes with
        # their own seq), then uid as a final deterministic tie-breaker
        return (self.priority, self.seq, self.uid) < (other.priority, other.seq, other.uid)
