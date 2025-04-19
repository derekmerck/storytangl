# graphs can have layers of projection fragments organized into lists
# can use bookmarked list for this

# todo: this admits only ONE narrative thread, do we want to track branching
#       or multiple fragment layers?  This would require careful integration with
#       history.

import functools

from pydantic import Field

from tangl.utils.bookmarked_list import BookmarkedList
from tangl.core.graph import Graph
from tangl.core.fragment import ContentFragment

class HasLinearLayer(Graph):

    linear_layer: BookmarkedList[ContentFragment] = Field(default_factory=BookmarkedList[ContentFragment])
