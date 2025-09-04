`tangl.core.solver`
-------------------
vocabulary for working with indeterminate interdependent-feature spaces
resolving a lane in an indeterminate space with incremental graph representation of stable dependencies
opinionated implementations for specific node and edge types and a graph resolver.

### Abstract Feature Graph

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

### Abstract Feature Handlers

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

**Provisioning**
- Unresolved dependency edges must be annotated with requirement constraints for the destination's data and shape features, and the provisioners scope-range
- **Provisioners** are special handlers that can perform graph editing operations (FIND, FIND_AND_MODIFY, CREATE, CREATE_AND_MODIFY, or WAIVE) to recruit or create nodes with appropriate data features
- The graph can be dynamically reconfigured, but no dependency edges may be broken once a node is visited
- Conflicting resolution strategies are resolved by edit distance, which penalizes topology change (introducing new nodes vs. modifying existing ones), scope-distance of the provisioner, and priority order
- Dependency edges may be UNRESOLVED (no destination, un-tested), RESOLVED (destination assigned), RESOLVED_BUT_GATED (destination assigned but fails predicate), RESOLVED_AND_FROZEN (assigned and visited), or UNRESOLVABLE (no destination, tested)

```
provision(node, domains)
    enumerate feasible edit actions given local constraints.
    compute minimal-cost edits recursively, using memoization to avoid recomputation.
```

**Trace Rendering**
- The _render handler_, a meta-handler that creates trace fragments from a resolved entity's state as part of flow control

### Solvers

**Feed-forward Resolution**
- Generative untangle, discover a stable, untangled lane
- Incrementally advance a solution frontier
```
forward_resolve(graph, cursor, trace, domains):
    resolve all dependencies (optimal edits)
    render trace node from resolved state
    advance cursor (update frontier)
```
- Intent → IR → Graph → Trace
```
Script (DSL, YAML, etc.)
    └──compile──> Declarative IR (abstract capabilities, rules, dependencies, templates)
        └──instantiate──> Dependency Graph (resolved nodes/resources at runtime)
            └──traverse──> Trace (runtime linearization)
                └──present──> Client/User
```

**Feed-backward Validation**
- Discriminative untangle, can this state be untangled
```
backward_verify(graph, sink, cursor, domains):
    recursively check all upstream dependencies reachable and satisfiable
    prune unreachable paths
```
