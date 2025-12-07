Dereferencing GraphItems
========================

**GraphItems** use _properties_ with implicit registry access::

    edge.source          # returns Node via self.graph.get()
    edge.destination     # property, no args

**Records** don't have `self.graph`, so they use _methods_ with explicit registry parameter::

    record.blame(registry)  # returns Entity via passed registry

**Collections & Queries** return fresh iterators::

    subgraph.members              # Iterator[GraphItem], not cached
    node.edges_in()               # Iterator[Edge], fresh lookup
    registry.find_all(label='x')  # Iterator[Entity], filtered

All iterators are **single-use**. Materialize explicitly if multiple
passes needed::

    # Single iteration: direct use
    for member in subgraph.members:
        process(member)
    
    # Multiple iterations: materialize first
    members = list(subgraph.members)
    first_pass(members)
    second_pass(members)

This pattern ensures queries always reflect current state and avoids
hidden cache invalidation complexity.
