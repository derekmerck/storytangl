from typing import Literal, Optional

from ...type_hints import Context
from ...structure import Node, Edge, Graph

class Choice(Edge):
    trigger: Optional[Literal["before", "after"]] = None

# Check for pre-req and post-req structure
def requires_choice(when: Literal["before", "after"], caller: Node, graph: Graph, ctx: Context) -> Optional[Edge]:

    for x in caller.edges(graph, trigger=when):  # should throw out anything with no trigger field
        if x.satisfied(ctx=ctx):  # ungated
            return x  # short circuit and redirect cursor
            # todo: need to indicate possible return
