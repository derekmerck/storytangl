Core
===========

All classes in the engine fall into one of these three categories:

- Entity, the basic mutable data object, including Node, Graph, Singleton and subclasses
- Handler, a stateless collection of class-methods
- Manager or Registry, a stateful object that can act as a pre-processor or data collection for handlers


Entities
--------

All entities use Pydantic for configuration and validation.

.. automodule:: tangl.entity.entity

There are 3 basic variants of Entities.

- Singleton Entities, immutable shared reference objects
- Node Entities, carry parent/child relationships to create DAGS
- Graph Entities, carry collections of nodes that make up multiple DAGS

### Singleton Entity

.. automodule:: tangl.entity.singleton

### Node and Graph

Node adds parent/child relationships to Entities.  Nodes nodes only carry
_references_ to other nodes and use a shared Graph object to dereference
them as needed.  Thus, node objects must always be used in conjunction with
graph objects.

.. autoclass:: tangl.graph.node.Node
.. autoclass:: tangl.graph.node.Graph

### Factory

A specialized Singleton Entity that provides three methods:
  - create_node
  - create_graph
  - create_factory

.. automodule:: tangl.graph.factory


Mixins and Handlers
-------------------

### Entity Mixins

Any Entity subclass can use these mixins.

- Namespace, carry scoped variables for computation and rendering
- Renderable, carry text and other objects that can be formatted for output
- Conditional and HasEffects, carry and evaluate or execute runtime statements
- Templated, can inject collections of default values into the entity-creation process

.. automodule:: tangl.entity.mixins.namespace

.. automodule:: tangl.entity.mixins.available

.. automodule:: tangl.entity.mixins.renderable

.. automodule:: tangl.entity.mixins.conditional

.. automodule:: tangl.entity.mixins.effects

.. automodule:: tangl.entity.mixins.templated

### Singleton Entity Mixins

.. automodule:: tangl.entity.mixins.instance_inheritance

### Node Mixins

Node mixins provide features pertaining to DAG relationships

- Traversable, can be navigated and bookmarked by the GraphHandler
- Associating, can handle transient peer-to-peer children
- SingletonWrapper, use SingletonEntities as nodes with mutable instance variables

.. automodule:: tangl.graph.mixins.traversal

.. automodule:: tangl.graph.mixins.cascading_namespace

.. automodule:: tangl.graph.mixins.associating

.. automodule:: tangl.graph.mixins.wrapped_singleton

### Graph Handlers and Mixins

Graph mixins are for handling traversal and queries.

.. automodule:: tangl.graph.mixins.traversal


Managers
--------

### Plugin Manager

.. automodule:: tangl.graph.mixins.plugins

.. automodule:: tangl.plugin_spec.plugin_spec

### Graph Storage Manager

A Manager object that supports flexible storage and serialization strategies for Graphs, Nodes, and Singleton Entities.

.. automodule:: tangl.persistence

.. automodule:: tangl.graph.structuring
