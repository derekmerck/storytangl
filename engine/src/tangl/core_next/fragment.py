from typing import Any, Literal

from .node import Node

class ContentFragment(Node):
    fragment_type: Literal['content'] = 'content'
    content_format: Literal['text'] = 'text'
    content: Any = str
