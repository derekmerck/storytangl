Edge Projection via Structural Domains
=======================================

Edges represent relationships between nodes. In narrative contexts, certain
edges (dependencies, affordances, roles) need to be **visible in the namespace**
so content can reference them symbolically.

The Problem
-----------

A scene might have a "villain" role (dependency edge) that gets bound to a
specific actor node during planning. Content blocks in that scene need to
reference ``{{villain.name}}`` without knowing which specific actor fills
the role.

**Challenge:** How do edges become namespace entries without coupling
``tangl.core`` to ``tangl.vm`` planning concepts?

**Solution:** Structural domains (subgraphs, scenes, chapters) are responsible
for projecting their edges into ``vars`` when contributing to scope.

Architecture
------------

**Core Provides:**
    - :class:`~tangl.core.domain.Domain` – Base class with ``vars`` dict
    - :class:`~tangl.core.domain.DomainSubgraph` – Structural domain grouping nodes
    - :class:`~tangl.core.domain.Scope` – Namespace builder from active domains

**Application Domains Implement:**
    - Logic to populate ``vars`` with edge projections
    - Refresh mechanisms when edges change

Example: Scene Domain with Role Projection
-------------------------------------------

.. code-block:: python

    from tangl.core import DomainSubgraph, Node
    from tangl.vm.planning import Dependency
    
    class SceneDomain(DomainSubgraph):
        """Structural domain that projects role/setting edges into namespace."""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._base_vars = dict(self.vars)  # Save author-defined vars
            self.refresh_edge_projections()     # Add edge projections
        
        def refresh_edge_projections(self):
            """Update vars to include current edge destinations/sources.
            
            Called after planning phase to ensure namespace reflects newly
            bound dependencies and affordances.
            """
            # Start with author-defined vars
            projected = dict(self._base_vars)
            
            # For each member node, project its edges
            for member_id in self.member_ids:
                member = self.graph.get(member_id)
                if member is None:
                    continue
                
                # Dependency edges: {label: destination}
                for edge in member.edges_out(is_instance=Dependency):
                    if edge.label and edge.satisfied:
                        projected[edge.label] = edge.destination
                        projected[f"{edge.label}_satisfied"] = True
                    elif edge.label:
                        projected[f"{edge.label}_satisfied"] = False
                
                # Affordance edges: {label: source}
                # (Similar pattern for affordances if needed)
            
            self.vars = projected

Usage in Narrative Flow
------------------------

**Author defines scene with roles:**

.. code-block:: yaml

    # In tangldown or scene template
    scene:
      id: tavern_scene
      roles:
        villain:
          identifier: "antagonist"
          policy: EXISTING
        bartender:
          identifier: "npc_bartender"
          policy: CREATE
          template:
            obj_cls: Actor
            name: "Gruff Bartender"

**Planning phase resolves roles:**

.. code-block:: python

    # During PLANNING at approach-to-tavern node:
    frame.run_phase(P.PLANNING)
    # → Finds existing "antagonist" actor, binds to villain role
    # → Creates new "npc_bartender" actor, binds to bartender role
    
    # Refresh domain projections
    for domain in frame.context.scope.active_domains:
        if isinstance(domain, SceneDomain):
            domain.refresh_edge_projections()
    
    # Invalidate scope cache
    frame.context.invalidate_scope_cache()

**Content blocks reference roles:**

.. code-block:: markdown

    ## Tavern Interior
    
    You enter the dimly lit tavern. {{villain.name}} glares at you from
    the corner booth. {{bartender.name}} nods as you approach the bar.

**Rendered output:**

.. code-block:: text

    You enter the dimly lit tavern. Lord Darkness glares at you from
    the corner booth. Gruff Bartender nods as you approach the bar.

If the villain dies and is replaced later, the scene domain can rebind
the "villain" role to a different actor node, and all content automatically
references the new villain.

Lifecycle Hooks
---------------

**When edge projections update:**

1. **After PLANNING phase:**
   - Dependencies/affordances are resolved
   - Structural domains should refresh edge projections
   - Context scope cache must be invalidated

2. **After UPDATE phase:**
   - Edge states may change (satisfaction, provider changes)
   - Structural domains should refresh edge projections
   - Context scope cache must be invalidated

**Pattern in Frame:**

.. code-block:: python

    def follow_edge(self, edge):
        # ... VALIDATE phase ...
        
        self.run_phase(P.PLANNING)
        self._refresh_structural_domains()
        self.context.invalidate_scope_cache()
        
        # ... PREREQS, UPDATE, JOURNAL phases ...
        
        self.run_phase(P.UPDATE)
        self._refresh_structural_domains()
        self.context.invalidate_scope_cache()
        
        # ... FINALIZE, POSTREQS phases ...
    
    def _refresh_structural_domains(self):
        """Notify structural domains to update edge projections."""
        for domain in self.context.scope.active_domains:
            if hasattr(domain, 'refresh_edge_projections'):
                domain.refresh_edge_projections()

Design Rationale
----------------

**Why not project edges in core.Scope?**
    - Would couple core to vm.planning (Dependency, Affordance classes)
    - Different applications have different edge semantics
    - Domains are the right abstraction for application-level projection

**Why not make edges self-projecting?**
    - Tried this in earlier versions, led to tight coupling
    - Domains provide better lifecycle management
    - Allows batched updates rather than per-edge invalidation

**Why refresh in Frame rather than auto-refresh on access?**
    - Performance: avoids recomputing on every namespace access
    - Predictability: explicit refresh points in phase pipeline
    - Debuggability: clear when projections update

**What if I don't need edge projection?**
    - Simple applications can ignore this mechanism
    - Only relevant when symbolic references to edges are needed
    - CLI adventures might not need it; complex RPGs will

Constraints and Guarantees
---------------------------

**Structural domains must:**
    - Implement ``refresh_edge_projections()`` if they project edges
    - Populate ``self.vars`` with edge labels as keys
    - Handle missing/unsatisfied edges gracefully

**Frame/Context must:**
    - Call ``_refresh_structural_domains()`` after mutation phases
    - Call ``invalidate_scope_cache()`` after domain refresh
    - Ensure phases see consistent namespace state

**Applications must:**
    - Register structural domains on appropriate nodes/subgraphs
    - Ensure edge labels don't collide with domain var names
    - Document which edges are projected and when

See Also
--------
- :class:`~tangl.core.domain.Scope` – Namespace construction
- :class:`~tangl.core.domain.DomainSubgraph` – Structural grouping
- :mod:`tangl.vm.planning` – Dependency/affordance resolution
- :class:`~tangl.vm.frame.Frame` – Resolution orchestration

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