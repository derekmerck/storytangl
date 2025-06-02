`tangl.core.entity`
------------------

Basic vocabulary for describing any element in the framework

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

**Graph**
- A registry of nodes and edges
- Node and edge topology provide _shape features_

**Node**
- An entity that lives on a Graph and may be connected to other Nodes by Edges

**Edge**
- An entity that lives on a Graph and connects a source node to a destination node
