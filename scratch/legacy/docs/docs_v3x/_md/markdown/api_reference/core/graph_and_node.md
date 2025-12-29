# Graph

### *pydantic model* tangl.core.graph.Graph

The Graph class serves as a central repository for all [`Nodes`](#tangl.core.graph.Node)
within a story. It manages the relationships between nodes and provides methods for efficient
node retrieval and traversal.

## Key Features

* **Node Registry**: The Graph maintains a flat dictionary of nodes and has methods for adding, removing, and retrieving items.  Nodes added to the graph must have unique UUIDs and paths.
* **Efficient Lookup**: Supports lookup by UUID, label, or path.
* **Filtering**: Ability to find nodes based on various criteria like class type or tags.
* **Traversal Support**: Provides the foundation for story traversal mechanics.

## Usage

```python
from tangl.core.graph import Graph, Node

# Create a graph
graph = Graph()

# Add nodes to the graph
root = Node(label="root", graph=graph)
child1 = Node(label="child1")
child2 = Node(label="child2")

root.add_child(child1)
root.add_child(child2)

# Retrieve nodes
retrieved_node = graph.get_node(child1.uid)
print(retrieved_node == child1)  # True

# Find nodes
special_nodes = graph.find_nodes(with_tags={"special"})
```

## Mixin Classes

The Graph class is designed to be extended for specific story management needs.

* [`Traversable`](mixins_and_handlers.md#tangl.core.graph.handlers.TraversableGraph): Adds graph traversal functionality.

* **Fields:**
  - `uid ()`
  - `label ()`
  - `tags ()`
  - `obj_cls ()`
  - `nodes (dict[UUID, Node])`
* **Validators:**
  - `_handle_none_tags` » `tags`
  - `_handle_none_tags` » `with_tags`

#### *field* nodes *: dict[UUID, Node]* *[Optional]*

A dictionary that maps UUIDs to Nodes, forming the backbone of the narrative structure.

#### add_node(node)

Incorporates nodes into the graph, underpinning the dynamic expansion of the narrative.

#### remove_node(node)

This is \_not_ guaranteed to find all references nor to preserve references
to children with multiple associations.

It is provided purely for completeness and testing purposes.

#### get_node(key)

Get a node by unique identifier or path

* **Return type:**
  [`Node`](#tangl.core.graph.Node)

#### find_nodes(with_cls=None, filt=None, with_tags=None)

Filter nodes based on various conditions:

* **Parameters:**
  * **node_cls** – Tuple of Node subtypes to find, e.g. Renderables | Edges
  * **filt** (`Callable`) – Callable test for a specific criteria, e.g. lambda x: x.has_tag(‘important’)
  * **has_tags** – Iterable of tags that should pe present on the node
  * **conditions** – List of condition strings that should be satisfied by the node namespace
* **Return type:**
  `list`[`TypeVar`(`NodeType`, bound= [`Entity`](entity.md#tangl.core.entity.Entity))]
* **Returns:**
  List of Nodes matching the given conditions or all Nodes if no conditions are given

#### find_node(with_cls=None, filt=None, with_tags=None)

Convenience functions to return the first candidate from find_nodes query.

* **Return type:**
  [`Node`](#tangl.core.graph.Node)

#### has_tags(\*tags)

Condition querying based on tags, enhancing search and categorization.

* **Return type:**
  `bool`

#### *field* uid *: UUID* *[Optional]* *(name 'uid_')*

Unique identifier for each instance for registries and serialization.

#### *field* label *: Optional[str]* *= None* *(name 'label_')*

A short public identifier, usually based on a template name or a truncated uid hash if unspecified, may require uniqueness in some contexts.

#### *field* tags *: Tags* *[Optional]*

Mechanism to classify and filter entities based on assigned characteristics or roles.

#### *field* obj_cls *: Optional[ClassName]* *= None*

The ability to self-cast on instantiation is actually granted by `SelfFactorying`, but the trigger field is included in the base class documentation because in practice, all Entities are self-casting.

# Node

### *pydantic model* tangl.core.graph.Node

Bases: [`Entity`](entity.md#tangl.core.entity.Entity)

Nodes are the basic building blocks of the story structure in StoryTangl. They extend the
[`Entity`](entity.md#tangl.core.entity.Entity) class, adding hierarchical relationship capabilities and
graph association.

## Key Features

* **Parent-Child Relationships**: Nodes can have bidirectional relationships with both parent and children nodes.
* Graph Association: Each node is associated with a [`Graph`](#tangl.core.graph.Graph) for efficient traversal and querying.
* Path Generation: Nodes generate a unique [`path`](#tangl.core.graph.Node.path) based on the node’s position in the graphh hierarchy.
* Dynamic Child Management: Methods for adding, removing, and finding child nodes.

## Usage

```python
from tangl.core.graph import Node, Graph

# Create a graph and nodes
graph = Graph()
root = Node(label="root", graph=graph)
child1 = Node(label="child1")
child2 = Node(label="child2")

# Build hierarchy
root.add_child(child1)
root.add_child(child2)

# Access hierarchy
print(child1.parent == root)  # True
print(root.children)  # [child1, child2]
print(child1.path)  # "root/child1"
```

## Mixin Classes

Like its base-class, Entity, Node is designed to be extended with various mixin-classes.
These mixins add graph-related functionality to the Node, trading, and traversal.

* `ScopedNamespace`: Adds cascading namespaces from parents.
* [`Associating`](mixins_and_handlers.md#tangl.core.graph.handlers.Associating): Adds transient connections the Node.
* [`Traversable`](mixins_and_handlers.md#tangl.core.graph.handlers.TraversableNode): Adds graph traversal functionality.

Like Entity, they can self-cast by using the reserved kwarg [`obj_cls`](#tangl.core.graph.Node.obj_cls) to reference any
subclass of Node.

## Related Concepts

* [`Edge`](#tangl.core.graph.Edge) can be used to dynamically connect a node to another by reference.
* `SingletonNode` wraps a singleton with unique local vars and parent/children relationships.
* `StoryNode` provides a common basis for all Story-related object.

* **Fields:**
  - `uid ()`
  - `label ()`
  - `tags ()`
  - `obj_cls ()`
  - `graph (Graph)`
  - `anon (bool)`
  - `parent_id (Optional[UUID])`
  - `children_ids (list[UUID])`
* **Validators:**
  - `_handle_none_tags` » `tags`
  - `_handle_none_tags` » `with_tags`
  - `_register_self_with_graph` » `all fields`
  - `_reference_parent_to_parent_id` » `all fields`
  - `_register_self_with_parent` » `all fields`

#### *field* graph *: Graph* *[Optional]*

The Graph object collection that contains this node.  Omitted from serialization and comparison to prevent recursion issues.

#### *field* anon *: bool* *= False*

#### *field* parent_id *: Optional[UUID]* *= None*

#### *property* parent *: [Node](#tangl.core.graph.Node)*

Link to this node’s parent.

#### *field* children_ids *: list[UUID]* *[Optional]*

#### *property* children *: list[[Node](#tangl.core.graph.Node)]*

A list of child nodes.

#### add_child(node, as_parent=True)

#### remove_child(node, delete_node=False)

#### find_children(with_cls=None, filt=None, with_tags=None, sort_key=None)

Search by class, tags, or filter function within a node’s immediate descendants.

* **Return type:**
  `list`[`TypeVar`(`NodeType`, bound= [`Node`](#tangl.core.graph.Node))]

#### discard_children(with_cls=None, filt=None, with_tags=None, delete_node=False)

#### find_child(with_cls=None, filt=None, with_tags=None, sort_key=None)

* **Return type:**
  `TypeVar`(`NodeType`, bound= [`Node`](#tangl.core.graph.Node))

#### get_child(key)

#### *property* root *: NodeType | None*

The root of this node’s tree.

#### ancestors()

Provide navigation and lookup capabilities within the graph’s structure, essential for tracing narrative paths and relationships.

#### *property* path *: str*

The label path from this node’s root to this node (used as a unique label)

#### has_tags(\*tags)

Condition querying based on tags, enhancing search and categorization.

* **Return type:**
  `bool`

#### *field* uid *: UUID* *[Optional]* *(name 'uid_')*

Unique identifier for each instance for registries and serialization.

#### *field* label *: Optional[str]* *= None* *(name 'label_')*

A short public identifier, usually based on a template name or a truncated uid hash if unspecified, may require uniqueness in some contexts.

#### *field* tags *: Tags* *[Optional]*

Mechanism to classify and filter entities based on assigned characteristics or roles.

#### *field* obj_cls *: Optional[ClassName]* *= None*

The ability to self-cast on instantiation is actually granted by `SelfFactorying`, but the trigger field is included in the base class documentation because in practice, all Entities are self-casting.

# Edge

### *pydantic model* tangl.core.graph.Edge

Bases: [`Node`](#tangl.core.graph.Node)

An Edge is a specialized [`Node`](#tangl.core.graph.Node) that connects a parent predecessor node
with a dynamically linked successor node, facilitating traversal and story flow.

## Key Features

* **Predecessor-Successor Relationship**: Links two nodes for traversal purposes.
* **Predecessor Child**: Edges are typically created as children of their predecessor nodes.
* **Activation Modes**: Supports ‘first’ (redirect), ‘last’ (continue), or None (manual) activation.  The activation mode determines when the TraversalHandler interacts with the edge.
* **Availability Inheritance**: Edge availability depends on the successor’s availability.
* **Traversal Role**:  Edges may define “on_enter” and “on_exit” tasks, but cannot redirect or continue themselves.

## Usage

```python
from tangl.core.graph import Node, Edge

# Create nodes and an edge
predecessor = Node(label="start")
successor = Node(label="next")
edge = Edge(predecessor=predecessor, successor=successor, activation="last")

# Access edge properties
print(edge.predecessor == predecessor)  # True
print(edge.successor == successor)  # True
print(edge.activation)  # "last"
```

* **Fields:**
  - `uid ()`
  - `label ()`
  - `tags ()`
  - `obj_cls ()`
  - `graph ()`
  - `anon ()`
  - `parent_id ()`
  - `children_ids ()`
  - `activation (ActivationMode)`
  - `successor (UniqueLabel | UUID)`
* **Validators:**
  - `_handle_none_tags` » `tags`
  - `_handle_none_tags` » `with_tags`
  - `_alias_predecessor_to_parent` » `all fields`
  - `_convert_successor_to_ref` » `successor`

#### *field* activation *: ActivationMode* *= None*

#### *property* predecessor *: TraversableNode*

#### *field* successor *: UniqueLabel | UUID* *[Required]* *(name 'successor_ref')*

#### *property* successor *: [TraversableNode](mixins_and_handlers.md#tangl.core.graph.handlers.TraversableNode)*

## SimpleEdge

### tangl.core.graph.edge.ActivationMode

alias of `Literal`[‘first’, ‘last’] | `None`

### *pydantic model* tangl.core.graph.SimpleEdge

Bases: [`Entity`](entity.md#tangl.core.entity.Entity)

An SimpleEdge is an *anonymous* (unregistered) link between two entities. The entities
themselves do not hold links to the edge, so the connector can be garbage collected.

* **Fields:**
  - `uid ()`
  - `label ()`
  - `tags ()`
  - `obj_cls ()`
  - `predecessor (Entity)`
  - `successor (Entity)`
* **Validators:**
  - `_handle_none_tags` » `tags`
  - `_handle_none_tags` » `with_tags`

#### *field* predecessor *: Entity* *[Required]*

#### *field* successor *: Entity* *[Required]*

#### has_tags(\*tags)

Condition querying based on tags, enhancing search and categorization.

* **Return type:**
  `bool`

#### *field* uid *: UUID* *[Optional]* *(name 'uid_')*

Unique identifier for each instance for registries and serialization.

#### *field* label *: Optional[str]* *= None* *(name 'label_')*

A short public identifier, usually based on a template name or a truncated uid hash if unspecified, may require uniqueness in some contexts.

#### *field* tags *: Tags* *[Optional]*

Mechanism to classify and filter entities based on assigned characteristics or roles.

#### *field* obj_cls *: Optional[ClassName]* *= None*

The ability to self-cast on instantiation is actually granted by `SelfFactorying`, but the trigger field is included in the base class documentation because in practice, all Entities are self-casting.
