import pytest
from tangl.graph import Graph, Node, GraphStructuringHandler
from tangl.persistence.serializers import *
from tangl.config import settings

def test_node_structuring():

    node1 = Node()
    data = GraphStructuringHandler.unstructure(node1)
    print( data )
    node2 = GraphStructuringHandler.structure(data)
    assert node1 == node2

    node2.tags.add("hello")
    assert node1 != node2

class SubclassedNode(Node):
    foo: int = 100

def test_subclassed_node_structuring():

    node1 = SubclassedNode(foo=200)
    data = GraphStructuringHandler().unstructure(node1)
    print( data )
    assert data['foo'] == 200
    node2 = GraphStructuringHandler.structure(data)
    assert type(node1) == type(node2)
    assert node1 == node2

    node2.tags.add("hello")
    assert node1 != node2

# Example graph creation function
@pytest.fixture
def example_graph():
    graph = Graph()
    node = Node(label="unique_label")
    graph.add_node(node)
    node2 = SubclassedNode(foo=200)
    graph.add_node(node2)
    return graph

def test_graph_structuring(example_graph):

    graph1 = example_graph
    node_id = list(example_graph.nodes.keys())[0]
    data = GraphStructuringHandler().unstructure(graph1)
    print( data )

    graph2 = GraphStructuringHandler().structure(data)
    assert graph1 == graph2

    example_graph.nodes[node_id].tags.add("hello")
    assert graph1 != graph2

def test_graph_structuring2(example_graph):

    initial_node = example_graph.get_node("unique_label")

    data = GraphStructuringHandler.unstructure(example_graph)
    graph2 = GraphStructuringHandler.structure(data)

    retrieved_node = graph2.get_node("unique_label")
    assert retrieved_node == initial_node

    assert example_graph == graph2

@pytest.fixture(params=[NoopSerializationHandler,
                        PickleSerializationHandler,
                        JsonSerializationHandler,
                        YamlSerializationHandler,
                        BsonSerializationHandler
                        ])
def serializer(request):
    if request.param == BsonSerializationHandler:
        # Check if Mongo is supported or available
        if not settings.service.apis.mongo.enabled:
            pytest.xfail("Mongo support is not available")
    return request.param()

def test_graph_serialization(serializer, example_graph):
    original_graph = example_graph
    node_id = list(example_graph.nodes.keys())[0]
    unstructured = GraphStructuringHandler.unstructure(original_graph)
    flat = serializer.serialize(unstructured)
    unflat = serializer.deserialize(flat)
    restructured_graph = GraphStructuringHandler.structure(unflat)

    # Assertions to verify that the deserialized graph is equivalent to the original
    assert restructured_graph == original_graph  # Implement appropriate comparison logic

    original_graph.get_node(node_id).tags.add("hello")
    assert restructured_graph != original_graph

@pytest.fixture
def example_graph_w_factory():
    # factory = GraphFactory('test_factory')
    # graph = Graph(factory=factory)
    graph = Graph()
    node = Node()
    graph.add_node(node)
    return graph

@pytest.mark.xfail(reason="factory not serializing properly")
def test_graph_serialization_with_factory(serializer, example_graph_w_factory):
    original_graph = example_graph_w_factory
    unstructured = GraphStructuringHandler().unstructure_graph(original_graph)
    flat = serializer.serialize(unstructured)
    unflat = serializer.deserialize(flat)
    restructured_graph = GraphStructuringHandler().structure_graph(unflat)

    # Assertions to verify that the deserialized graph is equivalent to the original
    assert restructured_graph == original_graph
