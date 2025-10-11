from __future__ import annotations
from typing import Optional, Union, Protocol
from datetime import datetime, timedelta

from pydantic import BaseModel, Field, model_validator

from tangl.core.singleton import DataSingleton
from tangl.core.entity.handlers import HasTags, HasAliases
from .enums import MediaDataType

class MediaRecord(HasAliases, HasTags, DataSingleton):
    """
    MediaRecords can be dereferenced by the response handler to generate a client-relative path.
    """
    resource_type: MediaDataType = None
    inventory_time: datetime = Field(default_factory=datetime.now)
    expiry: Optional[datetime | timedelta] = None

    @model_validator(mode='after')
    def _convert_expiry_time_delta(self):
        if isinstance(self.expiry, timedelta):
            self.expiry = self.inventory_time + self.expiry
        return self

    # aliases_: set[IdentifierType] = Field(default_factory=set, alias="alias")
    #
    # @property
    # def aliases(self) -> set[IdentifierType]:
    #     res = self.aliases_ | { self.data_hash, self.label }
    #     res.discard(None)
    #     return res
    #
    # def has_alias(self, identifier: IdentifierType) -> bool:
    #     return identifier in self.aliases
