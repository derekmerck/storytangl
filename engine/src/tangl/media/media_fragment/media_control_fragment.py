from typing import Literal
from pydantic import Field

from tangl.core.fragment import ControlFragment
from .media_fragment import MediaFragment

class MediaControlFragment(MediaFragment, ControlFragment, extra='allow'):
    fragment_type: Literal["media_update", "media_delete"] = Field("media_update", alias='type')
    reference_type: Literal["media"] = "media"
