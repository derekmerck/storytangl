import uuid

from tangl.core import Node, Index

def node_factory(data: dict, index: Index = None, parent: Node = None):
    """
    Recursively create Node objects from a dictionary.

    This will _only_ create base-class Nodes.  It is primarily for testing/dev.

    It does not:
    - type cast
    - handle templating
    - refactor type-hinted children properties
    """

    # Base case: if no 'children' key, make a single Node
    if 'children' not in data:
        return Node(guid=uuid.uuid4(), parent=parent, index=index, **data)

    # Recursive case: create this node and its children
    else:
        children = data.pop('children')
        node = Node(guid=uuid.uuid4(), parent=parent, index=index, **data)
        for child_data in children:
            child = node_factory(child_data, parent=node)
            node.add_child(child)
        return node

def index_factory(data: list, index: Index = None):
    """Create an Index from a dictionary with potentially multiple root nodes."""
    index = index or Index()
    root_nodes = [node_factory(root_data, index) for root_data in data]
    for node in root_nodes:
        index.add(node)
    return index
