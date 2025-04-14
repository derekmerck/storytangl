from __future__ import annotations
from typing import Type, ClassVar, Any, TYPE_CHECKING, TypeVar, Mapping, Optional, Callable
from collections import ChainMap
import logging

from pluggy import PluginManager
from pydantic import BaseModel, model_validator, field_validator

from tangl.entity import Entity, EntityType, BaseJournalItem
from tangl.entity.mixins import RenderHandler, NamespaceHandler
from tangl.entity.smart_new import SmartNewHandler
from tangl.plugin_spec import GraphPluginSpec, PLUGIN_LABEL
from tangl.utils.response_models import KVList
from tangl.graph import Node, NodeType, Graph, GraphType, GraphFactory
from .associating import Associating, AssociationHandler
from .traversal import TraversableNode, Edge, TraversableGraph, TraversalHandler

if TYPE_CHECKING:
    from tangl.media import MediaNode

ServiceResponse = TypeVar("ServiceResponse", BaseJournalItem, KVList)

logger = logging.getLogger("tangl.plugins")
logger.setLevel(logging.WARNING)

class PluginHandler:
    """
    This handler wraps a `pluggy` plugin manager and translates between UsesPlugins
    methods and the actual plugin manager hook calls.
    """

    # entity hooks

    @classmethod
    def on_new_entity(cls, pm: PluginManager, obj_cls: str | type[EntityType], data: dict = None) -> Type[EntityType] | None:
        # returns a class
        logger.debug( f'trying to call on_new_entity {obj_cls}')
        res = pm.hook.on_new_entity(obj_cls=obj_cls, data=data)
        if not isinstance(res, type):
            logger.debug( f'failed to get a valid new class {res}')
            return obj_cls
        logger.debug( f"new obj_cls: {res}" )
        return res

    @classmethod
    def on_get_namespace(cls, pm: PluginManager, entity: EntityType) -> Mapping | list[Mapping]:
        # return map of custom vals
        maps = pm.hook.on_get_namespace(entity=entity)  # type: list[Mapping]
        if all([isinstance(r, dict) for r in maps]):
            return {**ChainMap(*reversed(maps))}
        return maps

    @classmethod
    def on_render(cls, pm: PluginManager, entity: EntityType) -> Mapping | list[Mapping]:
        # return map of custom vals
        maps = pm.hook.on_render(entity=entity)  # type: list[Mapping]
        if all([isinstance(r, dict) for r in maps]):
            return {**ChainMap(*reversed(maps))}
        return maps  # fallback, return list of maps

    # graph/node hooks

    @classmethod
    def on_init_entity(cls, pm: PluginManager, entity: EntityType):
        # todo: only do this if the hook exists, world always calls it
        # in-place
        if isinstance(entity, Node):
            return pm.hook.on_init_node(node=entity)
        elif isinstance(entity, Graph):
            return pm.hook.on_init_graph(graph=entity)
        elif isinstance(entity, GraphFactory):
            return pm.hook.on_init_factory(factory=entity)

    @classmethod
    def on_enter_entity(cls, pm: PluginManager, entity: TraversableNode | TraversableGraph, with_edge: Edge = None) -> Optional[Edge]:
        # if `enter` returns an edge, the graph handler will redirect to follow it automatically
        # this is marked firstresult, so no aggregation
        if isinstance(entity, Node):
            return pm.hook.on_enter_node(node=entity, with_edge=with_edge)    # type: Edge
        elif isinstance(entity, Graph):
            return pm.hook.on_enter_graph(graph=entity)  # type: Edge

    @classmethod
    def on_exit_entity(cls, pm: PluginManager, entity: TraversableNode | TraversableGraph, with_edge: Edge = None) -> Optional[Edge]:
        # if exit returns an edge, the graph handler will continue and follow it automatically
        # this is marked 'firstresult', so no aggregation
        if isinstance(entity, Node):
            return pm.hook.on_exit_node(node=entity, with_edge=with_edge)    # type: Edge
        elif isinstance(entity, Graph):
            return pm.hook.on_exit_graph(graph=entity)  # type: Edge

    @classmethod
    def on_associate_with(cls, pm: PluginManager, node: Associating,
                          other: Node, as_parent: bool = False):
        # in-place bookkeeping
        pm.hook.on_associate_with(node=node, other=other, as_parent=as_parent)

    @classmethod
    def on_disassociate_from(cls, pm: PluginManager, node: Associating, other: Node):
        # in-place bookkeeping
        pm.hook.on_disassociate_from(node=node, other=other)

    @classmethod
    def on_get_traversal_status(cls, pm: PluginManager, graph: TraversableGraph) -> list[Mapping | KVList]:
        # return this as is and let the service layer convert it into a response
        return pm.hook.on_get_traversal_status(graph=graph)

    # other hooks

    @classmethod
    def on_prepare_media(cls,
                         pm: PluginManager,
                         node: MediaNode,
                         forge_kwargs: dict = None,
                         spec_overrides: dict = None) -> Any:
        # prepare a media node, may return a RIT, media, or operate in place
        # called directly by media_handler
        return pm.hook.on_prepare_media(node=node, forge_kwargs=forge_kwargs, spec_overrides=spec_overrides)

    @classmethod
    def on_handle_service_response(cls, pm: PluginManager, response: ServiceResponse) -> ServiceResponse:
        # called directly by service manager
        return pm.hook.on_handle_response(response=response)

