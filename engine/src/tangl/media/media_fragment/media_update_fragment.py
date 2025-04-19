from typing import Literal
from pydantic import Field

from .media_fragment import MediaFragment
from tangl.core.fragment import UpdateFragment

class MediaUpdateFragment(MediaFragment, UpdateFragment, extra='allow'):
    fragment_type: Literal["media_update"] = Field("media_update", alias='type')
    reference_type: Literal["media"] = "media"
