from typing import Literal, Optional, Any
from uuid import UUID, uuid4

from pydantic import Field, BaseModel
import yaml

import tangl.utils.setup_yaml
from tangl.type_hints import UniqueLabel, Identifier
from .presentation_hints import PresentationHints

class ContentFragment(BaseModel, extra='allow'):
    """
    Represents a basic content element in any response and the core
    schema for communicating story-content and info-content to the front-end.

    Presentation hint fields are optional and may not be respected by the client.

    Attributes:
    - fragment_type: General type of fragment, i.e., text, media, kv, runtime
    - label (str): Optional name/key for the fragment
    - content (str): Optional value/text/media for the fragment
    - content_format: Instruction for how to parse content field, ie, markdown or encoded data
    """
    # base features
    uid: UUID = Field(init=False, default_factory=uuid4, alias="fragment_id")
    fragment_type: str = Field(..., alias='type')
    label: UniqueLabel = Field(None)
    content: Any = Field(...)
    content_format: str = Field(None, alias='format')
    presentation_hints: Optional[PresentationHints] = Field(None, alias='hints')

    # If not wrapped in a response, can be used with batches to assemble a response on client end
    response_id: Optional[UUID] = None
    sequence: Optional[int] = 0

    # Indicate if fragment can be "activated", for choices, allow the choice to be selected, etc.
    activatable: bool = False
    # For activatable fragments, is this fragment _currently_ active.
    active: bool = True
    # Params to be included with the cb if the fragment is "activated", ie, a choice, link, button, input, custom ui trigger
    activation_payload: Optional[Any] = None

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(*args, **kwargs)

    def __str__(self):
        data = self.model_dump()
        s = yaml.dump(data, default_flow_style=False)
        return s

UpdateFragmentType = Literal['update', 'delete']

class UpdateFragment(ContentFragment, extra='allow'):
    fragment_type: UpdateFragmentType = Field("update", alias='type')
    reference_type: Literal['content'] = "content"
    reference_id: Identifier = Field(..., alias='ref_id')
    # identifier (uid or unique label) for the content fragment we want to update content or presentation of

