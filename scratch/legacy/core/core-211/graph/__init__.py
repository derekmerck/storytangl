"""
Graph Subpackage
---------------

Graph serves as the foundational building-block for constructing complex narrative structures. Rooted in the principles of graphs and trees, it offers a flexible framework to represent and manipulate key moments, choices, or events in the narrative.

Node inherits from Entity and represents a node in a Graph, with properties like parent, children, etc.
Graph contains a dict of Node objects representing a graph structure.

Node mixins deal with relationships.

- AssociationHandler manages dynamic relationships between Associating nodes.
- TraversalHandler handles graph traversal logic for Traversable nodes.
- StructuringHandler helps serialize and deserialize Graph and Node objects.
- PluginHandler allows hooking into lifecycle events of graphs and nodes.

The module is designed to provide both simplicity for basic narrative structures and extensibility for more advanced requirements. By combining nodes, trees, and the collection index, along with the power of mixins, users can create intricate, dynamic, and interactive narratives.

In the larger context of the StoryTangl package, the Node module acts as the structural backbone, enabling the creation, manipulation, and interpretation of narrative content.

- **Nodes**: Represents individual units or moments in the narrative. They can be associated with various mixins to imbue them with specific functionalities.
- **Trees**: Organizes nodes in a hierarchical manner, allowing for parent-child relationships and enabling the representation of branching narratives.
- **Graph**: A collection of nodes, facilitating easy access, lookup, and management of nodes. This abstraction helps in keeping the narrative organized and easily traversable.
- **Mixins**: Extend the functionalities of nodes, allowing for specific behaviors such as rendering, runtime evaluation, traversal, trading, and more.
"""

from .graph import Graph, GraphType
from .node import Node, NodeType

from .structuring import GraphStructuringHandler
from .factory import GraphFactory, HierarchicalStructuringHandler

