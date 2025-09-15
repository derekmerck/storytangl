`tangl.core`
============

Basic vocabulary for describing the shape and basic behaviors of any element in the framework.

vocabulary for working with indeterminate interdependent-feature spaces

Entity and low-level, abstract modules such as Graph, Handler, Domain/Scope, and Provisioner that depend only on Entity and one another. 

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

### Abstract Feature Graph

- A Graph is a registry of **GraphItems**, **Nodes**, **Edges**, and **Subgraphs**
- GraphItem topology provide _shape features_
- Nodes may be connected by Edges
- Subgraphs are collections of Nodes that form a structural domain
- When nodes are also subgraphs, they can provide a scale-space shape representation

provides:
- _structure_, _resource_, _content_ type nodes and subgraphs
- _choice_, _dependency_, _blame_ type edges
- _dependency_ (open destination), and _requirement_ (open source) type dynamic edges and provisioning
- _journal_ for managing lists of content nodes

- Edge subtype by purpose: 
  - **Choice** (flow control path)
  - **Dependency** (resource requirement)
  - **Trace** (output sequencing)
  - **Blame** (audit trail)
  - 
- Node Subtype by function:
  - **Structure** (directed control flow)
  - **Resource** (reusable functionality or data)
  - **Trace fragment** (immutable snapshots of state following flow)

**Subgraphs**
- Nodes may partition into embedded communities of related nodes
- All structural nodes live on a subgraph with a _source_ and a _sink_
- Any structural node may expand to contain a subgraph of structural nodes with their own _source_ and _sink_, thus providing a _hierarchical scale space_
- Resource nodes may _anchor_ a subgraph of related resources and structures, recruiting the anchor generally recruits the entire _resource space_
- Trace fragments are organized on a linear manifold within the graph that follows the control flow. They correspond directly to structure nodes, so can be expanded or aggregated into a similar hierarchy of sub-sequences

```
book (top-level graph)
├── chapter/act (subgraph/module)
│   ├── scene (structure-subgraph)
│   │   ├── verse/block (single structure node)
│   │   │   └── line/fragment (single trace fragment)
```

### Dispatch

- Handlers and HandlerRegistries
- JobReceipt
- Domains and Scopes

**Scoped Context**
- Mapping of identifiers to data and shape features, handlers, and provisioners
- Organized by node (local), graph scales (non-local), semantic scopes (namespaces, e.g., domain, user, global, class mro), with more relevant (closer) values shadowing less relevant (distant) values with the same identifier
- Similar to composition of transforms in hierarchical shape models, provides a local view of the global state

```
global
├── domain
│   ├── mod/user overrides
│   └── shared resources (singletons)
└── local graph/subgraph
    └── node/block context
```

**Domain**
- Domains are shared capabilities, they publish a namespace layer (vars) and handlers
