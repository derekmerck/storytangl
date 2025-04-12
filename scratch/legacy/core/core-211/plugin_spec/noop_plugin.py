from __future__ import annotations
from typing import Type, Any, TYPE_CHECKING, TypeVar, Mapping, Optional
import logging

from pluggy import HookimplMarker

from tangl.entity import EntityType, BaseJournalItem
from tangl.entity.mixins import HasNamespace, Renderable
from tangl.graph import Node, Graph, GraphFactory
from tangl.utils.response_models import KVList
from .plugin_spec import PLUGIN_LABEL

if TYPE_CHECKING:
    from tangl.media import MediaNode
    from tangl.graph.mixins import Associating, TraversableNode, Edge, TraversableGraph

ServiceResponse = TypeVar("ServiceResponse", BaseJournalItem, KVList)

logger = logging.getLogger("tangl.plugins")

hookimpl = HookimplMarker(PLUGIN_LABEL)

class NoOpGraphImpl:
    """
    Graph plugin hookimpl template
    """

    # entity hooks

    @hookimpl
    def on_new_entity(self, obj_cls: Type[Node], data: dict) -> Type[Node]:
        return obj_cls

    @hookimpl
    def on_get_namespace(self, entity: HasNamespace) -> Mapping:
        pass

    @hookimpl
    def on_render(self, entity: Renderable) -> Mapping:
        pass

    # graph/node hooks

    @hookimpl
    def on_init_node(self, node: Node):
        pass

    @hookimpl
    def on_associate_with(self, node: Associating, other: Associating, as_parent: bool):
        pass

    @hookimpl
    def on_disassociate_from(self, node: Associating, other: Associating):
        pass

    @hookimpl
    def on_enter_node(self, node: TraversableNode, with_edge: Edge) -> Optional[Edge]:
        pass

    @hookimpl
    def on_exit_node(self, node: TraversableNode, with_edge: Edge) -> Optional[Edge]:
        pass

    @hookimpl
    def on_init_graph(self, graph: TraversableGraph):
        pass

    @hookimpl
    def on_enter_graph(self, graph: TraversableGraph):
        logger.debug(f"calling on enter graph")
        pass

    @hookimpl
    def on_exit_graph(self, graph: TraversableGraph):
        pass

    @hookimpl
    def on_get_traversal_status(self, graph: TraversableGraph) -> Mapping | list[Mapping]:
        pass

    # other hooks

    @hookimpl
    def on_init_factory(self, factory: GraphFactory):
        pass

    @hookimpl
    def on_prepare_media(self, node: MediaNode, forge_kwargs: dict, spec_overrides: dict) -> Any:
        pass

    @hookimpl
    def on_handle_response(self, response: ServiceResponse) -> Any:
        pass
