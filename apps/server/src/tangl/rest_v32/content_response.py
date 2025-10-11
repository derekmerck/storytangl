from __future__ import annotations
from typing import Union, Annotated, Any, Optional, Self
from uuid import uuid4
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, field_serializer

import tangl.info
from tangl.type_hints import Identifier
from tangl.core.fragment import ContentFragment, UpdateFragment, MediaFragment, MediaUpdateFragment, TextFragment, KvFragment, GroupFragment, UserEventFragment

# schema version can be tied to library minor version
minor_version = ".".join(tangl.info.__version__.split(".")[0:1])  # i.e "3.2"
CONTENT_SCHEMA_VERSION = minor_version

AnyContentFragment = Annotated[
    Union[TextFragment, MediaFragment, KvFragment, UpdateFragment, MediaUpdateFragment, GroupFragment, UserEventFragment],
    Field(discriminator='fragment_type')
]

class ContentResponse(BaseModel):
    # Any content response is an ordered list of content fragments
    schema_version: str = Field(CONTENT_SCHEMA_VERSION, init=False)
    uid: Identifier = Field(default_factory=uuid4, init=False, alias="response_id")
    timestamp: datetime = Field(default_factory=datetime.now, init=False)
    error: Optional[str] = None
    data: list[AnyContentFragment] = Field(...)
    # This _should_ automatically cast to proper model based on declared fragment type

    @field_validator("data", mode="before")
    @classmethod
    def _cast_dict_to_kv_list(cls, data):
        if isinstance(data, dict):
            # Converter for simple, un-styled kv responses
            data = [ {'key': k, 'value': v, 'fragment_type': 'kv'} for k, v in data.items() ]
        return data

    @field_validator("data", mode="before")
    @classmethod
    def _check_has_content(cls, data):
        if not data:
            raise ValueError("ContentResponse data is empty.")
        return data

    @field_serializer("timestamp")
    def _ts_isoformat(self, value: datetime) -> str:
        return value.isoformat()

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('by_alias', True)
        return super().model_dump(*args, **kwargs)

    def get_ordered_fragments(self) -> list[AnyContentFragment]:
        """Return fragments in sequence order"""
        return sorted(self.data, key=lambda f: getattr(f, "sequence", 0))

    def filter_for_client(self, capabilities: set[str]) -> Self:
        """
        Return a new ContentResponse with fragments filtered for client capabilities.
        """
        # Filter logic here (e.g., removing media fragments if 'media' not in capabilities)
        filtered_fragments = [f for f in self.data if self._is_supported(f, capabilities)]
        return self.model_copy(update={'data': filtered_fragments})
