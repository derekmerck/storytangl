Dereferencing GraphItems
------------------------

**GraphItems** use properties with implicit registry access::

    edge.source          # returns Node via self.graph.get()
    edge.destination     # property, no args

This enables WatchedRegistry to intercept all cross-item access and supports equality by id rather than recursive checks.

**Records** use methods with explicit registry parameter::

    record.blame(registry)  # returns Entity via passed registry

This preserves record independence from graph topology and
maintains immutability (no cached references).

Both patterns store only UUIDs during serialization.
