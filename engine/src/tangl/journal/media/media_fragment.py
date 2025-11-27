from __future__ import annotations
from typing import Literal, Optional
from base64 import b64encode

from pydantic import field_serializer

from tangl.type_hints import Pathlike
from tangl.journal.content import ContentFragment, PresentationHints
from tangl.core.behavior import BehaviorRegistry
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT

# from tangl.media.enums import MediaRole
from tangl.media.media_data_type import MediaDataType
from .staging_hints import StagingHints

ContentFormatType = Literal['url', 'data', 'xml', 'json', 'rit']
# Media fragments can have a RIT as content and need to be _dereferenced_ at the service
# layer to an actual data object or file url
# The final mime-type is assigned there as well

media_fragment_handler = BehaviorRegistry(
    label="media_fragment_handler",
    aggregation_strategy="pipeline")

class MediaFragment(ContentFragment, extra='allow'):
    """
    This is a type of fragment that can be generated according to
    inline data or url, or from a media dependency linked to a MediaRIT.

    Attributes:
      - label (str): Text associated with the content (caption, label, lyric, etc.)
      - content_type: image, vec, vo, music, sfx, anim, mov
      - content: Path, xml, dict, binary, or RIT
      - content_format: path, xml, json, binary, rit
      - media_role (MediaRole): Intended use, e.g., `narrative_im`

    Only one of url or data may be provided.
    """
    content_type: MediaDataType = MediaDataType.MEDIA
    content: Pathlike | bytes | str | dict | MediaRIT
    content_format: ContentFormatType
    staging_hints: Optional[StagingHints] = None
    media_role: Optional[str] = None  # fragment's intended use
    scope: Optional[str] = "world"

    # todo: could also pickle it if creating a dto to a python client
    @field_serializer("content")
    def _encode_binary_content(self, content):
        if self.content_format == "data" and isinstance(self.content, bytes):
            return b64encode(content)
        return str(content)
