`tangl.core`
============

Basic vocabulary and low-level abstractions for describing the shape and basic behaviors of any element in the framework.

## Layer 1: Identity

**Entity**
- Minimal base class for all managed objects
- Has uid, tags, data, and metadata
- Can structure, unstructure
- Provides _data features_
- Robust feature-match function for search
- May be gated by a predicate function/handler

**Registry**
- Collection of related entities
- Searchable by feature

**Record**
- Frozen entities with monotonically increasing sequence numbers automatically assigned
- **StreamRegistry** provides order, bookmarks, and channel selection on top of Registry. 

**Singleton**
- Immutable entities with unique names that can be shared within a semantic scope
- May have instance inheritance
- May be wrapped as shared references in Node instances

## Layer 2: Topology
Graph, Node, Edge, Subgraph, Fragment

- A Graph is a registry of **GraphItems**: **Nodes**, **Edges**, and **Subgraphs**
- GraphItem topology provides _shape features_
- Nodes may be connected by edges
- Subgraphs are collections of nodes that form a structural domain
- Fragments carry pre-image output and control information about a graph process, they are sequential, frozen, and may link indirectly to graph items by uid, although they are not proper GraphItems themselves

## Layer 3: Capability
Handler, JobReceipt, Domain, Scope

**Dispatch**
- Common api for actions on entities
- Internal **HandlerFunc** takes a caller and namespace, produces a result
- Handler creates a **JobReceipt** with audit info and the result for each invocation
- **HandlerRegistry** holds related handlers and can chain activations for complex, multi-handler jobs

**Domain**
- A shared capability bundle that publishes a namespace of identifiers with values, and a handler registry for subscribers
- Structural domains are inferred from the graph topology (a node's ancestor subgraphs), affiliate domains are joined explicitly with tags or other selectors
- Scopes are ordered structural and affiliate domain layers that bundles all capabilities visible to a single 'anchor' node on a given graph

---

`tangl.core` is an abstract dataclass module, its members should ONLY depend on:
- **utils**
