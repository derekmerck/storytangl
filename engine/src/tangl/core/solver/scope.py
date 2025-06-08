from __future__ import annotations
from typing import Optional, Iterator, Self, ClassVar
from uuid import UUID
from abc import ABC, abstractmethod

from pydantic import Field

from tangl.core.entity import Entity, Registry, Singleton, Node, Graph
from tangl.core.handler import HasContext, HandlerRegistry, BaseHandler


class ScopedEntityABC(ABC):

    @abstractmethod
    def get_scopes(self) -> Iterator[Self]:
        ...

    def is_within(self, other: Self) -> bool:
        return other in self.get_scopes()

    def governs_for(self, other: Entity) -> bool:
        if hasattr(other, "is_within"):
            return other.is_within(self)
        raise ValueError(f"{other!r} does not implement 'is_within'.")


class Affiliation(Singleton, ScopedEntityABC):
    """
    Represents an opt-in scope -- domains are immutable and don't care about
    what entities belong to them.  It's up to each entity to track relevant
    domains.
    """
    def get_scopes(self):
        yield self


class HasAffiliateScopes(Entity, ScopedEntityABC):
    affiliations: list[Affiliation] = Field(default_factory=list)
    # ordered most precise to least precise

    def get_scopes(self):
        for a in self.affiliations:
            yield a.get_scopes()


class HasAncestors(Node, ScopedEntityABC):
    """
    Represents a one-to-many hierarchical scope with parent-child relationships
    -- graphs and subgraphs _do_ care about which nodes/subgraphs belong to them.

    Parent is the conceptual anchor for a subgraph.  Purpose is to be able to
    inherit scope from parents, or use within scope as a predicate for children.

    The underlying shared graph is only used for dereferencing memberships,
    is-parent and is-within are _not_ explicit edges in the sense of structural
    edges, dependencies, blame, etc.

    For a registry of entities, this would be a Partition and require a reference
    to the containing registry in all accessors.  Using Graph here is just a
    syntactic convenience b/c generic registry items don't carry a reference
    to a single management container.
    """
    parent_id: Optional[UUID] = None
    # Either a node, or None if it is a partition on the graph itself

    @property
    def parent(self) -> Graph | Node:
        if self.parent_id is not None:
            return self.graph.get(self.parent_id)
        return self.graph

    @parent.setter
    def parent(self, value: None | Node) -> None:
        self.parent_id = value

    children_ids: list[UUID] = Field(default_factory=list)

    @property
    def children(self) -> Iterator[Node]:
        yield from [ self.graph.get(g) for g in self.children_ids ]

    def find_children(self, **criteria) -> Iterator[Entity]:
        for child in self.children:
            if child.matches(**criteria):
                yield child

    def add_child(self, node: Node) -> None:
        self.children_ids.append(node.id)

    @property
    def ancestors(self) -> Iterator[Self]:
        # nearest to farthest
        current = self
        while current is not None:
            yield current
            current = current.parent

    def get_scopes(self):
        return self.ancestors

    def subgraph_path(self) -> Iterator[Self]:
        """Get the full subgraph path from root to this subgraph"""
        return reversed(list(self.ancestors))

    PATH_SEP: ClassVar[str] = "/"

    @property
    def path(self) -> str:
        return self.PATH_SEP.join( [ str(s) for s in self.subgraph_path() ] )

Subgraph = HasAncestors

class HasScopes(HasAffiliateScopes, HasAncestors):

    def get_scopes(self):
        """
        Self
         ├─ Ancestor1
         │   └─ Ancestor2
         ├─ Self.affiliations
         ├─ Ancestor1.affiliations
         ├─ Ancestor2.affiliations
         └─ global_domains
        """
        seen = set()
        # 1. Self
        yield self;
        seen.add(id(self))
        # 2. Ancestors (nearest to farthest)
        for ancestor in getattr(self, "ancestors", []):
            if id(ancestor) not in seen:
                yield ancestor;
                seen.add(id(ancestor))
        # 3. Affiliations of self
        for aff in getattr(self, "affiliations", []):
            if id(aff) not in seen:
                yield aff;
                seen.add(id(aff))
        # 4. Affiliations of each ancestor, nearest first
        for ancestor in self.ancestors:
            for aff in getattr(ancestor, "affiliations", []):
                if id(aff) not in seen:
                    yield aff;
                    seen.add(id(aff))
        # 5. Globals
        if id(global_domain) not in seen:
            yield global_domain;
            seen.add(id(global_domain))
    # todo: need a way to convert a domain to a specific handler registry when using
    #       'chain_find_all' to collect handlers


class HasInstanceHandlers(Entity):
    """
    Subgraphs can declare class level handlers for different node types
    using the available registration methods.

    However, singleton affiliations need a per-instance registration and discovery
    pattern.
    """
    instance_handlers: dict[str, Registry] = Field(default_factory=dict)

    # decorator
    def register_instance_handler(self, registry_label: str, **kwargs):
        # todo: Instance handlers should not infer "has_cls" predicates,
        #       nodes with this domain in their scope should get the domain locals
        #       and providers
        if registry_label not in self.instance_handlers:
            self.instance_handlers[registry_label] = HandlerRegistry(label=registry_label)
        registry = self.instance_handlers.get(registry_label)  # type: HandlerRegistry
        return registry.register(instance_handler=True, **kwargs)

    def find_all_instance_handlers(self, registry_name: str, *args, **kwargs) -> Iterator[BaseHandler]:
        registry = self.instance_handlers.get(registry_name)
        if registry is not None:
            yield from registry.find_all(*args, **kwargs)

class ContextDomain(Affiliation, HasContext, HasInstanceHandlers):
    # will automatically provide its locals to any node via the class handler
    # can also add additional handlers by registering with "register_instance_handler"
    # and then declaring the domain affiliation in a "HasScopes" object.
    ...

global_domain = ContextDomain(label="global")

from tangl.info import __version__
@global_domain.register_instance_handler("gather_context", has_cls=HasContext)
def provide_version(self: ContextDomain, ctx):
    return {'tangl_version': __version__}

# todo: this is how it _should_ work, but it doesn't yet b/c handlers don't autodiscover
#       domains and chain them yet
MyScopedNode = type('MyScopedEntity', (HasContext, HasScopes, Entity), {} )
node = MyScopedNode(locals={"foo": "bar"}, affiliations=[global_domain])
print( node.gather_context() )
assert set(node.gather_context().keys()) == {'foo', 'tangl_version', 'self'}
