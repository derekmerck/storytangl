"""
Job receipts
------------
Immutable results returned by handlers. Each receipt is a :class:`~tangl.core.record.Record`
that captures the result payload and optional typing info for validation.
"""
from __future__ import annotations
from typing import Any, Self, Optional, Type, Literal
from enum import Enum
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.core.record import Record


class JobReceipt(Record):
    """
    JobReceipt(blame: Handler, result: Any)

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
    - :meth:`first_result` – first truthy payload across receipts.
    - :meth:`last_result` – last truthy payload across receipts (pipeline-style).
    - :meth:`any_truthy` – boolean OR across payloads.
    - :meth:`all_truthy` – boolean AND across payloads.
    - :meth:`gather` – list of all payloads.
    """
    record_type: Literal['job_receipt'] = Field("job_receipt", alias='type')

    result: Any
    result_type: Optional[Enum | str | Type[Entity]] = None  # use for validation

    # Call introspection
    caller_id: Optional[UUID] = None
    other_ids: list[UUID] = None
    ctx: Any = Field(None, exclude=True)  # _never_ try to serialize or compare this
    params: Optional[StringMap] = Field(None, exclude=True)  # _never_ try to serialize or compare this

    @classmethod
    def first_result(cls, *receipts: Self) -> Any | None:
        """Return the first truthy `result` among `receipts`, else `None`."""
        for r in receipts:
            if r and r.result:
                return r.result
        return None
        # may want to change this to first non-none result as with last result?

    @classmethod
    def last_result(cls, *receipts: Self) -> Any | None:
        """Return the last non-none `result` among `receipts`, else `None`."""
        # this is a PIPE when the last handler is a composer that yields a comprehensive result
        for r in reversed(receipts):
            if r is not None and r.result is not None:
                return r.result
        return None
        # Returning the reversed(first-truthy) is more succinct here, but fails if the desired
        # final result is Falsy, like [] for an empty compositor step would be _skipped_, and
        # then the most recent Truthy result from the pipe would be returned instead.
        # return cls.first_result(*reversed(receipts))

    @classmethod
    def any_truthy(cls, *receipts: Self) -> bool:
        """True if any receipt has a truthy `result`."""
        return bool(cls.first_result(*receipts))

    @classmethod
    def all_truthy(cls, *receipts: Self) -> bool:
        """True if all non-`None` receipts have truthy `result`."""
        # could early exit on this in dispatch
        return all([bool(r.result) for r in receipts if r is not None])

    @classmethod
    def gather(cls, *receipts: Self) -> list[Any]:
        """Collect all non-`None` receipt payloads into a list."""
        return [r.result for r in receipts if r is not None]
