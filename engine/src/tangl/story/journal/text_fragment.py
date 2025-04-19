from typing import Literal

from pydantic import Field

from tangl.core.fragment import ContentFragment

TextFragmentType = Literal['text', 'title', 'narrative', 'paragraph', 'dialog', 'choice']
TextContentFormatType = Literal['plain', 'html', 'markdown']

class TextFragment(ContentFragment, extra='allow'):
    fragment_type: TextFragmentType = Field("text", alias='type')
    content: str
    content_format: TextContentFormatType = Field("plain", alias='format')
