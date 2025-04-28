from typing import Literal
from pydantic import Field

from .media_fragment import MediaFragment
from tangl.core.fragment import ControlFragment

class MediaControlFragment(MediaFragment, ControlFragment, extra='allow'):
    fragment_type: Literal["media_update", "media_delete"] = Field("media_update", alias='type')
    reference_type: Literal["media"] = "media"
