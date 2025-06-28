from typing import Optional, Any
from enum import Enum

import yaml
from pydantic import ConfigDict, Field, BaseModel

from tangl.core.entity import Entity


class BaseFragment(Entity):
    """
    Represents a minimal content element and the core schema for communicating
    content to the front-end.

    - JournalFragments and InfoFragments are _content_ objects in the fragment stream
    - GroupFragments, and UpdateFragments are _control_ objects in the fragment stream
    - KvFragments, MediaFragments, and DiscourseFragments have special rules for how the
    content field is represented.

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

    def __str__(self):
        data = self.model_dump()
        s = yaml.dump(data, default_flow_style=False)
        return s

    # If not wrapped in a response, can be used with batches to assemble a response on client end
    # response_id: Optional[Identifier] = None
    # sequence: Optional[int] = None