from typing import Literal, Optional, Any
from uuid import UUID, uuid4

from pydantic import Field
import yaml

from tangl.type_hints import UniqueLabel, Identifier
from tangl.core.entity import Entity
from .presentation_hints import PresentationHints

class ResponseFragment(Entity, extra='allow'):
    """
    Represents a basic content element in any response and the core
    schema for communicating story-content and info-content to the front-end.

    Presentation hints need not be respected by the client.

    Attributes:
    - fragment_type: General type of fragment, i.e., text, media, kv
    - label (str): Optional name/key for the fragment
    - content (str): Optional value/text/media for the fragment
    - content_format: Instruction for how to parse content field, ie, markdown or encoded data
    - presentation_hints: Optional suggestions for icon, html styling, and staging for presentation
    """
    # base features
    fragment_id: UUID = Field(init=False, default_factory=uuid4)
    fragment_type: str = Field(..., alias='type')
    label: UniqueLabel = None
    content: Any
    content_format: str = Field(None, alias='format')
    presentation_hints: Optional[PresentationHints] = None

    # If not wrapped in a response, can be used for async batches to assemble a response on client end
    response_id: Optional[UUID] = None
    sequence: Optional[int] = 0

    # Params to be included with the cb if the fragment is "activated", ie, a choice, link, button, input
    active: bool = False
    activation_payload: Optional[Any] = None

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(*args, **kwargs)

    def __str__(self):
        data = self.model_dump()
        s = yaml.dump(data, default_flow_style=False)
        return s

UpdateFragmentType = Literal['update', 'discard']

class ResponseFragmentUpdate(ResponseFragment, extra='allow'):
    fragment_type: UpdateFragmentType = Field("update", alias='type')
    reference_id: Identifier = Field(..., alias='ref_id')
    # identifier (uid or label) for the fragment we want to update content or presentation of
