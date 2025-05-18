from __future__ import annotations
from uuid import UUID
from typing import Any, Generic, Optional, TypeVar, Self, Literal, Mapping, ClassVar, Union

from pydantic import BaseModel, Field

ContextView = Mapping[str, Any]
Identifier = UUID | str

class Gated(Entity):
    def satisfied(self, ctx: ContextView) -> bool: ...

class HasReqsM(Gated, Entity):
    requirements: list[Requirement] = Field(default_factory=list)
    def satisfied(self, ctx: ContextView) -> bool:
        return all(r.satisfied_by is not None for r in self.requirements) and super().satisfied(ctx)



class EffectHandler(Service):

    def apply_effect(self, effect, ctx):
        ...

    def apply_effects(self, node: Node, ctx: ContextView) -> Optional[Requirement]:
        for x in Node.effects:
            if x.satisfied(ctx):  # ungated
                self.apply_effect(x, ctx)

class ContentHandler(Service):

    def generate_fragments(self, node, journal, ctx: ContextView) -> Optional[list["Fragment"]]:
        res = []
        for render_source in node.render_source:
            if render_source.satisfied(ctx):
                for render_target in journal.render_target:  # journal may include html, media, etc.
                    res.append( self.render_content(render_source, render_target, ctx) )

    def update_journal(self, journal, fragments, bookmark):
        # Save linearized content
        ...

    def get_journal_entry(self, journal, which):
        # Return content for client
        ...

# --------------- Main Loop -----------------

