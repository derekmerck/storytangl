from typing import Optional, Literal

from pydantic import Field

from tangl.core.entity import Node, Graph  # req Graph for pydantic validation
from tangl.core.fragment import BaseFragment, PresentationHints, ControlFragment

class ContentFragment(BaseFragment):
    # red, output, linked within by red, without by yellow
    """
    ContentFragments are Nodes on the graph, they are connected to their
    originating structure or resource nodes by 'blame' edges for auditing.

    The journal layer of the graph is made up of ordered content fragments generated
    by structure nodes as they are traversed by the graph cursor.

    Edges between content fragments are implicit in sequence since the journal is
    strictly linear and monotonic in sequence.
    """
    fragment_type: Literal["content"] = Field("content", alias="type")

    # base features
    presentation_hints: Optional[PresentationHints] = Field(None, alias='hints')
