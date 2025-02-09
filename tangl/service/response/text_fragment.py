from typing import Literal

from pydantic import Field

from .base_fragment import ResponseFragment

TextFragmentType = Literal['text', 'title', 'narrative', 'paragraph', 'dialog', 'choice']
TextContentFormatType = Literal['plain', 'html', 'markdown']

class TextResponseFragment(ResponseFragment, extra='allow'):
    fragment_type: TextFragmentType = Field("text", alias='type')
    content: str
    content_format: TextContentFormatType = Field("plain", alias='format')
