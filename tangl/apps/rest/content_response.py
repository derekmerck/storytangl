from __future__ import annotations
from typing import Union, Annotated, Literal, Any, Self
from uuid import uuid4
from datetime import datetime

from pydantic import BaseModel, Field

import tangl.info
from tangl.type_hints import Identifier
from tangl.service.content_fragment import ContentFragment, UpdateFragment, MediaFragment, MediaUpdateFragment, TextFragment, KvFragment

# schema version can be tied to library minor version
minor_version = ".".join(tangl.info.__version__.split(".")[0:1])  # i.e "3.2"
CONTENT_SCHEMA_VERSION = minor_version

AnyContentFragment = Annotated[
    Union[TextFragment, MediaFragment, KvFragment, UpdateFragment, MediaUpdateFragment],
    Field(discriminator='fragment_type')
]

class ContentResponse(BaseModel):
    # Any content response is an ordered list of content fragments (text, media, or update)
    schema_version: str = CONTENT_SCHEMA_VERSION
    response_id: Identifier = Field(default_factory=uuid4, init=False)
    timestamp: datetime = Field(default_factory=datetime.now, init=False)
    data: list[AnyContentFragment] = Field(default_factory=list)
    # This _should_ automatically cast to proper model based on declared fragment type

    @classmethod
    def from_ordered_dict(cls, data: dict) -> Self:
        fragments = [ {'key': k, 'value': v, 'fragment_type': 'kv'} for k, v in data.items() ]
        return ContentResponse(data=fragments)
