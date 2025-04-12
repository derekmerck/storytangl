import copy
import inspect
from typing import Literal, Type, get_type_hints, get_args, Any
import logging

from tangl.entity import Entity
# from tangl.entity.self_casting import SelfCastingHandler
from tangl.entity.smart_new import SmartNewHandler
from .node import Node, NodeType
from .graph import Graph, GraphType

ChildValueType = Literal['item_collection', 'discrete_item']
ChildFieldInfo = dict[str, tuple[Type[NodeType], ChildValueType]]

IGNORE_UNRECOGNIZED = False
# these get consumed by entity's new/init so they are "recognized"
PASSTHRU_FIELDS = [ '_pm', 'defer_init', 'templates', 'template_maps', 'from_ref' ]

logger = logging.getLogger("tangl.factory")
logger.setLevel(logging.WARNING)

class HierarchicalStructuringHandler:

    @staticmethod
    def _infer_child_type(attrib) -> Type[NodeType]:
        try:
            type_hints = get_type_hints(attrib.fget)
        except NameError:
            # print( f"Failed on {attrib.fget}")
            raise TypeError
        return_hint = type_hints['return']  # list[item] or dict[str, item]

        if inspect.isclass(return_hint) and issubclass(return_hint, Node):
            child_cls = return_hint
            return child_cls, "discrete_item"

        elif return_args := get_args(return_hint):
            child_cls = return_args[-1]
            if inspect.isclass(child_cls) and issubclass(child_cls, Node):
                return child_cls, "item_collection"

        raise TypeError(f"Unable to infer value type from return hint {return_hint}")

    @staticmethod
    def _get_child_fields(obj_cls: Type[NodeType]) -> ChildFieldInfo:

        child_type_info = {}
        for attrib_name in dir(obj_cls):
            if attrib_name in ['__fields__']:
                continue
            attrib = getattr(obj_cls, attrib_name)
            if isinstance(attrib, property):
                # It might be a child type, try to infer the class
                try:
                    # property fields with leading underscores are assumed to be type hinting aliases
                    # for the un-underscored name, ie., _components: Component -> components: Component
                    child_cls, value_type = HierarchicalStructuringHandler._infer_child_type(attrib)
                    child_type_info[attrib_name.strip("_")] = child_cls, value_type
                except (TypeError, KeyError) as e:
                    # logger.warning(f"Cannot infer type from { attrib_name }, {e}")
                    pass
        return child_type_info

    @classmethod
    def structure_node(cls,
                       base_cls: Type[NodeType] = Node,       # expected class
                       obj_cls: Type[NodeType] | str = None,  # declared subclass
                       parent: NodeType = None,
                       graph: GraphType = None,
                       graph_cls: Type[GraphType] = Graph,
                       **data) -> NodeType:
        """
        Recursively structure a hierarchical Node representation, such as from a ScriptItem
        dump with children represented as fields.
        """
        # Create a graph if we don't have one
        graph = graph or graph_cls()

        # Determine the real object class
        obj_cls = SmartNewHandler.handle_cls(base_cls, obj_cls, **data)
        logger.debug(f"real class is {obj_cls}")
        # Determine the real kwargs
        data = SmartNewHandler.handle_kwargs(obj_cls, kwargs=data)

        # Copy data to keep original immutable
        data = copy.deepcopy(data)

        # include _pm and defer_init, if given for plugin classes
        fields_to_pass = obj_cls.public_field_names() + PASSTHRU_FIELDS
        # These fields can be structured normally by obj_cls
        recognized_field_data = { k: v for k, v in data.items()
                                  if k in fields_to_pass }

        logger.debug(f"{obj_cls.__name__} {recognized_field_data}")

        # Create base Node
        node = obj_cls(graph=graph, **recognized_field_data)
        if parent:
            parent.add_child(node)
        else:
            graph.add_node(node)

        # These fields must be recursively structured into child nodes
        child_field_info = cls._get_child_fields( obj_cls )
        # print( child_field_info )
        child_field_data = { k: v for k, v in data.items() if k in child_field_info and v is not None }

        # Handle hierarchical fields
        for field_name, child_values in child_field_data.items():
            child_obj_cls, value_type = child_field_info[field_name]

            match value_type:
                case "discrete_item":
                    if not isinstance( child_values, dict ):
                        raise ValueError("Wrong value type for discrete-item child field")
                    child_data = child_values
                    child_data.setdefault('obj_cls', child_obj_cls)
                    cls.structure_node(graph=graph,
                                       base_cls=child_obj_cls,
                                       parent=node,
                                       **child_data)
                case "item_collection":
                    if isinstance(child_values, list):
                        if not all(isinstance(c, dict) for c in child_values):
                            raise ValueError("Wrong value type for list-defined child collection")
                        for i, child_data in enumerate( child_values ):
                            key_len = min( len(field_name), 3 )
                            child_data.setdefault('label', f'{field_name[:key_len]}_{i}')
                            child_data.setdefault('obj_cls', child_obj_cls)
                            cls.structure_node(graph=graph,
                                               base_cls=child_obj_cls,
                                               parent=node,
                                               **child_data)
                    elif isinstance(child_values, dict):
                        if not all(isinstance(c, dict) for c in child_values.values()):
                            raise ValueError(f"Wrong value type for dict-item child collection {child_values}")
                        for k, child_data in child_values.items():
                            child_data.setdefault('label', k)
                            child_data.setdefault('obj_cls', child_obj_cls)
                            cls.structure_node(graph=graph,
                                               base_cls=child_obj_cls,
                                               parent=node,
                                               **child_data)
                case _:
                    raise TypeError("Unrecognized value type")

        # These fields have no unstructuring hints
        unrecognized_fields = { k: v for k, v in data.items() if
                                k not in recognized_field_data and
                                k not in child_field_data }

        if unrecognized_fields and \
                not IGNORE_UNRECOGNIZED and \
                not obj_cls.model_config.get('extras') == "allow":
            raise TypeError(f"Encountered parameters for {obj_cls} with no unstructuring rules: { unrecognized_fields }")

        return node


class GraphFactory(Entity):
    """
    Builds graphs from hierarchical node representations such as Script objects.
    """

    def create_node(self, **node_data) -> NodeType:
        return HierarchicalStructuringHandler.structure_node(**node_data)

    def create_graph(self, base_cls: Type[Graph] = Graph, nodes: list = None, **graph_data) -> GraphType:
        obj_cls = SmartNewHandler.handle_cls(base_cls=base_cls, **graph_data)  # type: Type[Graph]
        graph = obj_cls(**graph_data, factory=self)
        for node_data in nodes or []:
            node = self.create_node(graph=graph, **node_data)
        return graph
