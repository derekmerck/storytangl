`tangl.vm`
==========

Interpreter/virtual machine for graph evolution.

The vm evolves and grows the feature graph from a root node, maintaining a consistent, coherent state of local data and interdependencies.

The first 3 layers: Identity, Topology, and Capability, are provided by `tangl.core`.

## Layer 4: Resolution
Frame, Context, Planning, Event-Sourcing

- a graph, a pointer to an anchor node (i.e., the program counter), and the node's scoped capabilities make a **Frame** for the vm
- each cursor update provokes a cascade of nested phase handler invocations that validate, extend, and navigate the resolution frontier
- the **Planner** is a specialized handler that handles topology updates by creating, modifying, or linking nodes on the graph
- graph mutations are tracked with a replayable, **Event-Sourced** process

---

`tangl.vm` is a simple application module, its members should ONLY depend on:
- **core**
- **utils**