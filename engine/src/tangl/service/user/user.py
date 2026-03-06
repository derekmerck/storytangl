from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, field_serializer, field_validator

from tangl.core import Entity
from tangl.type_hints import Hash
from tangl.utils.hash_secret import hash_for_secret


class User(Entity):
    """Service user account model."""

    content_hash: Hash = Field(None, json_schema_extra={"is_identifier": True})
    created_dt: datetime = Field(default_factory=datetime.now, init=False)
    last_played_dt: Optional[datetime] = None
    privileged: bool = False
    current_ledger_id: UUID | None = None

    @field_validator("created_dt", "last_played_dt", mode="before")
    @classmethod
    def _from_isoformat(cls, data):
        if isinstance(data, str):
            return datetime.fromisoformat(data)
        return data

    @field_serializer("created_dt", "last_played_dt")
    def _to_isoformat(self, data):
        if data:
            return data.isoformat()
        return data

    def set_secret(self, value: str) -> None:
        self.content_hash = hash_for_secret(value)
