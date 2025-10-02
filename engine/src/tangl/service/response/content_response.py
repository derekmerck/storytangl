from __future__ import annotations
from typing import Union, Annotated

from pydantic import Field

from tangl.core import BaseFragment
# from tangl.service.user import UserEventFragment
from tangl.service.response.base_response import BaseResponse


AnyContentFragment = Annotated[
    Union[
        BaseFragment,

        # Static content
        # --------------
        # ContentFragment
        # DialogFragment,
        # MediaFragment,

        # Styled Data
        # -----------
        # KvFragment,

        # Control/UX
        # ----------
        # ChoiceFragment,  # Activatable content
        # ControlFragment,
        # GroupFragment,
        # UserEventFragment
    ],
    Field(discriminator='fragment_type')
]

class ContentResponse(BaseResponse):
    content: list[AnyContentFragment] = Field(...)
    # This _should_ automatically cast to proper model based on declared fragment type

