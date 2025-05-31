from __future__ import annotations
from typing import Optional, Protocol, Any, Literal, Self, Callable, Iterator, ClassVar, TypeVar, Generic
from uuid import UUID

StringMap = dict[str, Any]
Scope = dict

from tangl.core.entity import Entity, Node, Edge, Graph
from tangl.core.handler import BaseHandler, HandlerRegistry, AvailabilityHandler, ContextHandler, EffectHandler

#### GRAPH VIEWS ####
    
class Journal(Protocol):
    def add_entry(self, fragments: list[ContentNode], bookmark: str = None): ...


#### NODES ####

class StructureNode(Node):
    ...

class ResourceNode(Node):
    ...

class ContentNode(Node):
    ...


##### EDGES ####

# open dependencies on the frontier will be provisioned by the resolver
class DependencyEdge(Edge):   # open dest
    dest_predicate: ...
    dest_criteria: ...

# all open requirements will be tested by the resolver against the frontier
class RequirementEdge(Edge):  # open source
    source_predicate: ...
    source_criteria: ...
    
When = Literal["before", "after"]
    
class ChoiceEdge(Edge):
    # Links structure nodes
    choice_trigger: When = "before"
    ...


#### HANDLERS ####

class ProvisionHandler(HandlerRegistry):

    registry: ClassVar[HandlerRegistry[Self]] = HandlerRegistry()

    def get_provider_for(self, dependency: DependencyEdge, *scopes, ctx: StringMap) -> bool: ...

    @classmethod
    def provision_dependency(cls, dependency: DependencyEdge, *scopes, ctx: StringMap) -> Node:
        for h in cls.registry.gather_handlers(dependency, *scopes):
            if dependency.is_satisfied_by(h.get_provider_for(dependency, ctx=ctx)):
                return h.func(dependency, ctx)
                dependency.dest = node
                return node
        else:
            raise RuntimeError(f"Cannot satisfy dependency {dependency}")
    # return first

    @classmethod
    def provision_node(cls, node: Node, *scopes, ctx: StringMap):
        for dependency in node.edges("out", "dependency"):
            if not dependency.is_resolved():
                node = cls.provision_dependency(dependency, *scopes, ctx=ctx)
                dependency.dest = node  # todo: this should create an provides edge back

class RenderHandler(HandlerRegistry):

    @classmethod
    def render_content(cls, node: Node, ctx: StringMap) -> list[ContentNode]: ...
    # merge all


#### EXAMPLE ENTITIES ####

context_handler = HandlerRegistry(default_excute_all_strategy="gather")

class HasContext(Entity):

    def gather_context(self, scopes: list[Scope]=None) -> StringMap:
        return context_handler.chain(*scopes).execute_all(self, ctx=None)

class MyEntity(Entity):

    locals: StringMap = dict()

    @context_handler.register(priority=10)
    def _provide_locals(self, **kwargs):
        return self.locals

    @HandlerRegistry.mark_handler(kind="context", priority=10)
    def _provide_special_value(self, **kwargs):
        return {'value': 'foo'}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        context_handler.gather_marked_handlers(cls)



class ForwardResolver:

    graph: Graph
    cursor: Node
    journal: Journal
    scopes: list[Scope]

    def _check_choices(self, when: When, *, ctx: StringMap) -> Optional[Edge]:
        for choice in self.cursor.edges("out", "control"):
            if choice.is_resolved() and choice.control_trigger == when and not choice.is_gated(ctx=ctx):
                # Automatically advance frontier
                return choice

    def resolve_choice(self, edge: ChoiceEdge, *, bookmark: str = None):

        while edge is not None:
            edge = self.advance_cursor(edge, bookmark=bookmark)
            bookmark = None

    def advance_cursor(self, edge: ChoiceEdge, *, bookmark: str = None) -> Optional[ChoiceEdge]:

        # Validate step
        if not isinstance(edge, ChoiceEdge):
            raise RuntimeError(f"Cannot advance, {edge} is not a control edge")
        if edge.src is not self.cursor:
            raise RuntimeError(f"Cannot advance, {edge} is not on cursor")
        node = edge.dest
        ctx = ContextHandler.gather_context(node, *self.scopes)
        if node.is_gated(*self.scopes, ctx=ctx):
            raise RuntimeError(f"Cannot advance, {node} is unavailable")

        # Update cursor
        self.cursor = node

        # Resolve frontier edges
        ProvisionHandler.provision_node(node, ctx=ctx)
        # # Resolve requirements
        # # Adds edges with open source to the frontier
        # ProvisionHandler.link_requirements(node, ctx=ctx)

        # Check for auto-advance
        if (next_edge := self._check_choices("before", ctx=ctx)) is not None:
            return next_edge

        # Update context
        EffectHandler.apply_effects(self.cursor, self.graph, *self.scopes, ctx=ctx, when="before")

        # Generate trace content
        fragments = RenderHandler.render_content(self.cursor, self.graph, *self.scopes, ctx=ctx)
        self.journal.add_entry(fragments, bookmark=bookmark)

        EffectHandler.apply_effects( self.cursor, self.graph, *self.scopes, ctx=ctx, when="after")

        # Check for auto-advance
        if (next_edge := self._check_choices("after", ctx=ctx)) is not None:
            return next_edge
