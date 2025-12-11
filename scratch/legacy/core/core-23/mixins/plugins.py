import inspect

from typing import Type, Optional, Mapping, TYPE_CHECKING
from collections import ChainMap
from logging import getLogger

from pydantic import BaseModel, Field, model_validator
from pluggy import PluginManager, HookspecMarker, HookimplMarker

from tangl.graph import Node, Graph, GraphFactory
from tangl.entity.mixins import NamespaceHandler, HasNamespace, RenderHandler, Renderable
from .traversable import Traversable, Edge

if TYPE_CHECKING:
    from tangl.media import MediaReference, MediaResource

logger = getLogger("tangl.plugins")

PLUGIN_LABEL = "graph"

hookspec = HookspecMarker(PLUGIN_LABEL)
hookimpl = HookimplMarker(PLUGIN_LABEL)

class GraphPluginSpec:

    @hookspec(firstresult=True)
    def on_new_node(self, node_cls: Type[Node], kwargs: dict) -> Type[Node]:
        """Called by factory when a new node is created. Returns new Node type."""

    @hookspec
    def on_init_node(self, node: Node):
        """Called during node initialization. Modifies instance in place."""

    @hookspec
    def on_get_node_ns(self, node: HasNamespace) -> Mapping:
        """Called by the NamespaceHandler. Returns mapping of local vars."""

    @hookspec
    def on_render_node(self, node: Renderable) -> Mapping:
        """Called by the RenderHandler _before_ passing templates to the jinja renderer"""

    @hookspec(firstresult=True)
    def on_enter_node(self, node: Traversable) -> Optional[Edge]:
        """Called by the TraversalHandler _before_ the GTH applies node effects and
        renders the journal update. If an edge is returned, the GTH will immediately
        follow the edge without processing the current node"""

    @hookspec(firstresult=True)
    def on_exit_node(self, node: Traversable) -> Optional[Edge]:
        """Called by the TraversalHandler _after_ the GTH applies node effects and
        renders the journal update.  If an edge is returned, the GTH will immediately
        follow the edge without waiting for a player choice "follow edge" instruction."""

    @hookspec
    def on_init_graph(self, graph: Graph):
        """Called during graph initialization. Modifies instance in place."""

    @hookspec
    def on_exit_graph(self, graph: Graph):
        """Called when reaching an 'end' leaf to finalize the result. Modifies instance in place."""

    @hookspec
    def on_get_traversal_status(self, graph: Graph) -> Mapping | list[Mapping]:
        """Called by the GraphTraversalHandler. Returns a mapping of kv pairs
        or a list of kv's with properties, e.g., [{key:abc,value:foo,{important=True}},{...}]"""

    @hookspec
    def on_init_factory(self, factory: GraphFactory):
        """Called during factory initialization. Modifies instance in place."""

    @hookspec(firstresult=True)
    def on_get_media_resource(self, node: 'MediaReference', kwargs: dict) -> Optional['MediaResource']:
        """Called by the MediaHandler when dereferencing a MediaReference into a MediaResource object.  By default, the `kwargs` parameter includes a 'forge_kwargs' and 'spec_overrides' dicts.  If a MediaResource is returned, it is used as is by the MediaHandler."""


class NoOpGraphPlugin:
    """
    Graph plugin hookimpl template
    """

    @hookimpl
    def on_new_node(self, node_cls: Type[Node], kwargs: dict) -> Type[Node]:
        return node_cls

    @hookimpl
    def on_init_node(self, node: Node):
        pass

    @hookimpl
    def on_get_node_ns(self, node: HasNamespace) -> Mapping:
        pass

    @hookimpl
    def on_render_node(self, node: Renderable) -> Mapping:
        pass

    @hookimpl
    def on_enter_node(self, node: Traversable) -> Optional[Edge]:
        pass

    @hookimpl
    def on_exit_node(self, node: Traversable) -> Optional[Edge]:
        pass

    @hookimpl
    def on_init_graph(self, graph: Graph):
        pass

    @hookimpl
    def on_exit_graph(self, graph: Graph):
        pass

    @hookimpl
    def on_get_traversal_status(self, graph: Graph) -> Mapping | list[Mapping]:
        pass

    @hookimpl
    def on_init_factory(self, factory: GraphFactory):
        pass

    @hookimpl
    def on_get_media_resource(self, node: 'MediaResource', kwargs: dict) -> 'MediaResource':
        pass


