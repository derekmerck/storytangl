from typing import Optional, Literal

from pydantic import Field

from tangl.core import GraphItem, Graph  # req Graph for pydantic validation
from .content_fragment import ContentFragment
from .presentation_hints import PresentationHints

# todo: Name? TextFragment, JournalFragment, ContentFragment and base is BaseFragment?
class StyledFragment(ContentFragment, GraphItem):
    # red, output, linked within by red, without by yellow
    """
    - JournalFragments and InfoFragments are _content_ objects in the fragment stream
    - GroupFragments and UpdateFragments are _control_ objects in the fragment stream
    - KvFragments, MediaFragments, and DiscourseFragments are application-specific constructs
      that have their own special rules for how their content field is represented.

    The journal layer of the graph is made up of ordered content fragments generated
    by structure nodes as they are traversed by the graph cursor.

    JournalFragments are Nodes on the graph, they are connected to their
    originating structure or resource nodes by 'blame' edges for auditing.

    Edges between content fragments are implicit in sequence since the journal is
    strictly linear and monotonic in sequence.
    """
    fragment_type: Literal["content"] = Field("content", alias="type")

    # base features
    presentation_hints: Optional[PresentationHints] = Field(None, alias='hints')
