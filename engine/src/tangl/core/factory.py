from typing import Type, Optional, Iterator
from pydantic import Field

from tangl.type_hints import Hash
from .entity import Entity
from .singleton import Singleton
from .graph import Graph, GraphItem, Subgraph, Node, Edge
from .selector import Selector
from .behavior import BehaviorRegistry
from .template import TemplateRegistry, EntityTemplate, TemplateGroup
from .token import TokenFactory


# pseudo-graph-item helpers for template hierarchy
def _parent_templ(templ: EntityTemplate) -> Optional[TemplateGroup]:
    return templ.registry.find_one(Selector(has_member=templ))


def _ancestor_templs(templ: EntityTemplate) -> Iterator[TemplateGroup]:
    parent = _parent_templ(templ)
    while parent:
        yield parent
        parent = _parent_templ(parent)


def _get_ancestors_by_templ(templ_hash: Hash,
                            templs: TemplateRegistry) -> list[TemplateGroup]:
    ref_templ = templs.find_one(Selector.from_id(templ_hash))
    return list(_ancestor_templs(ref_templ))


def _get_node_by_templ(templ_hash: Hash,
                       templs: TemplateRegistry,
                       graph: Graph) -> Optional[GraphItem]:
    # 1. find a template
    # 3. find the materialized node based on that template in the current graph
    ref_templ = templs.find_one(Selector.from_id(templ_hash))
    return graph.find_one(Selector.from_id(ref_templ.content_hash()))


def _get_parent_by_templ(templ_hash: Hash,
                         templs: TemplateRegistry,
                         graph: Graph) -> Optional[Subgraph]:
    # 1. find a template
    # 2. find that template's parent template group
    # 3. find the materialized container based on that template group
    #    in the current graph
    ref_templ = templs.find_one(Selector.from_id(templ_hash))
    ref_templ_parent = _parent_templ(ref_templ)
    if ref_templ_parent is None:
        return None
    ref_templ_parent_hash = ref_templ_parent.content_hash()
    return graph.find_one(Selector.from_id(ref_templ_parent_hash))


class GraphFactory(Singleton):
    # Shape and behavior authority for a graph
    #
    # Provides services:
    # - materialize_graph  (eager shape init)
    # - get_authorities    (behaviors)
    # - get_entry_cursor   (nearest entry-like object given scope)
    #
    # Provides dispatch hooks:
    # - domain specific Entity subclasses for creation
    # - domain specific templates and token catalog providers for planning

    dispatch: BehaviorRegistry = Field(default_factory=BehaviorRegistry)

    token_types: list[Singleton] = Field(default_factory=list)
    template_types: list[Type[GraphItem]] = Field(default_factory=list)
    graph_type: Type[Graph] = Graph

    templates: TemplateRegistry = Field(default_factory=TemplateRegistry)
    default_entry_ref: str = "start"

    def get_authorities(self) -> list[BehaviorRegistry]:
        return [ self.dispatch ]

    def get_entry_cursor(self, graph: Graph) -> GraphItem:
        # todo: check only within a scope and this becomes reusable for
        #       any container entry point
        s = Selector.chain_or(
            Selector(has_identifier=self.default_entry_ref),
            Selector(has_tags={self.default_entry_ref})
        )
        return graph.find_one(s, sort_key=lambda x: len(list(x.ancestors)))

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

    def materialize_graph(self, graph: Graph = None, **kwargs):
        # Simple EAGER default materialization
        #
        # This is not a resolver. It is strictly a deterministic expander for
        # already-resolved template topology.
        #
        # Assumptions:
        #  - all template payloads already have correct kind
        #  - edge templates have an unambiguous predecessor node template indicated
        #    by hash
        #  - does NOT use scope, container templates have unambiguous member templates
        #    indicated by hash
        #  - does NOT account for tokens, those are created and linked as needed

        if graph is None:
            graph = self.graph_type(**kwargs)
        graph.factory = self  # set self as the shape and behavior authority

        templ_regs = self._provide_templates()

        for templs in templ_regs:
            for templ in templs.find_all(
                    Selector.from_kind(Subgraph),
                    sort_key=lambda x: len(_get_ancestors_by_templ(x.templ_hash, templs))):
                # sort with fewest ancestors first (closest to root)
                group: Subgraph = templ.materialize()
                graph.add(group)

                parent: Subgraph | None = _get_parent_by_templ(group.templ_hash, templs, graph)
                if parent:
                    parent.add_member(group)

        for templs in templ_regs:
            for templ in templs.find_all(Selector.from_kind(Node)):
                # any order, all parent containers already created
                node: Node = templ.materialize()
                graph.add(node)

                parent: Subgraph | None = _get_parent_by_templ(node.templ_hash, templs, graph)
                if parent:
                    parent.add_member(node)

        for templs in templ_regs:
            for templ in templs.find_all(Selector.from_kind(Edge)):
                # any order, all predecessors already created
                edge = templ.materialize()
                graph.add(edge)

                # assumes predecessor_ref is set by compiler with templ_hash
                # as the anchor for the edge's scope
                predecessor = _get_node_by_templ(edge.predecessor_ref, templs, graph)
                if not predecessor:
                    raise ValueError(f"No predecessor found for {edge!r}")
                edge.set_predecessor(predecessor)

                # assume successor_ref is a label or path and we want the closest match
                successor = graph.find_one(Selector.from_id(edge.successor_ref), sort_key=lambda x: graph.path_dist(edge.predecessor, x))
                # todo: need graph.path_dist(a,b)
                if not successor:
                    raise ValueError(f"No successor found for {edge!r}")
                edge.set_successor(successor)