class PluginHandler:
    """
    Relay for plugin hook calls with result aggregation.
    """

    @staticmethod
    def on_new_node(pm: PluginManager, node_cls: Type[Node], **kwargs) -> Type[Node]:
        # this is marked firstresult, so no aggregation
        return pm.hook.on_new_node(node_cls=node_cls, kwargs=kwargs)  # type: Type[Node]

    @staticmethod
    def on_init_node(pm: PluginManager, node: Node):
        pm.hook.on_init_node(node=node)

    @staticmethod
    def on_get_namespace(pm: PluginManager, node: HasNamespace) -> Mapping:
        maps = pm.hook.on_get_node_ns(node=node)  # type: list[Mapping]
        return ChainMap(*maps)

    @staticmethod
    def on_render_node(pm: PluginManager, node: Renderable) -> Mapping:
        maps = pm.hook.on_render_node(node=node)  # type: list[Mapping]
        return ChainMap(*maps)

    @staticmethod
    def on_enter_node(pm: PluginManager, node: Traversable) -> Optional[Edge]:
        # this is marked firstresult, so no aggregation
        return pm.hook.on_enter_node(node=node)   # type: Edge

    @staticmethod
    def on_exit_node(pm: PluginManager, node: Traversable) -> Optional[Edge]:
        # this is marked firstresult, so no aggregation
        return pm.hook.on_exit_node(node=node)    # type: Edge

    @staticmethod
    def on_init_graph(pm: PluginManager, graph: Graph):
        pm.hook.on_init_graph(graph=graph)

    @staticmethod
    def on_exit_graph(pm: PluginManager, graph: Graph):
        pm.hook.on_exit_graph(graph=graph)

    @staticmethod
    def on_get_traversal_status(pm: PluginManager, graph: Graph) -> Mapping | list[Mapping]:
        # return this as is and let the service layer deal with it
        return pm.hook.on_get_traversal_status(graph=graph)

    @staticmethod
    def on_init_factory(pm: PluginManager, factory: GraphFactory):
        pm.hook.on_init_factory(factory=factory)

    @staticmethod
    def on_get_media_resource(pm: PluginManager,
                              media_ref: 'MediaReference',
                              forge_kwargs: dict = None,
                              spec_overrides: dict = None) -> 'MediaResource':
        kwargs = {
            'forge_kwargs': forge_kwargs,
            'spec_overrides': spec_overrides
        }
        return pm.hook.on_get_media_resource(node=media_ref, kwargs=kwargs)


class HasPluginManager(BaseModel):
    # This goes on a graph or singleton that actually holds a pm

    plugin_manager: PluginManager = Field( default_factory=lambda: PluginManager( PLUGIN_LABEL ))

    @model_validator(mode='after')
    def _register_hooks(self):
        self.pm.add_hookspecs(GraphPluginSpec)

    @property
    def pm(self):
        # r/o alias for plugin_manager
        return self.plugin_manager

    class Config:
        arbitrary_types_allowed = True

    def __init__(self,
                 plugins = None,
                 **kwargs):
        super().__init__(**kwargs)

        hooks_name = self.pm.register(NoOpGraphPlugin())
        logger.debug(f"registered default hooks {hooks_name}")

        if plugins:
            hooks_name = self.pm.register(plugins())
            logger.debug(f"registered passed hooks {hooks_name}")

        if isinstance(self, GraphFactory):
            PluginHandler.on_init_factory(self.pm, self)
        elif isinstance(self, Graph):
            PluginHandler.on_init_graph(self.pm, self)
        elif isinstance(self, Node):
            PluginHandler.on_init_node(self.pm, self)

    # The functions override functions in GraphFactory

    def _normalize_node_cls(self, node_cls: str | type[Node], **kwargs) -> type[Node]:
        # This function is called early in GraphFactory.create_graph to dereference
        # a string `node_cls` arg before new'ing.  This version inserts a plugin-lookup
        # to transform classes as well.
        if not node_cls:
            raise ValueError(f"No node_cls provided along with {kwargs}")
        if isinstance(node_cls, str):
            if new_node_cls := Node.get_subclass_by_name(node_cls):
                node_cls = new_node_cls
        if new_node_cls := PluginHandler.on_new_node(self.pm, node_cls=node_cls, kwargs=kwargs):
            node_cls = new_node_cls
        if not inspect.isclass(node_cls) or not issubclass(node_cls, Node):
            logger.warning(Node.get_all_subclasses())
            raise ValueError(f"Unable to determine node-type from {node_cls} {kwargs}")
        return node_cls

    def create_graph(self, graph_cls: Type[Graph] = None, **kwargs):
        if new_graph_cls := PluginHandler.on_new_node(self.pm, graph_cls=graph_cls, kwargs=kwargs):
            graph_cls = new_graph_cls
        return super().create_graph(graph_cls, **kwargs)  # invokes a class func


class UsesPluginManager:
    # This goes on a node or a graph with a reference pm
    @property
    def pm(self: Node) -> PluginManager:
        try:
            return self.graph.pm
        except AttributeError:
            try:
                return self.factory.pm
            except AttributeError:
                # logger.debug('No valid pm')
                pass

    def __init__(self, defer_init = False, **kwargs):
        super().__init__(**kwargs)
        if self.pm and not defer_init:
            if isinstance(self, GraphFactory):
                PluginHandler.on_init_factory(self.pm, self)
            elif isinstance(self, Graph):
                PluginHandler.on_init_graph(self.pm, self)
            elif isinstance(self, Node):
                PluginHandler.on_init_node(self.pm, self)

    # @NamespaceHandler.strategy
    # def _include_plugin_ns(self: HasNamespace):
    #     if self.pm:
    #         PluginHandler.on_get_node_ns(self.pm, self)

    def render(self: Renderable):
        # This is not a strategy, it replaces the render func
        if not isinstance(self, Renderable):
            raise RuntimeError("Invoking render on non-renderable type")
        if self.pm:
            if x := self.pm.hook.on_render_node(self):
                return x
        return RenderHandler.render(self)
