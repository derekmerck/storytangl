from typing import Optional, Any
from enum import Enum

import yaml
from pydantic import ConfigDict

from tangl.core.entity import Node, Graph  # Must import graph to define Node subclasses


class JournalFragment(Node):
    # red, output, linked within by red, without by yellow
    """
    Minimal content fragment, fundamental unit for trace processes journal/log
    output.  Extended elsewhere.

    Fragments may be connected to their originating structure or resource nodes
    by 'blame' edges if they are part of the same graph.

    Edges between journal items are implicit in sequence since the journal is strictly
    linear and monotonic in sequence.
    """
    # fragments are immutable once created
    model_config = ConfigDict(frozen=True)

    content_type: Optional[str|Enum] = None  # intent for content, e.g., 'text', 'choice', 'media'
    content: Any
    sequence: Optional[int] = None
    # mime-type is added in the service layer, when the fragment is serialized into a dto.

    def __str__(self):
        data = self.model_dump()
        s = yaml.dump(data, default_flow_style=False)
        return s
