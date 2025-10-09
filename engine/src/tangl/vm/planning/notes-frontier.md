Resolution Frontier
===================

The **resolution frontier** is the set of structural nodes and edges immediately
reachable from the current cursor position that determine what can happen next
in the narrative.

Temporal Model
--------------

Resolution operates in a **forward-looking** manner during the PLANNING phase:

.. code-block:: text

    Step N-1: At Node A
      ├─ VALIDATE: Is A valid?
      ├─ PLANNING: What does B need? (look ahead)
      │   └─ Resolve dependencies/affordances for NEXT nodes
      │   └─ Mark edges A→B as satisfied/unsatisfied
      ├─ PREREQS: Auto-follow any satisfied edges?
      ├─ (Player chooses edge A→B)
      ├─ UPDATE: Apply effects TO Node A (before leaving)
      ├─ JOURNAL: Render Node A's content
      ├─ FINALIZE: Commit mutations/events
      └─ POSTREQS: Auto-follow any satisfied edges?

    Step N: Moved to Node B
      ├─ VALIDATE: Is B valid?
      ├─ PLANNING: What does C need? (look ahead from B)
      └─ ...

Key Insights
------------

**Planning is predictive, not reactive:**
    The PLANNING phase at Node A resolves requirements for **destination nodes**
    (B, C, D, etc.) reachable from A. This determines which edges out of A are
    ``satisfied`` and therefore available as choices.

**Edge satisfaction affects current node rendering:**
    After planning, the number and state of satisfied outgoing edges changes
    how Node A should be presented. For example:
    
    - "You see 3 doors: red (locked), blue (open), green (open)"
    - The door states depend on whether their destination dependencies are satisfied
    
**Namespace must reflect edge state:**
    Handlers in UPDATE/JOURNAL phases need to see which edges are satisfied.
    This requires invalidating cached scope/namespace after PLANNING completes.

Phases and Their Responsibilities
----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 15 40 45

   * - Phase
     - Purpose
     - Mutations?
   * - VALIDATE
     - Check cursor is valid, conditions met
     - No
   * - PLANNING
     - Look ahead: resolve dependencies for **next** nodes
     - Yes (graph structure)
   * - PREREQS
     - Auto-follow satisfied edges (conditional jumps)
     - No (returns edge)
   * - UPDATE
     - Apply effects to **current** node (before leaving)
     - Yes (node state)
   * - JOURNAL
     - Render current node content for presentation
     - No (returns fragments)
   * - FINALIZE
     - Commit events, cleanup, patch generation
     - Yes (if event-sourced)
   * - POSTREQS
     - Auto-follow satisfied edges (post-action jumps)
     - No (returns edge)

Namespace Invalidation Contract
--------------------------------

Because PLANNING and UPDATE mutate the graph, the ``Context.scope`` cache
becomes stale. Phases that follow must see updated state:

**After PLANNING:**
    - New nodes may have been provisioned
    - Edge satisfaction states have changed
    - Namespace must reflect updated frontier

**After UPDATE:**
    - Node attributes may have changed
    - Resource states (inventory, flags) updated
    - Namespace must reflect new state

**Implementation:**
    Call ``ctx.invalidate_scope_cache()`` after mutation phases::

        self.run_phase(P.PLANNING)
        self.context.invalidate_scope_cache()  # Rebuild scope for later phases
        
        self.run_phase(P.UPDATE)
        self.context.invalidate_scope_cache()  # Rebuild scope for JOURNAL

See Also
--------
- :class:`Context` – Frozen execution context per step
- :class:`Scope` – Cached namespace builder
- :mod:`tangl.vm.planning` – Dependency resolution mechanics