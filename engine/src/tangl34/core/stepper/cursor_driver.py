from pydantic import BaseModel

from ..structure import Graph, Domain, Node, Edge
from ..journal import Journal
from ..services.gather import discover_scopes, gather_context
from ..services.provision import resolve_requirements
from ..services.choices import requires_choice
from ..services.render import render_fragments
from ..services.effects import apply_effects


class CursorDriver(BaseModel):
    domain: Domain
    graph: Graph
    cursor: Node
    journal: Journal

    def update_cursor(self, edge: Edge):

        self.cursor = edge.dst(self.graph)

        # 1) GATHER
        scopes = discover_scopes(self.cursor, self.graph, self.domain)
        ctx = gather_context(*scopes)

        # 2) BEFORE
        resolve_requirements(*scopes, ctx=ctx)  # update structure
        if edge := requires_choice("before", *scopes, ctx=ctx):
            return edge # short circuit
        apply_effects("before", *scopes, ctx=ctx)  # update state

        # 3) RENDER
        frags = render_fragments(*scopes, ctx=ctx)
        self.journal.extend(frags)  # update journal

        # 4) AFTER
        apply_effects("after", *scopes, ctx=ctx)  # update state
        if edge := requires_choice("after", *scopes, ctx=ctx):
            return edge  # short circuit
