from typing import Union, Annotated
from uuid import uuid4
from datetime import datetime

from pydantic import BaseModel, Field

from tangl.info import __version__
from tangl.type_hints import Identifier
from .base_fragment import BaseFragment, ContentUpdateFragment, RuntimeInfoFragment
from .media_fragment import MediaFragment, MediaUpdateFragment
from .text_fragment import TextFragment
from .kv_fragment import KvFragment

# schema version can be tied to library minor version
minor_version = ".".join(__version__.split(".")[0:1])  # i.e "3.2"
RESPONSE_SCHEMA_VERSION = minor_version

class BaseResponse(BaseModel):
    schema_version: str = RESPONSE_SCHEMA_VERSION
    response_id: Identifier = Field(default_factory=uuid4, init=False)
    timestamp: datetime = Field(default_factory=datetime.now, init=False)
    data: list[BaseFragment]


class InfoResponse(BaseResponse):
    # Any info response is an ordered dict of (potentially styled) kv fragments interpreted as key/value pairs
    data: list[KvFragment]

ContentFragment = Annotated[
    Union[TextFragment, MediaFragment, ContentUpdateFragment],
    Field(discriminator='fragment_type')
]

class ContentResponse(BaseResponse):
    # Any content response is an ordered list of content fragments (text, media, or update)
    data: list[ContentFragment]  # This will automatically cast to proper model


class RuntimeResponse(BaseResponse):
    data: list[RuntimeInfoFragment]
