Reference Implementation Outline
--------------------------------

- An interactive fiction engine
- Flexible, easy to author content for, and extensible
- Provides many built-in features and hooks for custom mechanics
- Well documented for users, content authors, and developers
- Simple to set up and use

- Graph Representation - A hypergraph represents complex narrative relationships that go beyond simple node-to-node connections.
- State Efficiency - Use scoped state to handle complex worlds with many locally relevant variables efficiently.
- Content Generation - Support both templated content and integration with LLMs for dynamic content generation.
- Persistence Strategy - Design for efficient serialization/deserialization of potentially large narrative graphs.
- Extensibility - Use a plugin architecture for content templates, conditions, effects, and renderers.


The reference implementation is conceived as a 4-layer app:

- business layer, which implements the ASG principles
- service layer
- data layer
- presentation layer


For our proof of concept, I imagine a story world defined as a graph of interconnected narrative concepts -- in particular cardinal types for, scenes/content blocks, actors, places, and objects/things are all nodes.  Nodes can carry components, or links to other nodes in the form of edges.  Edges between content blocks are narratively traversable.  Edges between content blocks and actors or places are roles and settings respectively.  These may be pre-set or created/defined dynamically.  Things are usually carried by scenes, places, or actors in a sub-component called a wallet.

A story instance is a copy of the graph structure, with references back to the world templates.  The graph may evolve over time away from the template reference, and it will accumulate local information at various nodes as actors change outfits, for example, or scenes are navigated or pruned, or new nodes are dynamically added in according to the base world's rules.

The story instance is managed by the narrative daemon, which takes external input, updates the story instance state, and renders the state update into a candidate linear narrative thread.  Finally, a server/client layer transforms the thread into the final presentation by adding, transforming, and culling elements according to the client's capabilities and preferred formats.

The server and narrative daemon are stateless and can manage many story worlds (templates and rules) and story instances (states) in parallel.  There is also a meta-story layer for a user/reader that aggregates summary data from all story instances belonging to that user for reference within any of their story instances (achievements, unlocks, turns played, etc.).

For a python server implementation, clients could range from a cli or tcl interface that serves a single world and user and manages its own story daemon, to a web client that communicates with a REST server via json and http, to a renpy program with an adapter that sideloads its own story daemon or refers to a remote story daemon via the same REST interface as a web client would.

Technical Stack
---------------
- Language: python ^3.10
- Key Dependencies: pydantic, pillow, markdown, jinja
- Development Tools: poetry, pytest, git, sphinx, drone
- Distribution: pip, docker, pyinstaller

Docs
----

- Uses _sphinx_
- Separate user (author) and developer/api guides
- Extensive docstrings for autodoc

