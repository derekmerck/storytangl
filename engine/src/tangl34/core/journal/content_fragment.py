from typing import Literal, Any

from ..entity import Entity

FragmentKind = Literal['content', 'resource', 'control']
ContentEncoding = Literal['text', 'binary']

class ContentFragment(Entity):
    fragment_kind: FragmentKind = 'content'
    content: Any = None
    encoding: ContentEncoding = 'text'
    mime_type: str = 'text/plain'
