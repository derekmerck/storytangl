from typing import Optional, Any
from enum import Enum

import yaml
from pydantic import ConfigDict, Field, BaseModel

from tangl.core.entity import Entity


class ContentFragment(Entity):
    """
    Specialized entity that provides the core schema for communicating content
    about the graph to a front-end.

    Attributes:
    - fragment_type: General type of fragment, i.e., text, media, kv, runtime, used
      for automatically inferring fragment type from data.
    - label (str): Optional name/key for the fragment
    - content (str): Optional value/text/media for the fragment
    - content_format: Instruction for how to parse content field, ie, markdown or encoded data
    """
    # fragments are immutable once created
    model_config = ConfigDict(frozen=True)

    fragment_type: Optional[str|Enum] = Field(..., alias='type')
    # intent for fragment, e.g., 'content', 'update', 'group', 'media', etc.
    content: Any
    content_format: Optional[str] = Field(None, alias='format')
    # seq and mime-type are added in the service layer, when the fragment is serialized into a dto.
