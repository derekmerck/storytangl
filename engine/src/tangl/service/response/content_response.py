from __future__ import annotations
from typing import Union, Annotated

from pydantic import Field, BaseModel

from tangl.core.fragment import KvFragment, ControlFragment, GroupFragment
from tangl.core.solver import ContentFragment
from tangl.media.media_fragment import MediaFragment
from tangl.discourse.discourse_fragment import DialogFragment, ChoiceFragment
# from tangl.service.user import UserEventFragment
from tangl.service.response.base_response import BaseResponse


AnyContentFragment = Annotated[
    Union[
        ContentFragment,
        # MediaFragment,
        # ChoiceFragment,
        # DialogFragment,
        # # InfoFragment,
        # KvFragment,
        # ControlFragment,
        # GroupFragment,
        # UserEventFragment
    ],
    Field(discriminator='fragment_type')
]

class ContentResponse(BaseResponse):
    content: list[AnyContentFragment] = Field(...)
    # This _should_ automatically cast to proper model based on declared fragment type

