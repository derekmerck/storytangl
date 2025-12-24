from __future__ import annotations
import logging
import warnings
from uuid import UUID
from typing import Optional, Iterator, Iterable, TYPE_CHECKING
import functools

from pydantic import Field, model_validator

from tangl.type_hints import Identifier, Tag
from tangl.utils.hashing import hashing_func
from tangl.core.entity import Entity, match_logger
from tangl.core.registry import Registry

match_logger.setLevel(logging.WARNING)

if TYPE_CHECKING:
    from .subgraph import Subgraph
    from .node import Node
    from .edge import Edge

class GraphItem(Entity):
    """
    GraphItem(graph: Graph)

    Base abstraction for graph elements that are self-aware of their container graph.

    Why
    ----
    Centralizes membership/parentage logic so :class:`Node`, :class:`Edge`, and
    :class:`Subgraph` behave consistently. Instances auto-register with their
    :attr:`graph` and expose ancestry utilities used throughout planning and scope.

    Key Features
    ------------
    * **Auto-registration** – post-init validator calls ``graph.add(self)``.
    * **Hierarchy helpers** – :meth:`parent`, :meth:`ancestors`, :meth:`root`, :meth:`path`.
    * **Stable identity** – :meth:`_id_hash` includes the graph uid when present.

    .. admonition::Auto-Registration
        If possible, GraphItems will automatically register with their
        parent Graph on instantiation since they are inert without graph
        context (cannot resolve relationships, query neighbors, etc.).
        GraphItems are bound to a single graph for their lifetime and
        should not be transferred between graphs.

        Use `graph.add(item)` only when you need to defer registration or
        explicitly document the attachment point.

    API
    ---
    - :attr:`graph` – back-reference to the owning :class:`Graph` (not serialized).
    - :meth:`parent` – nearest containing :class:`Subgraph` (cached).
    - :meth:`ancestors` – iterator of containing subgraphs (nearest → farthest).
    - :meth:`root` – top-most containing subgraph or ``None``.
    - :meth:`path` – dotted label path from root to self.
    - :meth:`_invalidate_parent_attr` – clear cached parent on re-parenting.
    """
    graph: Graph = Field(default=None, exclude=True)
    # graph is for local dereferencing only, do not serialize to prevent recursions
    # hold id only for peer graph items to prevent recursions, see edge

    @model_validator(mode='after')
    def _register_with_graph(self):
        if self.graph is not None:
            self.graph.add(self)
        return self

    # use cached-property and invalidate if re-parented
    @functools.cached_property
    def parent(self) -> Optional[Subgraph]:
        return next(self.graph.find_subgraphs(has_member=self), None)

    def _invalidate_parent_attr(self):
        # On reparent
        if hasattr(self, "parent"):
            delattr(self, "parent")

    def ancestors(self) -> Iterator[Subgraph]:
        current = self.parent
        while current:
            yield current
            current = current.parent

    def has_path(self, pattern: str) -> bool:
        from fnmatch import fnmatch
        match_logger.debug(f"fnmatch({self.path}, {pattern}) = {fnmatch(self.path, pattern)}")
        return fnmatch(self.path, pattern)

    def has_ancestor(self, ancestor: Subgraph) -> bool:
        return ancestor in self.ancestors()

    def has_ancestor_tags(self, *tags: Tag) -> bool:
        # Normalize args to set[Tag]
        if len(tags) == 1 and isinstance(tags[0], set):
            tags = tags[0]  # already a set of tags
        else:
            tags = set(tags)

        ancestors = [self] + list(self.ancestors())
        ancestor_tags = { t for a in ancestors for t in a.tags }
        match_logger.debug(f"Comparing query tags {tags} against {ancestor_tags}")
        return tags.issubset(ancestor_tags)

    def has_parent_label(self, parent_label: str) -> bool:
        # seems redundant
        return self.parent is not None and self.parent.label == parent_label

    def has_scope(self, scope: dict) -> bool:
        warnings.warn("`has_scope` is deprecated; prefer `matches(has_path, has_ancestor_tags)`.", DeprecationWarning, stacklevel=2)
        return self.matches(**scope)

    @property
    def root(self) -> Optional[Subgraph]:
        # return the most distant subgraph membership (top-most ancestor)
        last = None
        for anc in self.ancestors():
            last = anc
        return last

    # I don't _think_ this is an identifier, there _could_ be a block `scene1.foo` and an actor `scene1.foo`, although it would probably be confusing and a mistake.
    @property
    def path(self):
        # Include self in path
        reversed_ancestors = reversed([self] + list(self.ancestors()))
        return '.'.join([a.get_label() for a in reversed_ancestors])

    def _id_hash(self) -> bytes:
        # Include the graph id if assigned (should always be)
        if self.graph is not None:
            return hashing_func(self.uid, self.__class__, self.graph.uid)
        else:
            return super()._id_hash()


