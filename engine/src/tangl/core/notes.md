`tangl.core`
============

Basic vocabulary for describing the shape and basic behaviors of any element in the framework.

Entity and low-level modules such as Graph, Handler, Domain, Provision that depend only on Entity and one another. 

Modules should not depend on other application- or task-specific tangl subpackages.

**Entity**
- Base class for all managed objects
- Minimal, universally identifiable unit
- Has uid, tags, metadata
- Can structure, unstructure
- Provides _data features_
- Robust feature-match function for search, selection
- May be gated by a predicate function/handler

**Registry**
- Collection of related entities
- Searchable by feature

**Singleton**
- Immutable entities with unique names that can be shared within a semantic scope

**Graphs**
- A Graph is a registry of GraphItems, Nodes, Edges, and Subgraphs
- GraphItem topology provide _shape features_
- Nodes may be connected by Edges
- Subgraphs are collections of Nodes that 

**Edge**
- An entity that lives on a Graph and connects a source node to a destination node

**Subgraph**
- An entity that lives on a Graph and gathers multiple nodes into a single unit
- When nodes are also subgraphs, they can provide a scale-space shape representation

**Domains and Scopes**
...

**Provisioning**
...

