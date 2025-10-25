# tangl.core.fragment.content_fragment.py
from typing import Optional, Any
from enum import Enum

from pydantic import Field

from tangl.core.record import BaseFragment
from .presentation_hints import PresentationHints


class ContentFragment(BaseFragment):

    fragment_type: Optional[ str | Enum ] = 'content'

    content: Any
    content_format: Optional[str] = Field(None, alias='format')
    # seq and mime-type are added in the service layer, when the fragment is serialized into a dto.
    presentation_hints: Optional[PresentationHints] = Field(None, alias='hints')
