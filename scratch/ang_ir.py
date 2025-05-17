from __future__ import annotations
from uuid import UUID
from typing import Any, Generic, Optional, TypeVar, Self, Literal, Mapping, ClassVar, Union

from pydantic import BaseModel, Field

ContextView = Mapping[str, Any]
Identifier = UUID | str

# --------------- Entities -----------------


# --------------- Graphs/Scopes -----------------


# --------------- Mixins -----------------

class Gated(Entity):
    def satisfied(self, ctx: ContextView) -> bool: ...

class HasReqsM(Gated, Entity):
    requirements: list[Requirement] = Field(default_factory=list)
    def satisfied(self, ctx: ContextView) -> bool:
        return all(r.satisfied_by is not None for r in self.requirements) and super().satisfied(ctx)

# --------------- Requirements -----------------

class Requirement(Entity):
    req_criteria: dict[str, Any] = Field(default_factory=dict)
    satisfied_by: Optional[Link] = None
    obligation: Literal["find_or_create", "find_only", "create_only"] = "find_or_create"
    # find or create will try to find first and then build, requester will be gated if provision cannot be created
    # find only will _not_ try to build, requester will be gated if provision is un-findable
    # create only will always try to create a provision if the req is unsatisfied
    # builder is for "soft reqs" that can be waived by an inline resource
    builder: Optional[Provider] = None

    def find_match(self): ...
    def find_match_builder(self): ...

class StructureRequirement(Requirement):
    # Links a _path_ to a structure node
    phase: Optional[Literal["before", "after"]] = None

# --------------- Requirements -----------------

class Provision(Link):
    # Link that is assigned to a concept req once it is satisfied
    # It is always added to the recruiter's context by the req name
    req: Requirement

class Path(Provision):
    # Link that is assigned to a structure req once it is satisfied
    # It is always added to the requirement's transition table by the req name
    req: StructureRequirement
    @property
    def phase(self) -> Optional[Literal["before", "after"]]:
        return self.req.phase

class Provider(Entity):
    # ProvisionFinder takes a _graph_ and finds a matching node/entity/link within scope
    def provides_match(self, **criteria: Any) -> bool:
        return self._find_match(**criteria) is not None
    def get_match(self, **criteria: Any) -> Provider: ...

class FindProvider(Provider):
    # Find provider within scope-range
    def _find_match(self, scopes, **criteria: Any) -> Provider: ...
    def get_match(self, scopes, **criteria: Any) -> Provider:
        return self._find_match(**criteria)

class IndirectProvider(Provider):
    # Find template within registry
    templates: EntityRegistry[Provider]

    def _find_match(self, **criteria: Any) -> Provider:
        return next(*self.templates.find(**criteria))

    def get_match(self, **criteria: Any) -> Provider:
        template = self._find_template(**criteria)
        return template.build(**criteria)


# --------------- Service Handlers -----------------

Service = Entity

class ContextHandler(Service):

    def gather_context(self, scopes) -> ContextView: ...

class ScopeHandler(Entity):

    def gather_scopes(self, node: Node) -> 'ScopeView': ...

class Resolver(Service):

    def resolve_requirement(self, req: Requirement, scopes, ctx) -> Optional[Requirement]:
        # try to find a provider else find an indirect provider and create for each
        # Update context with any new provisions
        ...

class ChoiceHandler(Service):

    # Pre-req structure
    def check_before_paths(self, node: Node, ctx: ContextView) -> Optional[Link]:
        for x in Node.find(*node.links, cls=Path, phase="before"):
            if x.satisfied(ctx):  # ungated
                return x  # short circuit and redirect cursor, need to indicate possible return

    # Post-req structure
    def check_after_paths(self, node: Node, ctx: ContextView) -> Optional[Link]:
        for x in Node.find(*node.links, cls=Path, phase="after"):
            if x.satisfied(ctx):  # ungated
                return x  # short circuit and redirect cursor


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

class CursorDriver(Service):

    domain: Domain
    graph: Graph
    journal: "Journal"

    def update_cursor(self, choice: Link, bookmarks) -> Optional[Link]:

        node = choice.dst

        # 1. Get the scoped context view
        scopes = ScopeHandler.gather_scopes(node)
        ctx = ContextHandler.gather_context(scopes)

        # 2. Expand resolution horizon
        for requirement in node.requirements:
            Resolver.resolve(requirement, scopes, ctx)

        # 3. Redirection
        if next_link := ChoiceHandler.check_before_paths(node, ctx)
            return next_link

        # 4. Apply effects
        EffectHandler.apply_effects(node, ctx)

        # 5. Generate content
        fragments = ContentHandler.generate_fragments(scopes, ctx)
        # Setting, current action and impact, images, choices
        ContextHandler.update_journal(self.journal, fragments, bookmarks)

        # 6. Auto-continue
        if next_link := ChoiceHandler.check_after_paths(node, ctx):
            return next_link

        # Block on user input



