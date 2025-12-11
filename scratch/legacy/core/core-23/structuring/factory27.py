from __future__ import annotations
import inspect
import pydantic
from typing import Type, get_type_hints, get_args, Iterable, Literal
from logging import getLogger

from tangl.type_hints import UniqueLabel
from tangl.entity import Entity, SingletonEntity
from .node import Node, Graph

logger = getLogger("tangl.graph.factory")

class GraphFactory(SingletonEntity):

    # These defaults could be static, but the signatures should be left as instance
    # methods so that overrides can access properties on their instance.
    def _normalize_node_cls(self, node_cls: str | type[Node], **data) -> type[Node]:
        if isinstance(node_cls, str):
            node_cls = Node.get_subclass_by_name(node_cls)

        if not inspect.isclass(node_cls) or not issubclass(node_cls, Node):
            print( Node.get_all_subclasses() )
            raise ValueError(f"Unable to determine node-type from {node_cls}")

        return node_cls

    def _normalize_data(self, node_cls: type[Node], **data) -> dict:
        return data

    def _infer_child_type(self, attrib: property, value: list | dict ) \
            -> tuple[ type[Node], Literal['item_list', 'item_dict', 'discrete_item'] ]:

        type_hints = get_type_hints(attrib.fget)
        return_hint = type_hints['return']
        # if issubclass(return_hint, Node):

        child_cls, value_type = None, None
        if inspect.isclass(return_hint) and issubclass(return_hint, Node):
            child_cls = return_hint      # discrete item
            if isinstance(value, dict):
                value_type = "discrete_item"
            else:
                raise TypeError("Unable to infer value type from hint and value")
        elif return_args := get_args(return_hint):
            child_cls = return_args[-1]  # list[item] or dict[str, item]
            if isinstance(value, list):
                value_type = "item_list"
            elif isinstance(value, dict):
                value_type = "item_dict"
            else:
                raise TypeError("Unable to infer value type from hint and value")
        return child_cls, value_type

    def _create_child(self, child_cls, child_data, parent_node):
        if 'node_cls' not in child_data:
            child_data['node_cls'] = child_cls
        else:
            child_data['node_cls'] = child_cls.get_subclass_by_name(child_data['node_cls'])
        child = self.create_node(**child_data, graph=parent_node.graph)
        parent_node.add_child(child)

    def create_node(self,
                    node_cls: Type[Node] = Node,
                    graph: Graph = None,
                    **data) -> Node:
        """
        Recursively construct a node and all children
        """
        graph = graph or Graph()

        node_cls = self._normalize_node_cls(node_cls, **data)
        data = self._normalize_data(node_cls, **data)

        # deal with recognized field names
        recognized_field_names = node_cls.public_field_names()
        recognized_data = {key: value for key, value in data.items() if key in recognized_field_names}

        # create the object
        try:
            node = node_cls(**recognized_data, graph=graph)
        except TypeError:
            logger.error(f"Failed to create {node_cls} inst with {recognized_data}")
            raise
        except pydantic.ValidationError:
            logger.error(f"Failed validation for {node_cls} inst with {recognized_data}")
            raise

        # deal with unrecognized kwargs and misnamed children
        unrecognized_data = {key: value for key, value in data.items() if key not in recognized_field_names}
        for key, value in unrecognized_data.items():
            if hasattr(node_cls, key):
                attrib = getattr(node_cls, key)
                if isinstance(attrib, property) and isinstance(value, list | dict):
                    # It might be a child type, try to infer the class
                    child_cls, value_type = self._infer_child_type(attrib, value)
                    match value_type:
                        case "item_list":
                            # it's a list of children, can take it as is
                            for i, child_data in enumerate( value ):
                                if 'label' not in child_data:
                                    child_data['label'] = f"{key}{i}"
                                self._create_child(child_cls, child_data, parent_node=node)
                        case 'item_dict':
                            # it's a dict of children, flatten it into a list
                            for label, child_data in value.items():
                                # some dictionaries have no value and use the label itself as a ref
                                child_data = child_data or {}
                                if 'label' not in child_data:
                                    child_data['label'] = label
                                self._create_child(child_cls, child_data, parent_node=node)
                        case 'discrete_item':
                            child_data = value
                            self._create_child(child_cls, child_data, parent_node=node)
            elif key not in ['ref']:
                # node_cls doesn't have annotation for the unrecognized key
                # 'ref' is an inheritance reference key for singleton types
                raise TypeError(f"Unrecognized key: '{key}' in {node_cls.__name__} (val={value}, label={data.get('label')})")
        return node

    def create_graph(self, graph_cls: Type[Graph] = Graph, **kwargs) -> Graph:
        return graph_cls(**kwargs)

    @classmethod
    def create_factory(cls, label: UniqueLabel, **kwargs) -> GraphFactory:
        return cls(label=label, **kwargs)
