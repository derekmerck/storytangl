tangl.core.graph
=================

Connected entity structure representing the latent story space.

The graph package implements a directed property graph model with:

- **Nodes**: Core entities carrying state and capabilities  
- **Edges**: Typed connections between nodes with semantic labels
- **Graph**: A registry of nodes and edges 

StoryTangl graphs are the backbone of narrative representation, where:
- Story elements (scenes, actors, objects) are nodes
- Relationships (ownership, traversal options) are edges
- State is distributed locally rather than in a global dictionary

See Also
--------
RedirectCap, ContinueCap: Specialized capability factories for the Choice service that creates narrative paths