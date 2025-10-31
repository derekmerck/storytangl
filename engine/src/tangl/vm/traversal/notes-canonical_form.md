Canonical Single-Source/Single-Sink Form
=========================================

**Design Principle:** Every structural domain has exactly one abstract
source node and one abstract sink node, regardless of how many real
entry/exit points exist.

Why Canonical Form?
-------------------

Multiple sources and sinks complicate path analysis:

- "Can I reach an exit?" becomes "Can I reach any of N exits?"
- "Did I enter validly?" becomes "Did I come from any of M entries?"
- Reachability checks are O(sources × sinks × nodes)

With canonical form:

- All entries route through one abstract SOURCE
- All exits route through one abstract SINK
- Reachability checks are O(1) with preprocessing
- Graph algorithms become standard single-source/single-sink flows

Implementation
--------------

**Abstract source/sink nodes are hidden from players:**

.. code-block:: python

    scene = SceneDomain(
        graph=g,
        label="tavern",
        entry_nodes=[front_door, back_door, window],  # Multiple entries
        exit_nodes=[leave_front, leave_back, arrested],  # Multiple exits
    )
    
    # Creates hidden structure:
    # SOURCE → [front_door, back_door, window] → content → 
    #   → [leave_front, leave_back, arrested] → SINK

**Real entries/exits linked to abstract nodes:**

.. code-block:: python

    # Auto-generated during domain construction
    ChoiceEdge(source=scene.SOURCE, destination=front_door)
    ChoiceEdge(source=scene.SOURCE, destination=back_door)
    ChoiceEdge(source=scene.SOURCE, destination=window)
    
    ChoiceEdge(source=leave_front, destination=scene.SINK)
    ChoiceEdge(source=leave_back, destination=scene.SINK)
    ChoiceEdge(source=arrested, destination=scene.SINK)

Softlock Detection
------------------

With canonical form, softlock detection is simple:

.. code-block:: python

    def is_softlocked(cursor: Node, domain: StructuralDomain) -> bool:
        # Just check: can cursor reach the sink?
        return not cursor.can_reach(domain.sink)

No need to check N different exit nodes—just check the one canonical sink.

Nested Domains
--------------

Domains compose cleanly by linking sinks to sources:

.. code-block:: python

    chapter = ChapterDomain(...)
    scene_a = SceneDomain(...)
    scene_b = SceneDomain(...)
    
    # Link chapter entry to first scene
    ChoiceEdge(source=chapter.source, destination=scene_a.source)
    
    # Link scene A exit to scene B entry
    ChoiceEdge(source=scene_a.sink, destination=scene_b.source)
    
    # Link scene B exit to chapter exit
    ChoiceEdge(source=scene_b.sink, destination=chapter.sink)

Result: One clean path from chapter.source → chapter.sink, with
intermediate scene structure hidden at the chapter level.

Performance
-----------

**Reachability caching:**

After graph mutations (PLANNING, UPDATE), reachability must be recomputed:

.. code-block:: python

    # After provisioning new nodes/edges
    for node in affected_nodes:
        node.invalidate_reachability()

Lazy recomputation happens on first query:

.. code-block:: python

    # This triggers BFS if cache is dirty
    can_reach = cursor.can_reach(domain.sink)

Amortized cost: O(V + E) per mutation, O(1) per query.

See Also
--------
- :ref:`softlock-prevention` – Using canonical form for validation
- :ref:`structural-domains` – Domain composition patterns