tangl.core.graph
=================

Connected entity structure representing the latent story space.

The graph package implements a directed property graph model with:

- **Nodes**: Core entities carrying state and capabilities  
- **Edges**: Typed connections between nodes with semantic labels
- **Traversal**: Operations for moving through the graph  

StoryTangl graphs are the backbone of narrative representation, where:
- Story elements (scenes, actors, objects) are nodes
- Relationships (ownership, traversal options) are edges
- State is distributed locally rather than in a global dictionary

This implementation achieves higher performance and cleaner semantics
by using adjacency lists and typed edges, making traversal patterns
explicit while keeping the core data structure lightweight.

Unlike traditional property graphs, StoryTangl's graph is designed
specifically for phased traversal driven by the cursor system.

See Also
--------
RedirectCap, ContinueCap: Specialized capability factories for the Choice service