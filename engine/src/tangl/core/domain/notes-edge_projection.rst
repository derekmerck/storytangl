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
