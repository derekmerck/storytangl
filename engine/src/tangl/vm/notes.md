`tangl.vm`
==========

Interpreter/virtual machine for graph evolution.

resolving a lane in an indeterminate space with incremental graph representation of stable dependencies
opinionated implementations for specific node and edge types and a graph resolver.

`tangl.vm` is a simple application module, its members should ONLY depend on:
- **core**
- **utils**

provides:
- **session** (unit of work, load/save graph, create context, run a tick)
- **context** (process graph->domains->facts, capabilities at anchor)
- **planning** (provisioner, provider, templates, builder, finder)
- **event** log (create/apply update stack)

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
