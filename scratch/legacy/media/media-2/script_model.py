from typing import Optional

from pydantic import BaseModel, model_validator, AnyUrl

from tangl.type_hints import UniqueLabel
from .type_hints import MediaResource
from .enums import MediaRole
from .media_spec import MediaSpecification

class MediaItemScript(BaseModel, arbitrary_types_allowed=True):
    """
    MediaItemScript -> MediaNode -> JournalMediaItem (response)
    """
    # Embedded or external resources and can be passed along directly
    url: Optional[AnyUrl] = None  # external link
    data: Optional[MediaResource] = None    # inline svg or b64 encoded image

    # This requires a registry lookup for name
    name: Optional[UniqueLabel] = None  # backend file name or other media_id

    # This requires a loc lookup, or creation + registration
    # spec: Optional[MediaSpecification] = None         #: spec for procedural/generative creation
    # todo: can't use the class b/c abstract method
    spec: Optional[dict] = None         #: spec for procedural/generative creation

    media_role: Optional[MediaRole] = None
    text: Optional[str] = None  # title or caption

    @model_validator(mode='after')
    def _check_exactly_one_field(self):
        """
        Ensures that exactly one of `url`, `data`, `name`, or `spec` is provided.
        """
        fields = ['url', 'data', 'name', 'spec']
        provided_fields = sum(1 for field in fields if getattr(self, field) is not None)

        if provided_fields != 1:
            raise ValueError("Exactly one of 'url', 'data', 'name', or 'spec' must be provided.")
        return self