class UsesPlugins:

    @property
    def pm(self):
        raise NotImplementedError

    def __init__(self: EntityType, defer_init=False, **kwargs):
        super().__init__(**kwargs)
        if self.pm and not defer_init:
            PluginHandler.on_init_entity(self.pm, self)

    @SmartNewHandler.normalize_class_strategy
    def _check_plugins_for_class_override(base_cls: Type[Entity],
                                          _pm: PluginManager = None,
                                          **kwargs) -> Type[Entity]:
            if _pm:
                new_cls = PluginHandler.on_new_entity(_pm, base_cls, kwargs)
                if new_cls:
                    return new_cls

    @RenderHandler.strategy
    def _include_on_render_plugin(self: EntityType):
        if self.pm:
            return PluginHandler.on_render(self.pm, self)

    @NamespaceHandler.strategy
    def _include_on_get_namespace_plugin(self: EntityType):
        if self.pm:
            return PluginHandler.on_get_namespace(self.pm, self)

    @TraversalHandler.enter_strategy
    def _call_on_enter_plugin(self: TraversableGraph | TraversableNode, with_edge: Edge = None):
        if self.pm:
            return PluginHandler.on_enter_entity(self.pm, self, with_edge = with_edge)
    _call_on_enter_plugin.strategy_priority = 10

    @TraversalHandler.exit_strategy
    def _call_on_exit_plugin(self: TraversableGraph | TraversableNode, with_edge: Edge = None):
        if self.pm:
            return PluginHandler.on_exit_entity(self.pm, self, with_edge=with_edge)
    _call_on_exit_plugin.strategy_priority = 10

    @AssociationHandler.associate_with_strategy
    def _call_on_associate_with_plugin(self: NodeType, other: NodeType, as_parent: bool = False):
        if self.pm:
            return PluginHandler.on_associate_with(self.pm, self, other, as_parent=as_parent)

    @AssociationHandler.disassociate_from_strategy
    def _call_on_disassociate_from_plugin(self: NodeType, other: NodeType):
        if self.pm:
            return PluginHandler.on_disassociate_from(self.pm, self, other)


class HasPluginManager(UsesPlugins, BaseModel, arbitrary_types_allowed=True):

    #: independent pluggy plugin manager per world instance
    plugin_manager: PluginManager = None
    plugins: Any = None

    @field_validator('plugins', mode="before")
    @classmethod
    def _instantiate_plugins_if_req(cls, data):
        if callable(data):
            return data()
        return data

    @property
    def pm(self):
        return self.plugin_manager

    @pm.setter
    def pm(self, value: PluginManager):
        self.plugin_manager = value

    @model_validator(mode="after")
    # @classmethod
    def _setup_plugin_manager(self):
        if not isinstance(self.pm, PluginManager):
            logger.debug('creating pm')
            pm = PluginManager(PLUGIN_LABEL)
            pm.add_hookspecs(GraphPluginSpec)
            self.pm = pm
        if self.plugins:
            logger.debug("installing plugins")
            plugins = self.plugins
            self.pm.register(plugins, plugins.__class__.__name__)
        else:
            from tangl.plugin_spec import NoOpGraphImpl
            self.pm.register(NoOpGraphImpl())
        return self

    # factory plugin invocations

    def create_node(self, defer_init=False, **data) -> NodeType:
        return super().create_node(_pm=self.pm, defer_init=defer_init, **data)

    def create_graph(self, defer_init=False, **data) -> GraphType:
        # always defer the init on the graph class so nodes can be added
        graph = super().create_graph(_pm=self.pm, defer_init=True, **data)
        if not defer_init:
            # if the _caller_ requested a deferred init, don't trigger it yet
            PluginHandler.on_init_entity(self.pm, graph)
        return graph
