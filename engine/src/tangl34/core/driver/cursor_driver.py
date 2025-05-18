from pydantic import BaseModel, Field, field_validator

from ..structure import Graph, Domain, Node, Edge
from ..journal import Journal
from ..handlers import Scope
from ..handlers.gather import gather_context, discover_scopes
from ..handlers.provision import resolve_requirements, requires_choice
from ..handlers.render import render_fragments
from ..handlers.effects import apply_effects


class CursorDriver(BaseModel):
    cursor: Node    # Assumes scoped node
    graph: Graph    # Assumes scoped graph
    scopes: list[Scope] = Field(default_factory=list)  # additional scopes, e.g., domain, user
    journal: Journal

    def advance_cursor(self, choice: Edge, bookmarks = None):

        self.cursor = choice.dst(self.graph)

        # 1) GATHER
        scopes = discover_scopes(self.cursor, self.graph, *self.scopes)
        ctx = gather_context(*scopes)

        # 2) BEFORE
        resolve_requirements(self.cursor, self.graph, *scopes, ctx=ctx)  # update structure and choices
        if edge := requires_choice("before", self.cursor, self.graph, ctx=ctx):
            return edge # pre-req short circuit
        apply_effects("before", self.cursor,*scopes, ctx=ctx)  # update state

        # 3) RENDER
        frags = render_fragments(self.cursor, *scopes, ctx=ctx)
        # Setting, current action and impact, images, choices
        self.journal.extend(frags)  # update journal, todo: include bookmarks

        # 4) AFTER
        apply_effects("after", self.cursor, *scopes, ctx=ctx)  # update state
        if edge := requires_choice("after", self.cursor, self.graph, ctx=ctx):
            return edge  # post-req short circuit

        # Block on user input
