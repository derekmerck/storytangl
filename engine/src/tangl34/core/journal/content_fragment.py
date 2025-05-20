from typing import Literal, Any, Optional

from ..entity import Entity

class ContentFragment(Entity):
    """
    Minimal content fragment—just the fundamental unit for journal/log output.
    Extended elsewhere.
    """
    fragment_type: str = "content"  # e.g., 'text', 'choice', 'media'
    content: Any
    sequence: Optional[int] = None
