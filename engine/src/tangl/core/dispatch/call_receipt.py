# /tangle/core/dispatch/call_receipt.py
"""
Job receipts
------------
Immutable results returned by handlers. Each receipt is a :class:`~tangl.core.record.Record`
that captures the result payload and optional typing info for validation.
"""
from __future__ import annotations
from typing import Any, Self, Optional, Type, Literal, ClassVar, Callable, Iterator
from enum import Enum
from uuid import UUID
from collections import ChainMap

from pydantic import Field

from tangl.core.entity import Entity
from tangl.core.record import Record

# ----------------------------
# Receipts and Aggregation

class ResultCode(str, Enum):
    OK = "ok"
    SKIP = "skip"        # handler matched but chose not to act
    INVALID = "invalid"  # handler matched but input invalid
    NONE = "none"        # nothing applicable (for aggregations)
    ERROR = "error"

class AggregatorType(Enum):
    GATHER = "gather"
    MERGE = "merge"
    FIRST = "first"
    LAST = "last"
    ANY = "any"
    ALL = "all"

class CallReceipt(Record):
    """
    CallReceipt(blame: Behavior, result: Any)

    Immutable result record from a handler invocation.

    Why
    ----
    Provides a uniform, auditable envelope for handler outputs so dispatch
    pipelines can be composed and inspected.

    Key Features
    ------------
    * **Typed payload** – `result` plus optional `result_type` hint for validation.
    * **Composable reducers** – helpers to collect or summarize multiple receipts.

    API
    ---
    - :attr:`result` – value produced by the handler.
    - :attr:`result_type` – enum/string/type hint for consumers.
    - :meth:`gather_results` – list of all payloads.
    - :meth:`first_result` – first truthy payload across receipts.
    - :meth:`last_result` – last truthy payload across receipts (pipeline-style).
    - :meth:`any_truthy` – boolean OR across payloads.
    - :meth:`all_truthy` – boolean AND across payloads.
    """
    record_type: Literal['call_receipt'] = Field("call_receipt", alias='type')
    blame_id: UUID = Field(..., alias="behavior_id")

    # -----------------------
    # Result data
    result: Any
    result_code: ResultCode = ResultCode.OK
    result_type: Optional[Enum | str | Type[Entity]] = None  # use for validation

    # -----------------------
    # Call Introspection

    # !don't try to serialize or compare these!
    ctx: Any = Field(None, exclude=True)
    args: tuple | None = Field(None, exclude=True)
    params: dict | None = Field(None, exclude=True)

    # May include these explicitly or infer from args
    caller_id: Optional[UUID] = None  # args[0].uid
    other_ids: list[UUID] = None      # [a.uid for a in args[1:]]

    message: str | None = None

    # -----------------------
    # Aggregation

    @classmethod
    def gather_results(cls, *receipts: Self) -> Iterator[Any]:
        return (r.result for r in receipts if r.result is not None)

    @classmethod
    def merge_results(cls, *receipts: Self) -> ChainMap:
        results = cls.gather_results(*receipts)
        return ChainMap(*results)

    @classmethod
    def first_result(cls, *receipts: Self) -> Any:
        return next(cls.gather_results(*receipts), None)

    @classmethod
    def any_truthy(cls, *receipts: Self) -> bool:
        # all false -> not any true
        return any(cls.gather_results(*receipts))

    @classmethod
    def last_result(cls, *receipts: Self) -> Any:
        # Useful for pipelining
        return next(cls.gather_results(*reversed(receipts)), None)

    @classmethod
    def all_truthy(cls, *receipts: Self) -> bool:
        # any false -> not all true
        return all(cls.gather_results(*receipts))

    aggregation_func: ClassVar[dict[AggregatorType, Callable]] = {
        AggregatorType.GATHER: gather_results,
        AggregatorType.MERGE: merge_results,
        AggregatorType.FIRST: first_result,
        AggregatorType.ANY: any_truthy,
        AggregatorType.LAST: last_result,
        AggregatorType.ALL: all_truthy,
    }

    @classmethod
    def aggregate(cls, aggregator: AggregatorType = AggregatorType.GATHER,
                       *receipts: Self) -> Iterator[Any] | Any | bool | ChainMap:
        # Helper to avoid lambdas
        aggregation_func = cls.aggregation_func.get(aggregator)
        if aggregation_func is None:
            raise ValueError(f"Unknown aggregation type {aggregator}")
        return aggregation_func(*receipts)

    # -----------------------
    # Result-like helpers

    # Only invoke these directly to create a behavior-like response.
    # todo: should we allow these to be passed through by behavior.__call__()?

    @classmethod
    def ok(cls, blame, result, **kw):
        return cls(blame_id=blame.uid, result=result, result_code=ResultCode.OK, **kw)

    @classmethod
    def skip(cls, blame, msg=None, **kw):
        return cls(blame_id=blame.uid, result=None, result_code=ResultCode.SKIP, message=msg, **kw)

    @classmethod
    def invalid(cls, blame, msg=None, **kw):
        return cls(blame_id=blame.uid, result=None, result_code=ResultCode.INVALID, message=msg, **kw)

    @classmethod
    def error(cls, blame, msg, **kw):
        return cls(blame_id=blame.uid, result=None, result_code=ResultCode.ERROR, message=msg, **kw)
