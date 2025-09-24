# tangl/core/dispatch/job_receipt.py
from __future__ import annotations
import functools
from typing import Any, ClassVar, Self
from uuid import UUID

# from pydantic import model_validator, Field

# from tangl.type_hints import UnstructuredData
from tangl.utils.base_model_plus import HasSeq
from tangl.core.entity import Entity

@functools.total_ordering
class JobReceipt(HasSeq, Entity):

    blame_id: UUID | tuple[UUID, ...]  # end point(s) for blame edge on result
    result: Any

    @classmethod
    def last_result(cls, *receipts: Self) -> Any | None:
        return None if len(receipts) == 0 else receipts[-1].result

    @classmethod
    def all_true(cls, *receipts: Self) -> bool:
        return all([bool(r.result) for r in receipts if r is not None])
