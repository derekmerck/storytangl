StoryTangl v2.11
========

- latest python
- env managed with poetry
- source control with git
- testing with pytest
- docs with sphinx/myst


Contents
--------
- Core Classes
- Core Handlers
- Persistence
- Plugins
- Story Classes
- Media
- World Scripting
- Service API


Core Class Types
----------------

### Entity
- basic managed object
- has a uid
- serializes as class and dict
- deserializes to proper class

- may be lockable
- may provide a namespace of local vars
- may test availability w eval conditions
- may allow updating namespace w exec effects
- may provide a text field and rendered output

### SingletonEntity(Entity)
- has a unique instance name
- serializes as class and name
- deserializes to class and instance

### InheritingSingleton(Singleton)
- has a reference to a singleton of the same class
- unset attributes are derived from the reference instance

### Graph(Entity)
- registry of nodes
- includes a cursor indicating the currently active node
- serializes nodes in registry normally
- propagates its namespace to its nodes

### Node(Entity)
- has a graph
- has a parent
- stores and serializes node children and parent as uids (avoid loops)
- converts node children and parent on access via the graph

- may propagate its namespace to its children
- may propagate its availability conditions to its children
- may be connected to other nodes via traversable Edges
- may be associated with other nodes via a non-parent, peer relationship

### Edge(Entity)
- directed connection between two nodes
- predecessor is parent
- successor is stored and serialized as a uid or a name
- converts successor on access via the graph (need not exist when defined)
- determine availability according to both predecessor and successor ns

### Subgraph(Node)
- a bag of nodes that can be treated as a single node at some scale
- may provide scoped or delegated child availability
- may provide scoped or delegated child namespaces
  (such as sharing roles in scene namespaces)

### WrappedSingletonNode(Node)
- has a reference to a singleton of the wrapped class
- inherits properties and values from its reference singleton


Core Feature Handlers
---------------------

### Condition Handler
- process evals on an entity's namespace

### Availability Handler
- check conditions
- manage 'forced' unlocks when dev jumping to unavailable node

### Effect Handler
- process exec's in an entity's namespace

### Namespace Handler
- gather variables for an entity's namespace

### Traversal Handler
- follow edges while executing node entry and exit strategies
- update graph cursor

### Rendering Handler
- create output from an entity

### Association Handler
- update node-to-node relationships for peering and reparenting
