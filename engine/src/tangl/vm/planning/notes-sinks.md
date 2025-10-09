Sinks, Softlocks, and Escape Hatches
=====================================

Valid Sinks (Intentional Endpoints)
------------------------------------

A **sink node** is an intentional structural endpoint defined by the author.
Sinks represent narrative completion—they may be "good" or "bad" endings,
but they are **complete**.

**Characteristics:**

- Explicitly marked in structural domain: ``domain.sink_nodes``
- Has rendering content (death scene, victory text, etc.)
- May trigger achievements, statistics, replay prompts
- Represents fulfilled author intent

**Example: Death as Valid Sink:**

.. code-block:: yaml

    dragon_encounter:
      choices:
        - fight_with_sword:
            requires: has_sword
            leads_to: dragon_battle
        - fight_barehanded:
            requires: null  # Always available
            leads_to: heroic_death  # Sink node
            metadata:
              achievement: "Foolish Bravery"
              can_replay: true

The player **chose** certain death. This is narratively complete and
satisfying (in a dark way). The author intended this path.

Softlocks (Unintentional Dead Ends)
------------------------------------

A **softlock** occurs when no forward progress is possible due to
unsatisfied requirements and no valid sink is reachable.

**Characteristics:**

- NOT marked as sink (unintentional)
- No valid outgoing edges satisfy requirements
- No rendering content (structural gap)
- Represents authoring error or unexpected state

**Example: Accidental Softlock:**

.. code-block:: yaml

    dragon_cave:
      choices:
        - fight_dragon:
            requires: has_sword  # Player doesn't have sword
            # No other options!

Player is stuck. No death scene, no content, no way forward. This is a **bug**.

Prevention Strategy
-------------------

**Forward progress guarantee:**

    At every non-sink node, at least one of the following must be true:
    
    1. At least one outgoing edge is currently satisfiable
    2. At least one requirement can be provisioned within narrative rules
    3. A reset affordance is available as escape hatch

**PLANNING phase responsibilities:**

.. code-block:: python

    def ensure_forward_progress(cursor, domain):
        # Check 1: Any edges currently satisfiable?
        if has_satisfiable_edge(cursor):
            return True
        
        # Check 2: Can we provision to satisfy an edge?
        if can_provision_for_any_edge(cursor, domain):
            provision_and_mark_available(cursor)
            return True
        
        # Check 3: Is reset allowed?
        if domain.allows_reset:
            provision_reset_affordance(cursor)
            return True
        
        # True softlock: fail loudly
        raise SoftlockError(f"No forward progress from {cursor}")

Escape Hatches: Reset Affordances
----------------------------------

Like "unstuck" commands in 3D games, reset affordances provide emergency
exits from softlock situations.

**Implementation:**

.. code-block:: python

    class ResetAffordance(Affordance):
        """Emergency escape hatch for stuck players."""
        
        def available(self, ns: NS) -> bool:
            # Only show if no other valid choices
            cursor = ns["cursor"]
            other_choices = [
                e for e in cursor.edges_out(ChoiceEdge)
                if e.available(ns) and e != self
            ]
            return len(other_choices) == 0
        
        def execute(self, ctx: Context) -> Node:
            # Return to last checkpoint
            return ctx.graph.get_last_checkpoint()

**When to use:**

- Testing/debugging: always enable during development
- Published stories: use sparingly, signals authoring gap
- Procedural content: may be necessary due to generation limits
- Player agency: some authors embrace "you can always restart"

**Author control:**

.. code-block:: yaml

    chapter_domain:
      softlock_prevention:
        allow_reset: true
        checkpoint_strategy: "scene_entry"  # or "manual_save"
        reset_message: "Return to cave entrance?"

Design Philosophy
-----------------

**Intentional failure is narrative:**
    Death, capture, betrayal—these are **sinks**, not softlocks.
    They complete a story arc (even if tragic).

**Unintentional blocking is a bug:**
    "You need a sword but can't get one" is a **softlock**.
    This breaks flow and should never ship.

**The superposition view:**
    The fabula contains all possible threads. Some threads end in sinks
    (intentional). Softlocks are threads that end in void (unintentional).
    Planning ensures every thread from source→{any sink} is navigable.

See Also
--------
- :ref:`resolution-frontier` – Forward-looking planning
- :ref:`structural-domains` – Chapter/scene/book stacking
- :ref:`dependency-resolution` – Provisioning strategies