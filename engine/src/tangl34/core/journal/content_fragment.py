from typing import Literal, Any

from ..entity import Entity

FragmentKind = Literal['content', 'resource', 'control']
ContentKind = Literal['text', 'uri', 'data']

class ContentFragment(Entity):
    fragment_kind: FragmentKind = 'content'
    content: Any = None
    content_kind: ContentKind = 'text'
