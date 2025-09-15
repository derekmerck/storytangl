# tangl/core/dispatch/job_receipt.py
from __future__ import annotations
import functools
from typing import Any, ClassVar
from uuid import UUID

from pydantic import model_validator, Field

from tangl.type_hints import UnstructuredData
from tangl.core.entity import Entity

@functools.total_ordering
class JobReceipt(Entity):

    blame_id: UUID | tuple[UUID, ...]  # blame
    result: Any
    seq: int = Field(init=False)       # type checking, ignore missing

    @model_validator(mode="before")
    @classmethod
    def _set_seq(cls, data: UnstructuredData) -> UnstructuredData:
        data = dict(data or {})
        if data.get('seq') is None:   # unassigned or passed none
            # Don't want to incr if not using it
            data['seq'] = cls.incr_count()
        return data

    _instance_count: ClassVar[int] = 0

    @classmethod
    def incr_count(cls) -> int:
        cls._instance_count += 1
        return cls._instance_count

    def __lt__(self, other: Any) -> bool:
        # Sorts non-receipts to the front without raising
        return self.seq < getattr(other, 'seq', -1)
