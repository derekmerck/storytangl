from typing import Union, Annotated
from uuid import uuid4
from datetime import datetime

from pydantic import BaseModel, Field

from tangl.type_hints import Identifier
from .base_fragment import ResponseFragment, ResponseFragmentUpdate
from .media_fragment import MediaResponseFragment, MediaResponseFragmentUpdate
from .text_fragment import TextResponseFragment
from .kv_fragment import KvResponseFragment
from . import RESPONSE_SCHEMA_VERSION

class BaseResponse(BaseModel):
    schema_version: str = RESPONSE_SCHEMA_VERSION
    response_id: Identifier = Field(default_factory=uuid4, init=False)
    timestamp: datetime = Field(default_factory=datetime.now, init=False)
    data: list[ResponseFragment]

class InfoResponse(BaseResponse):
    # Any info response is an ordered dict of (potentially styled) kv fragments interpreted as key/value pairs
    data: list[KvResponseFragment]

ContentFragment = Annotated[
    Union[TextResponseFragment, MediaResponseFragment, ResponseFragmentUpdate],
    Field(discriminator='type')
]

class ContentResponse(BaseResponse):
    # Any content response is an ordered list of content fragments (text, media, or update)
    data: list[ContentFragment]  # This will automatically cast to proper model
