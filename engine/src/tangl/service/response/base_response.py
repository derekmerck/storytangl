from __future__ import annotations
from typing import Union, Optional, Any
from uuid import uuid4
from datetime import datetime

from pydantic import Annotated, Field, BaseModel

import tangl.info
from tangl.type_hints import Identifier
from tangl.core.entity import Entity
from tangl.core.fragment import KvFragment, ControlFragment, GroupFragment
from tangl.core.solver import ContentFragment
from tangl.media.media_fragment import MediaFragment
from tangl.discourse.discourse_fragment import DialogFragment, ChoiceFragment
from tangl.service.user import UserEventFragment

# schema version can be tied to library minor version
minor_version = ".".join(tangl.info.__version__.split(".")[0:1])  # i.e "3.2"
CONTENT_SCHEMA_VERSION = minor_version


class BaseResponse(Entity):

    # Any content response is an ordered list of content fragments
    schema_version: str = Field(CONTENT_SCHEMA_VERSION, init=False)
    uid: Identifier = Field(default_factory=uuid4, init=False, alias="response_id")
    timestamp: datetime = Field(default_factory=datetime.now, init=False)
    error: Optional[str] = None
