from typing import Literal, Optional

from ...type_hints import StringMap
from ...structure import Node, Edge, Graph

from .requirement import Requirement

class ChoiceRequirement(Requirement):
    # Links a _path_ to a structure node
    trigger: Optional[Literal["before", "after"]] = None

# Check for pre-req and post-req structure
def requires_choice(when: Literal["before", "after"], caller: Node, graph: Graph, ctx: StringMap) -> Optional[Edge]:

    for x in caller.edges(graph, trigger=when):  # should throw out anything with no trigger field
        if x.is_satisfied(ctx=ctx):  # ungated
            return x  # short circuit and redirect cursor
            # todo: need to indicate possible jump and return
