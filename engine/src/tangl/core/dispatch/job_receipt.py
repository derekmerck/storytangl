# tangl/core/dispatch/job_receipt.py
from __future__ import annotations
from typing import Any, Self, Optional, Type, Literal
from enum import Enum

from pydantic import Field

from tangl.core.entity import Entity
from tangl.core.record import Record

class JobReceipt(Record):
    record_type: Literal['job_receipt'] = Field("job_receipt", alias='type')

    # blame_id: UUID | tuple[UUID, ...]         # end point(s) for blame edge on result
    result: Any
    result_type: Optional[Enum | str | Type[Entity]] = None  # use for validation

    @classmethod
    def first_result(cls, *receipts: Self) -> Any | None:
        for r in receipts:
            if r and r.result:
                return r.result
        return None

    @classmethod
    def last_result(cls, *receipts: Self) -> Any | None:
        # this is a PIPE when the last handler is a composer that yields a comprehensive result
        return cls.first_result(*reversed(receipts))

    @classmethod
    def any_truthy(cls, *receipts: Self) -> bool:
        return bool(cls.first_result(*receipts))

    @classmethod
    def all_truthy(cls, *receipts: Self) -> bool:
        # could early exit on this in dispatch
        return all([bool(r.result) for r in receipts if r is not None])

    @classmethod
    def gather(cls, *receipts: Self) -> list[Any]:
        return [r.result for r in receipts if r is not None]
