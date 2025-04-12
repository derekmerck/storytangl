from typing import Type, Mapping, TYPE_CHECKING

from tangl.type_hints import UnstructuredData
from tangl.persistence.structuring import StructuringHandler
from tangl.entity import Entity, EntityType
from .graph import Graph, GraphType

if TYPE_CHECKING:
    from tangl.persistence import PersistenceManagerName

class GraphStructuringHandler(StructuringHandler):
    """
    Inherits from `StructuringHandler` but adds specialized handling for graph structures.
    Handles both simple entities and graph-based entities by checking if the `obj_cls` corresponds to a `Graph` subclass.

    Methods:
      - `structure(data)`: For graphs, it constructs the graph instance and then iterates over node data to structure each node and add it to the graph.
      - `unstructure(entity)`: For graphs, it serializes the graph itself while excluding nodes, then serializes each node individually and adds this list to the graph's serialized data.
        This ensures that both the graph's structural information and its constituent nodes are fully captured.
    """

    @classmethod
    def structure_graph(cls, graph_cls: Type[Graph], unstructured: UnstructuredData):
        nodes = unstructured.pop('nodes')
        graph = graph_cls(**unstructured)
        for node_data in nodes:
            node = cls.structure(node_data)
            graph.add_node(node)
        return graph

    @classmethod
    def structure(cls,
                  unstructured: UnstructuredData,
                  obj_cls_map: Mapping[str, Type] = None) -> Entity:
        obj_cls = unstructured.pop('obj_cls')
        if isinstance(obj_cls, str):
            if x := Entity.get_subclass_by_name(obj_cls):
                # 'cold-loading' for entity subclasses that haven't already been noted
                obj_cls = x
            else:
                # fall back on persisted class records
                obj_cls = obj_cls_map[obj_cls]
        if issubclass(obj_cls, Graph):
            return cls.structure_graph(obj_cls, unstructured)
        return obj_cls( **unstructured )

    @classmethod
    def unstructure_graph(cls, graph: GraphType):
        graph_data = graph.model_dump(exclude={'nodes'})
        if 'obj_cls' not in graph_data:
            graph_data['obj_cls'] = graph.__class__
        node_data = []
        for node in graph.nodes.values():
            node_data.append( cls.unstructure(node) )
        graph_data['nodes'] = node_data
        return graph_data

    @classmethod
    def unstructure(cls, entity: EntityType) -> UnstructuredData:
        if isinstance(entity, Graph):
            return cls.unstructure_graph(entity)
        return super().unstructure(entity)
