from __future__ import annotations

from typing import Iterator, Type

from pydantic import Field

from .singleton import Singleton
from .graph import Graph, GraphItem, Subgraph, Node, Edge
from .selector import Selector
from .behavior import BehaviorRegistry
from .template import TemplateRegistry, EntityTemplate, TemplateGroup
from .token import TokenFactory


# pseudo-graph-item helpers for template hierarchy
def _parent_templ(templ: EntityTemplate) -> TemplateGroup | None:
    registry = getattr(templ, "registry", None)
    if registry is None:
        return None
    return registry.find_one(Selector(has_member=templ))


def _ancestor_templs(templ: EntityTemplate) -> Iterator[TemplateGroup]:
    parent = _parent_templ(templ)
    while parent:
        yield parent
        parent = _parent_templ(parent)


def _template_depth(templ: EntityTemplate) -> int:
    return len(list(_ancestor_templs(templ)))


def _resolve_single_match[T](matches: list[T], description: str) -> T:
    if not matches:
        raise ValueError(f"{description} did not resolve")
    if len(matches) > 1:
        raise ValueError(f"{description} resolved ambiguously ({len(matches)} matches)")
    return matches[0]


def _get_parent_by_templ(
    templ_hash: bytes,
    templs: TemplateRegistry,
    graph: Graph,
) -> Subgraph | None:
    ref_templ = _resolve_single_match(
        list(templs.find_all(Selector(has_identifier=templ_hash))),
        f"template {templ_hash!r}",
    )
    ref_templ_parent = _parent_templ(ref_templ)
    if ref_templ_parent is None:
        return None
    ref_templ_parent_hash = ref_templ_parent.content_hash()
    return _resolve_single_match(
        list(graph.find_subgraphs(Selector(templ_hash=ref_templ_parent_hash))),
        f"parent subgraph for template {ref_templ_parent.get_label()!r}",
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
    template_types: list[Type[GraphItem]] = Field(default_factory=list)
    graph_type: Type[Graph] = Graph

    templates: TemplateRegistry = Field(default_factory=TemplateRegistry)
    default_entry_ref: str = "start"

    def get_authorities(self) -> list[BehaviorRegistry]:
        return [self.dispatch]

    def get_entry_cursor(self, graph: Graph) -> GraphItem | None:
        # TODO: check only within a scope and this becomes reusable for
        # any container entry point.
        s = Selector.chain_or(
            Selector(has_identifier=self.default_entry_ref),
            Selector(has_tags={self.default_entry_ref}),
        )
        return graph.find_one(s, sort_key=lambda x: len(list(x.ancestors())))

    @property
    def _kind_map(self) -> dict[str, Type[GraphItem]]:
        return {
            kind.__name__: kind for kind in (
                *self.template_types,
                *self.token_types,
                self.graph_type)
        }

    # todo: needs 'HasBehaviors' for registering cls/inst behaviors
    # @dispatch.register(task="on_create", wants_caller=EntityTemplate)
    def _dereference_kind(self, data: dict, **kwargs):
        if 'kind' in data and data['kind'] in self._kind_map:
            data['kind'] = self._kind_map.get(data['kind'])

    # @dispatch.register(task="on_get_providers")
    def _provide_templates(self, **kwargs) -> list[TemplateRegistry]:
        return [self.templates]

    # @dispatch.register(task="on_get_providers")
    def _provide_token_catalogs(self, **kwargs) -> list[TokenFactory]:
        return [TokenFactory(wst=cls) for cls in self.token_types]

    # @dispatch.register(task="on_init", wants_caller=Graph)
    # def _materialize_graph(self, caller: Graph, mode = None, **kwargs):
    #     # Could do this, but probably ouroboros
    #     if mode == "eager":
    #         self.materialize_graph(graph=caller)

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
        templs: TemplateRegistry,
        graph: Graph,
    ) -> Node:
        predecessor_ref = self._resolve_edge_ref(edge, "predecessor_ref")
        ref_templ = _resolve_single_match(
            list(templs.find_all(Selector(has_kind=Node, has_identifier=predecessor_ref))),
            f"predecessor template {predecessor_ref!r} for edge {edge.get_label()!r}",
        )
        return _resolve_single_match(
            list(graph.find_nodes(Selector(templ_hash=ref_templ.content_hash()))),
            f"materialized predecessor for edge {edge.get_label()!r}",
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
        candidates = [node for node in graph.nodes if selector.matches(node)]
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

    def materialize_graph(self, graph: Graph | None = None, **kwargs) -> Graph:
        """Materialize a graph from already-resolved template topology.

        Assumptions
        -----------
        - all template payloads already have the correct concrete kind;
        - container membership is already encoded in the template hierarchy;
        - edge refs are already canonicalized for deterministic lookup;
        - this method does not infer scope, compile policy, or token provision.
        """
        if graph is None:
            graph = self.graph_type(**kwargs)
        bind_factory = getattr(graph, "bind_factory", None)
        if callable(bind_factory):
            bind_factory(self)
        else:
            graph.factory = self

        templ_regs = self._provide_templates()

        for templs in templ_regs:
            for templ in templs.find_all(
                Selector(has_kind=Subgraph),
                sort_key=_template_depth,
            ):
                group: Subgraph = templ.materialize()
                graph.add(group)

                parent = _get_parent_by_templ(group.templ_hash, templs, graph)
                if parent:
                    parent.add_member(group)

        for templs in templ_regs:
            for templ in templs.find_all(Selector(has_kind=Node)):
                node: Node = templ.materialize()
                graph.add(node)

                parent = _get_parent_by_templ(node.templ_hash, templs, graph)
                if parent:
                    parent.add_member(node)

        for templs in templ_regs:
            for templ in templs.find_all(Selector(has_kind=Edge)):
                edge: Edge = templ.materialize()
                predecessor = self._resolve_predecessor(edge=edge, templs=templs, graph=graph)
                successor = self._resolve_successor(
                    edge=edge,
                    predecessor=predecessor,
                    graph=graph,
                )

                graph.add(edge)
                edge.set_predecessor(predecessor)
                edge.set_successor(successor)

        return graph
