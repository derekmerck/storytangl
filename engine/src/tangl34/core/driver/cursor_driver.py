from typing import Optional

from pydantic import BaseModel, Field

from ..structure import Graph, Node, Edge
from ..journal import HasJournal
from ..handlers import Scope, Renderable, HasContext, HasEffects
# from ..handlers.provision import resolve_requirements, requires_choice

# todo: remove stub functions for the prior handler api
def resolve_requirements(*args, **kwargs): return True
def requires_choice(*args, **kwargs): return None

class CursorDriver(BaseModel):
    cursor: Node    # Assumes scoped node
    graph: Graph    # Assumes scoped graph
    scopes: list[Scope] = Field(default_factory=list)  # additional scopes, e.g., domain, user
    journal: HasJournal

    def advance_cursor(self, choice: Edge, section_bookmark = None) -> Optional[Edge]:

        self.cursor = choice.dst(self.graph)

        # 1) CONTEXT
        ctx = HasContext.gather_context(self.cursor, self.graph, *self.scopes)

        # 2) BEFORE
        # Update structure and choices
        resolve_requirements(self.cursor, self.graph, *self.scopes, ctx=ctx)
        # Check for pre-req short circuit
        if edge := requires_choice("before", self.cursor, self.graph, ctx=ctx):
            return edge
        # Pre-update state
        HasEffects.apply_effects("before", self.cursor, self.graph, *self.scopes, ctx=ctx)

        # 3) RENDER
        # Setting, current action and impact, images, choices
        frags = Renderable.render_content(self.cursor, self.graph, *self.scopes, ctx=ctx)
        # Update journal
        if section_bookmark:
            self.journal.start_journal_section(section_bookmark)
        self.journal.add_journal_entry(frags)

        # 4) AFTER
        # Post-update state
        HasEffects.apply_effects("after", self.cursor, self.graph, *self.scopes, ctx=ctx)
        # Check for post-req short circuit
        if edge := requires_choice("after", self.cursor, self.graph, ctx=ctx):
            return edge

        # Block on user input