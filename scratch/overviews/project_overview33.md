StoryTangl - Project Mission (v3.3)
===================================

A high dimensional latent 'story space' that can represent all of the possible concepts and realizations that apply to a particular story form.

The form domain is explored by means of a graph of discrete structure and concept nodes. 

An initial structure node is generated and the initial graph cursor is set there.  

As structure nodes are established, related concepts must be recruited or created, possible paths forward are discovered or created, and the current plot point is projected onto a linear narrative 'journal' manifold in the space.

Structure node may _require_ that certain concepts be _provided_ in their scope.

As structure nodes are traversed, a resolution agent will attempt to match existing providers with unmet requirements, exploring increasingly distant scopes, from node-local, to node-adjacent, to graph-wide, to domain-wide.  

If no satisfactory provider can be found, a new provider will be instantiated if possible by referring to a (similarly scoped) registry of provider templates, and linked into the node's context.  New nodes may themselves come into existence with requirements which are dealt with recursively.

Basic Components
----------------

- All objects derive from a common base model, itself based on pydantic BaseModel
- Nodes are general objects with undirected and directed links.  They may only have one parent (incoming link).
- Created nodes may be instances (the shopkeeper, a castle), wrappers around singletons with a local context (blue jacket is open or closed), or simple references to singletons (hp, sword).

- Context is a scoped chain-map-like object.  It is prioritized closest (node-locals) to furthest (domain-defaults)
- Node-scope refers to a node's children and associates
- Ancestor-scope refers to the node's parent chain back to the root of the current subgraph
- Graph-scope (globals)
- Domain-scope refers to shared singleton rules and templates

- Requirements and Provisions are first-class objects.  Requirements have predicates that identify the feature that must be provided, and selectors/criteria/policies that a provider must match to be assigned.

- The graph controller provides a "cursor update" function that moves the cursor along an outgoing edge to a new structure node, resolves the local requirements and then creates a list of new "content fragments", projected output nodes that live on the linear "journal" manifold.

- There are 5 phases in a cursor update:
- gather context
- check for redirection edges before visiting the target
- apply effects on behalf of the target
- attempt to resolve all possible linked structure nodes to determine if they are available or not
- render content fragments for the target, including information about potential paths to linked nodes (choices/actions)
- finalization bookkeeping
- check for continuing edges before blocking on user input

- Nodes, graphs, classes, domains may register capabilities for each of these phases.

- Domain descriptions may be given in a variety of formats, but are compiled into an intermediate abstraction that natively supports the described operations.

