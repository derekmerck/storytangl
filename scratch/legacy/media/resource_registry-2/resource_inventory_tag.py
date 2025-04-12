from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from uuid import UUID

import pydantic
from pydantic import Field

from tangl.entity import Entity, SingletonEntity
from tangl.utils.uuid_for_secret import uuid_for_secret
from .enums import ResourceDataType

# todo: this should be a singleton, I think
class ResourceInventoryTag(Entity):
    name: Optional[str] = None
    data_hash: Optional[str] = None

    @pydantic.model_validator(mode='after')
    def _check_at_least_one(self) -> ResourceInventoryTag:
        if not self.name and not self.data_hash:
            raise ValueError("ResourceInventoryTag requires at least one of 'name' or 'data_hash'")
        return self

    resource_type: ResourceDataType

    inventory_time: datetime = Field(default_factory=datetime.now)
    expiry: Optional[datetime | timedelta] = None

    @pydantic.model_validator(mode='after')
    def _convert_expiry_time_delta(self):
        if isinstance(self.expiry, timedelta):
            self.expiry = self.inventory_time + self.expiry
        return self

    uid_: UUID = None

    @property
    def _secret(self) -> str | bytes:
        return self.name or self.data_digest

    @property
    def uid(self) -> UUID:
        return uuid_for_secret(self._secret)

    # Implements "HasAliases"
    def get_aliases(self):
        return [ v for v in [ self.name, self.data_hash ] if v ]

    def __hash__(self):
        # Want to be able to throw these into a set to uniquify them
        return hash((type(self),) + tuple(self.model_dump_json()))

    # class Config:
    #     frozen = True
