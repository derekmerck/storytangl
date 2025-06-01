from typing import Any, Optional

from tangl.core.entity import Entity

class ContentFragment(Entity):
    """
    Minimal content fragment, fundamental unit for journal/log output.
    Extended elsewhere.

    Fragments may be connected to their originating structure or resource nodes
    by 'blame' edges if they are part of the same graph.
    """
    fragment_type: str = "content"  # e.g., 'text', 'choice', 'media'
    content: Any
    sequence: Optional[int] = None