class Graph(Registry[GraphItem]):
    """
    Graph(data: dict[~uuid.UUID, GraphItem])

    Linked registry of :class:`GraphItem` objects (nodes, edges, subgraphs).

    Why
    ----
    Treats the whole topology as a searchable registry while providing typed
    helpers for construction and queries. Enforces link integrity so items always
    belong to the same graph.

    Key Features
    ------------
    * **Special adds** – :meth:`add_node`, :meth:`add_edge`, :meth:`add_subgraph`.
    * **Typed finds** – :meth:`find_nodes`, :meth:`find_edges`, :meth:`find_subgraphs`.
    * **Convenient get** – :meth:`get` by ``UUID`` or by ``label``/``path``.
    * **Integrity checks** – :meth:`_validate_linkable` before wiring edges/groups.

    API
    ---
    - :meth:`add` – attach any :class:`GraphItem` (sets ``item.graph`` then registers).
    - :meth:`add_node` – create/register a node.
    - :meth:`add_edge` – create/register an edge between items (accepts ``None`` endpoints).
    - :meth:`add_subgraph` – create/register a subgraph and populate members.
    - :meth:`find_nodes` / :meth:`find_edges` / :meth:`find_subgraphs` – filtered iterators.
    - :meth:`get` – lookup by id or by label/path.
    """

    # special adds
    def add(self, item: GraphItem) -> None:
        item.graph = self
        super().add(item)

    def add_node(self, *, obj_cls=None, **attrs) -> Node:
        from .node import Node
        obj_cls = obj_cls or Node
        n = obj_cls(**attrs)
        self.add(n)
        return n

    def add_edge(self, source: GraphItem, destination: GraphItem, *, obj_cls=None, **attrs) -> Edge:
        if source is not None:
            self._validate_linkable(source)
            source_id = source.uid
        else:
            source_id = None

        if destination is not None:
            self._validate_linkable(destination)
            destination_id = destination.uid
        else:
            destination_id = None

        from .edge import Edge
        obj_cls = obj_cls or Edge

        e = obj_cls(source_id=source_id, destination_id=destination_id, **attrs)
        self.add(e)
        return e

    def add_subgraph(self, *, obj_cls=None, members: Iterable[GraphItem] = None, **attrs) -> Subgraph:
        from .subgraph import Subgraph
        obj_cls = obj_cls or Subgraph
        sg = obj_cls(**attrs)
        self.add(sg)
        for item in members or ():
            sg.add_member(item)  # validates internally
        return sg

    # special finds
    def find_nodes(self, **criteria) -> Iterator[Node]:
        from .node import Node
        criteria.setdefault("is_instance", Node)
        return self.find_all(**criteria)

    @property
    def nodes(self) -> list[Node]:
        return list(self.find_nodes())

    def find_node(self, **criteria) -> Optional[Node]:
        return next(self.find_nodes(**criteria), None)

    def find_edges(self, **criteria) -> Iterator[Edge]:
        from .edge import Edge
        # find edges in = find_edges(destination=node)
        # find edges out = find_edges(source=node)
        criteria.setdefault("is_instance", Edge)
        return self.find_all(**criteria)

    @property
    def edges(self) -> list[Edge]:
        return list(self.find_edges())

    def find_edge(self, **criteria) -> Optional[Edge]:
        return next(self.find_edges(**criteria), None)

    def find_subgraphs(self, **criteria) -> Iterator[Subgraph]:
        from .subgraph import Subgraph
        criteria.setdefault("is_instance", Subgraph)
        return self.find_all(**criteria)

    @property
    def subgraphs(self) -> list[Subgraph]:
        return list(self.find_subgraphs())

    def find_subgraph(self, **criteria) -> Optional[Subgraph]:
        return next(self.find_subgraphs(**criteria), None)

    def get(self, key: Identifier):
        if isinstance(key, UUID):
            return super().get(key)
        elif isinstance(key, str):
            return self.find_one(label=key) or self.find_one(path=key)

    def _validate_linkable(self, item: GraphItem):
        if not isinstance(item, GraphItem):
            raise TypeError(f"Expected GraphItem, got {type(item)}")
        if item.graph != self:
            raise ValueError(f"Link item must belong to the same graph")
        if item.uid not in self.data:
            raise ValueError(f"Link item must be added to graph first")
        return True
