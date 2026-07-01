from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Iterator
from uuid import UUID

from pydantic import Field

from tangl.type_hints import Hash, Identifier

from .registry import HierarchicalGroup
from .singleton import Singleton
from .graph import Graph, GraphItem, Subgraph, Node, Edge, _ancestor_list
from .selector import Selector
from .behavior import BehaviorRegistry
from .template import TemplateRegistry, EntityTemplate, TemplateGroup
from .token import TokenCatalog


def _resolve_single_match[T](matches: list[T], description: str) -> T:
    if not matches:
        raise ValueError(f"{description} did not resolve")
    if len(matches) > 1:
        raise ValueError(f"{description} resolved ambiguously ({len(matches)} matches)")
    return matches[0]


def _attach_to_parent(parent: GraphItem, child: GraphItem) -> None:
    if isinstance(parent, (Subgraph, HierarchicalGroup)):
        parent.add_member(child)
        return
    raise TypeError(f"Parent {parent.__class__.__name__} does not support child membership")


class _TemplateIndex:
    """Per-materialization lookup cache for immutable template providers."""

    def __init__(self, templates: Iterable[EntityTemplate]) -> None:
        self.templates = list(templates)
        self.by_identifier: dict[Identifier, list[EntityTemplate]] = defaultdict(list)
        self.hash_by_uid: dict[UUID, Hash] = {}
        self.parent_by_child_uid: dict[UUID, TemplateGroup] = {}
        self.materialized_by_hash: dict[Hash, list[GraphItem]] = defaultdict(list)

        for templ in self.templates:
            templ_hash = templ.content_hash()
            self.hash_by_uid[templ.uid] = templ_hash
            self._index_identifier(templ_hash, templ)
            for identifier in templ.get_identifiers():
                self._index_identifier(identifier, templ)

        for templ in self.templates:
            if isinstance(templ, TemplateGroup):
                for member_id in templ.member_ids:
                    self.parent_by_child_uid.setdefault(member_id, templ)

    def _index_identifier(self, identifier: Identifier, templ: EntityTemplate) -> None:
        matches = self.by_identifier[identifier]
        if templ not in matches:
            matches.append(templ)

    def template_hash(self, templ: EntityTemplate) -> Hash:
        return self.hash_by_uid[templ.uid]

    def parent_template(self, templ: EntityTemplate) -> TemplateGroup | None:
        return self.parent_by_child_uid.get(templ.uid)

    def template_depth(self, templ: EntityTemplate) -> int:
        depth = 0
        seen: set[UUID] = set()
        parent = self.parent_template(templ)
        while parent is not None:
            if parent.uid in seen:
                raise ValueError(f"template hierarchy cycle at {parent.get_label()!r}")
            seen.add(parent.uid)
            depth += 1
            parent = self.parent_template(parent)
        return depth

    def graph_groups(self) -> list[TemplateGroup]:
        return sorted(
            (
                templ
                for templ in self.templates
                if isinstance(templ, TemplateGroup) and templ.has_payload_kind(GraphItem)
            ),
            key=self.template_depth,
        )

    def node_templates(self) -> Iterator[EntityTemplate]:
        return (
            templ
            for templ in self.templates
            if not isinstance(templ, TemplateGroup) and templ.has_kind(Node)
        )

    def edge_templates(self) -> Iterator[EntityTemplate]:
        return (templ for templ in self.templates if templ.has_kind(Edge))

    def remember_materialized(self, templ: EntityTemplate, item: GraphItem) -> None:
        self.materialized_by_hash[self.template_hash(templ)].append(item)

    def parent_graph_item(self, templ: EntityTemplate) -> GraphItem | None:
        parent = self.parent_template(templ)
        if parent is None:
            return None
        matches = self.materialized_by_hash.get(self.template_hash(parent), [])
        if not matches:
            return None
        return _resolve_single_match(
            matches,
            f"parent graph item for template {parent.get_label()!r}",
        )

    def resolve_template(
        self,
        *,
        identifier: Identifier,
        kind: type[GraphItem],
        description: str,
    ) -> EntityTemplate:
        return _resolve_single_match(
            [
                templ
                for templ in self.by_identifier.get(identifier, [])
                if templ.has_kind(kind)
            ],
            description,
        )

    def resolve_materialized_node(
        self,
        *,
        templ: EntityTemplate,
        description: str,
    ) -> Node:
        return _resolve_single_match(
            [
                item
                for item in self.materialized_by_hash[self.template_hash(templ)]
                if isinstance(item, Node)
            ],
            description,
        )


