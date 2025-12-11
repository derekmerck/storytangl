import logging

import uuid
from datetime import datetime
from logging import getLogger

from tangl.type_hints import UnstructuredData
from tangl.persistence.structuring import SimpleStructuring
from tangl.entity import Entity, SingletonEntity
from tangl.graph import Node, Graph

logger = logging.getLogger("tangl.persist")

# todo: if this is a _handler_, it should be class-methods only according to naming convention
#       otherwise it is a _manager_, but it doesn't seem to have any private vars...

class GraphStructuringHandler:
    """
    Handler for structuring and unstructuring Node and Graph objects.

    Converts Node and Graph objects to and from Python dictionary representations
    that are suitable for serialization/deserialization. This handler leverages
    Pydantic's 'model_dump' method and recursive instantiation to facilitate
    conversion between complex graph objects and simpler data structures.
    """

    def clean_unstructured_data(self, data: dict):
        # these types can be coerced back to python types from json-friendly formats
        for k, v in data.items():
            if isinstance(v, uuid.UUID):
                data[k] = v.hex
            if isinstance(v, set):
                data[k] = list(v)
            if isinstance(v, datetime):
                data[k] = v.isoformat(),
        # this will break if we need to include False or 0, but len(v) breaks on numbers
        data = { k: v for k, v in data.items() if v }
        return data

    def unstructure_node(self, node: Node | SingletonEntity ) -> UnstructuredData:
        if isinstance(node, SingletonEntity):
            data = {'label': node.label}
        elif isinstance(node, Node):
            data = node.model_dump(
                exclude={"graph"},
                exclude_none=True,
                exclude_defaults=True)
        else:
            raise TypeError(f"Unknown type {node.__class__} in graph")
        if node.__class__ != Node:
            data['node_cls'] = node.__class__.__name__
        return data

    def structure_node(self, data: UnstructuredData) -> Node:
        node_cls = data.pop('node_cls', Node)
        if node_cls is not Node:
            node_cls = Entity.get_subclass_by_name(node_cls)
        node = node_cls( **data )
        return node

    def unstructure_graph(self, graph: Graph) -> UnstructuredData:
        data = graph.model_dump(exclude={'nodes'})
        # data['factory'] = graph.factory.__reduce__()  # returns (cls, (label,))
        data['nodes'] = [ self.unstructure_node(v) for v in graph.nodes.values() ]
        if graph.__class__ != Graph:
            data['graph_cls'] = graph.__class__.__name__
        return data

    def structure_graph(self, data: UnstructuredData) -> Graph:
        nodes = data.pop('nodes')
        graph_cls = data.pop('graph_cls', Graph)
        if graph_cls is not Graph:
            graph_cls = Graph.get_subclass_by_name(graph_cls)
        # if 'factory' in data:
        #     factory_cls, factory_label = data.pop('factory')      # returns (cls, (label,))
        #     factory = factory_cls.get_instance(factory_label[0])  # todo: deref class
        # else:
        #     factory = None
        # todo: defer init here
        graph = graph_cls( **data )
        for data in nodes:
            graph.add_node( self.structure_node(data) )
        return graph

    def structure(self, data: UnstructuredData) -> Graph | Node:
        if 'node_cls' in data:
            return self.structure_node(data)
        elif 'graph_cls' in data:
            return self.structure_graph(data)
        logger.debug( f"SimpleStructure with obj_cls: {data['obj_cls']}" )
        return SimpleStructuring.structure(self, data)

    def unstructure(self, entity: Graph | Node) -> UnstructuredData:
        if isinstance(entity, Graph):
            data = self.unstructure_graph(entity)
        elif isinstance(entity, Node):
            data = self.unstructure_node(entity)
        else:
            try:
                data = SimpleStructuring.unstructure(self, entity)
                logger.debug( f"Using simple unstructure for {data}" )
            except Exception as e:
                print( e )
                raise TypeError(f"Unknown object type {type(entity)} passed to unstructure")
        return self.clean_unstructured_data(data)
