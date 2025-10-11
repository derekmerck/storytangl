from typing import Optional

from pydantic import model_validator, AnyUrl

from tangl.type_hints import UniqueLabel, StringMap
from tangl.scripting import BaseScriptItem
from tangl.media.enums import MediaRole

class MediaItemScript(BaseScriptItem):
    """
    MediaItemScript -> MediaNode -> JournalMediaItem (response)
    """
    media_role: Optional[MediaRole] = None
    text: Optional[str] = None        # title or caption

    # Embedded or external resources and can be passed along directly
    url: Optional[AnyUrl] = None      # external link
    data: Optional[str|bytes] = None  # inline svg or b64 encoded image

    # This requires a registry lookup for name
    media_ref: Optional[UniqueLabel] = None  # backend file name or other media_id

    # This requires a loc lookup, or creation + registration
    # todo: can't use the class b/c abstract method
    media_template: Optional[StringMap] = None   #: spec for procedural/generative creation


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
