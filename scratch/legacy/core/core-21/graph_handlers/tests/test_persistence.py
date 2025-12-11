import attr

from tangl.core import Node, Graph
from tangl.utils.persistent import PicklePersistent

PersistentNode = attr.make_class('PersistentNode', (), (PicklePersistent, Node))



PersistentGraph = attr.make_class('PersistentGraph', (), (PicklePersistent, Graph))


def test_index_persistence(tmpdir):

    # Create some structured data for node-tree-and-index creation
    data = [
        {
            'label': 'root1',
            'children': [
                {'label': 'child1'},
                {'label': 'child2'},
            ],
        },
        {
            'label': 'root2',
            'children': [
                {'label': 'child3'},
                {'label': 'child4'},
            ],
        },
    ]

    # Create an index using the factory
    original_index = PersistentGraph()

    for node_ in data:
        node_['children'] = [ Node(**data) for data in node_['children'] ]
        node = Node(**node_, graph=original_index)
        # for i, child_ in enumerate(node.children):
        #     node.children[i] = Node(**child_)
        #     node.add_child(node.children[i])

    # Save the index to a file
    file_path = tmpdir / 'index.pickle'
    original_index.save(file_path)

    # Load the index from the file
    loaded_index = PersistentGraph.load(file_path)

    # Verify that the loaded index is identical to the original
    assert len(loaded_index) == len(original_index)
    for guid, original_node in original_index.items():
        assert guid in loaded_index
        loaded_node = loaded_index.find(guid)
        assert loaded_node == original_node
        print( original_node.parent )
        print( loaded_node.parent )
        print( loaded_node.graph )
        print( "------" )
        print( loaded_index )
        assert loaded_node.graph is loaded_index