class GraphFactory(Singleton):
    """GraphFactory(label: str)

    Shape and behavior authority for a graph.

    Why
    ----
    ``GraphFactory`` centralizes the minimal core contract for eager topology
    materialization: create containers, create nodes, then wire edges against an
    already-resolved template bundle. It is a singleton by design so graphs can
    persist a factory reference by ``kind`` and ``label``, then recover the same
    behavior authority after structuring.

    This explicit graph/factory round-trip wrapper is the core analogue of the
    current ``StoryGraph.world`` persistence shim. It exists until core gains
    generic recursive handling for entity-shaped fields during structuring.

    Key Features
    ------------
    * Acts as the shape and behavior authority for a materialized graph.
    * Exposes deterministic eager materialization through
      :meth:`materialize_graph`.
    * Preserves authority identity across graph persistence through singleton
      structuring rules.

    API
    ---
    - :meth:`materialize_graph` expands already-resolved template topology.
    - :meth:`get_authorities` exposes bound behavior registries.
    - :meth:`get_entry_cursor` finds the shallowest entry-like graph item.

    Notes
    -----
    ``GraphFactory`` is not a resolver and not yet a story materializer
    replacement. Story-layer authorities may subclass it later; ``World`` is an
    expected future candidate.
    """

    dispatch: BehaviorRegistry = Field(default_factory=BehaviorRegistry)

    token_types: list[type[Singleton]] = Field(default_factory=list)
    template_types: list[type[GraphItem]] = Field(default_factory=list)
    graph_type: type[Graph] = Graph

    templates: TemplateRegistry = Field(default_factory=TemplateRegistry)
    default_entry_ref: str = "start"

    def get_authorities(self) -> list[BehaviorRegistry]:
        return [self.dispatch]

    def get_template_scope_groups(
        self,
        *,
        caller: GraphItem | None = None,
        graph: Graph | None = None,
    ) -> list[TemplateRegistry]:
        """Return the template registries authoritative for factory-built graphs."""
        _ = caller, graph
        return [self.templates]

    def get_entry_cursor(self, graph: Graph) -> GraphItem | None:
        s = Selector.chain_or(
            Selector(has_identifier=self.default_entry_ref),
            Selector(has_tags={self.default_entry_ref}),
        )
        return graph.find_one(s, sort_key=lambda x: len(_ancestor_list(x)))

    @property
    def _kind_map(self) -> dict[str, type[GraphItem]]:
        return {
            kind.__name__: kind for kind in (
                *self.template_types,
                *self.token_types,
                self.graph_type)
        }

    def _dereference_kind(self, data: dict, **kwargs):
        if 'kind' in data and data['kind'] in self._kind_map:
            data['kind'] = self._kind_map.get(data['kind'])

    def _provide_templates(self, **kwargs) -> list[TemplateRegistry]:
        return [self.templates]

    def _provide_token_catalogs(self, **kwargs) -> list[TokenCatalog]:
        return [TokenCatalog(wst=cls) for cls in self.token_types]

    def _resolve_edge_ref(self, edge: Edge, field_name: str) -> object:
        if not hasattr(edge, field_name):
            raise TypeError(
                f"Edge {edge.__class__.__name__} must define {field_name} "
                "for GraphFactory materialization"
            )
        value = getattr(edge, field_name)
        if value in (None, ""):
            raise ValueError(f"Edge {edge.get_label()!r} is missing {field_name}")
        return value

    def _resolve_predecessor(
        self,
        *,
        edge: Edge,
        template_index: _TemplateIndex,
    ) -> Node:
        predecessor_ref = self._resolve_edge_ref(edge, "predecessor_ref")
        ref_templ = template_index.resolve_template(
            identifier=predecessor_ref,
            kind=Node,
            description=(
                f"predecessor template {predecessor_ref!r} "
                f"for edge {edge.get_label()!r}"
            ),
        )
        return template_index.resolve_materialized_node(
            templ=ref_templ,
            description=f"materialized predecessor for edge {edge.get_label()!r}",
        )

    def _resolve_successor(
        self,
        *,
        edge: Edge,
        predecessor: Node,
        graph: Graph,
    ) -> Node:
        successor_ref = self._resolve_edge_ref(edge, "successor_ref")
        selector = Selector.chain_or(
            Selector(has_identifier=successor_ref),
            Selector(has_path=successor_ref),
        )
        candidates = list(graph.find_nodes(selector))
        if not candidates:
            raise ValueError(
                f"successor {successor_ref!r} for edge {edge.get_label()!r} did not resolve"
            )

        ranked = sorted(candidates, key=lambda node: graph.path_dist(predecessor, node))
        if len(ranked) > 1:
            best = graph.path_dist(predecessor, ranked[0])
            next_best = graph.path_dist(predecessor, ranked[1])
            if best == next_best:
                raise ValueError(
                    f"successor {successor_ref!r} for edge {edge.get_label()!r} "
                    "resolved ambiguously"
                )
        return ranked[0]

    def materialize_graph(
        self,
        graph: Graph | None = None,
        *,
        template_groups: Iterable[object] | None = None,
        **kwargs,
    ) -> Graph:
        """Materialize a graph from already-resolved template topology.

        Assumptions
        -----------
        - all template payloads already have the correct concrete kind;
        - container membership is already encoded in the template hierarchy;
        - edge refs are already canonicalized for deterministic lookup;
        - any ``template_groups`` override provides ``find_all`` / ``find_one``
          over an already-resolved template subset;
        - this method does not infer scope, compile policy, or token provision.
        """
        if graph is None:
            graph = self.graph_type(**kwargs)
        graph.bind_factory(self)

        templ_regs = (
            list(template_groups)
            if template_groups is not None
            else self._provide_templates()
        )
        template_indexes = [
            (templs, _TemplateIndex(templs.find_all()))
            for templs in templ_regs
        ]

        for _templs, template_index in template_indexes:
            for templ in template_index.graph_groups():
                group: GraphItem = templ.materialize()
                graph.add(group)
                template_index.remember_materialized(templ, group)

                parent = template_index.parent_graph_item(templ)
                if parent:
                    _attach_to_parent(parent, group)

        for _templs, template_index in template_indexes:
            for templ in template_index.node_templates():
                node: Node = templ.materialize()
                graph.add(node)
                template_index.remember_materialized(templ, node)

                parent = template_index.parent_graph_item(templ)
                if parent:
                    _attach_to_parent(parent, node)

        for templs, template_index in template_indexes:
            for templ in template_index.edge_templates():
                edge: Edge = templ.materialize()
                predecessor = self._resolve_predecessor(
                    edge=edge,
                    template_index=template_index,
                )
                successor = self._resolve_successor(
                    edge=edge,
                    predecessor=predecessor,
                    graph=graph,
                )

                graph.add(edge)
                edge.set_predecessor(predecessor)
                edge.set_successor(successor)

        return graph
