from __future__ import annotations
from typing import Type, Any, TYPE_CHECKING, TypeVar, Mapping, Optional, ClassVar
import logging

from pluggy import HookspecMarker, HookimplMarker
from tangl.entity import Entity, EntityType, BaseJournalItem
from tangl.entity.mixins import HasNamespace, Renderable
from tangl.graph import Node, Graph, GraphType, GraphFactory
from tangl.utils.response_models import KVList

if TYPE_CHECKING:
    from tangl.graph.mixins import Associating, TraversableNode, Edge, TraversableGraph
    from tangl.media import MediaNode

ServiceResponse = TypeVar("ServiceResponse", BaseJournalItem, KVList)

logger = logging.getLogger("tangl.plugins")

PLUGIN_LABEL = "graph"

hookspec = HookspecMarker(PLUGIN_LABEL)
hookimpl = HookimplMarker(PLUGIN_LABEL)

class GraphPluginSpec:

    # entity method hooks

    @hookspec(firstresult=True)
    def on_new_entity(self, obj_cls: Type[Entity], data: dict) -> Type[Entity]:
        """
        Called when a new entity like a World, Story, StoryNode is created.  Returns
        the new object class.
        This can be used to override a default object class with a world-specific
        subclass.
        """

    @hookspec
    def on_get_namespace(self, entity: HasNamespace) -> Mapping:
        """
        Called by the NamespaceHandler when a node namespace is evaluated.  Returns a
        mapping of variables that is merged onto the default namespace for the node.

        This generally gets called 3 times for a namespace: once for the StoryNode
        locals, once for the Story globals, and once for the World for branding and public
        properties."""

    @hookspec
    def on_render(self, entity: Renderable) -> Mapping:
        """
        Called by the RenderHandler when a node update is generated.  Returns a story
        update dict that is merged onto the default update dict for that class.
        Keys can be discarded by overwriting them with None values.
        """

    # graph method hooks

    @hookspec
    def on_init_node(self, node: Node):
        """
        Called when a node is initialized, execute custom initialization code
        such as dynamically creating additional story objects related to the node.
        Modifies in place.
        """

    @hookspec
    def on_associate_with(self, node: Associating, other: Node, as_parent: bool): ...

    @hookspec
    def on_disassociate_from(self, node: Associating, other: Node): ...

    @hookspec(firstresult=True)
    def on_enter_node(self, node: TraversableNode, with_edge: Edge) -> Optional[Edge]:
        """
        Called by the TraversalHandler when a node is entered.  Used to setup visit code
        and/or order a redirect.
        If a redirect Edge is returned, it followed immediately, skipping any further
        processing on the current node.
        """

    @hookspec(firstresult=True)
    def on_exit_node(self, node: TraversableNode, with_edge: Edge) -> Optional[Edge]:
        """Called by the TraversalHandler after the node is processed and an update is
        generated.  Used to clean up after visit code and look for continuations.
        If a continues Edge is returned, it is followed immediately, without waiting for
        a player choice or a further "follow edge" instruction."""

    def on_init_graph(self, graph: GraphType):
        """
        Called when a story is initialized, can be used to initialize global state.
        Modifies in place.
        """

    @hookspec(firstresult=True)
    def on_enter_graph(self, graph: TraversableGraph):
        """Called immediately after story initialization to set the entry bookmark
        (cursor) and enter the first node.  Modifies in place."""

    @hookspec(firstresult=True)
    def on_exit_graph(self, graph: TraversableGraph):
        """Called when reaching an 'end' leaf to finalize the story. Can be used to
        update user metadata , like completed stories or total amount of x over all
        stories.  Modifies in place.
        """

    @hookspec
    def on_get_traversal_status(self, graph: Graph) -> Mapping | KVList:
        """Called by the GraphTraversalHandler. Returns a mapping of kv pairs
        or a list of kv's with properties, e.g., [{key:abc,value:foo,{important=True}},{...}]"""

    # other hooks

    @hookspec
    def on_init_factory(self, factory: GraphFactory):
        """Called during factory (World) initialization. Modifies instance in place."""

    @hookspec(firstresult=True)
    def on_prepare_media(self, node: MediaNode, forge_kwargs: dict, spec_overrides: dict) -> Any:
        """
        Called by the MediaHandler when preparing a MediaNode node to generate a
        media resource.

        May modify in place, or return a new MediaNode or a media object.  If a new
        media resource is returned, the handler will register it and update the media
        node's RIT.

        :important: `forge_kwargs` and `spec_overrides` are passed as dicts in the
                    hookimpl, _not_ as `**kwargs`.  Spread them in the plugin function
                    if necessary.
         """

    @hookspec
    def on_handle_response(self, response: ServiceResponse) -> ServiceResponse:
        """
        Called by the ServiceManager to evaluate media resources and format text.

        May modify in place or return a new ServiceResponse.  If a new response is
        returned, it will supersede the original.
        """
