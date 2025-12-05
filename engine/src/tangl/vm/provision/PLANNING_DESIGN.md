# Planning & Provisioning System Design (v3.7)

**Status:** This document reflects the **actual current implementation** as of v3.7.  
**Last Updated:** December 2025  
**Location:** `engine/src/tangl/vm/provision/` and `engine/src/tangl/vm/dispatch/planning.py`

---

## Executive Summary

StoryTangl's planning system enables **dynamic narrative resolution** by:
- ✅ Provisioning resources on the **frontier** (next nodes) before user choice
- ✅ Detecting and preventing **softlocks** (unresolvable states)
- ✅ Supporting multiple **provisioning strategies** (existing, create, update, clone)
- ✅ Enforcing **hard vs soft requirements** for choice gating
- ✅ Providing **deterministic, cost-based resource selection**

**Key Insight:** Planning happens **in anticipation of movement**, not in response to it. By the time users see choices, all reachable nodes are already resolved (or marked unavailable).

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Architecture Overview](#architecture-overview)
3. [The Planning Cycle](#the-planning-cycle)
4. [Provisioning Mechanics](#provisioning-mechanics)
5. [What's Implemented](#whats-implemented)
6. [What's Missing](#whats-missing)
7. [Integration Points](#integration-points)
8. [Usage Examples](#usage-examples)

---

## Core Concepts

### The Frontier

**The frontier is the set of NEXT structural nodes reachable from the current cursor via ChoiceEdges.**

```python
# Implementation (engine/src/tangl/vm/dispatch/planning.py)
def _iter_frontier(cursor: Node) -> list[Node]:
    """Return frontier destinations reachable from cursor via choices."""
    return [
        edge.destination
        for edge in cursor.edges_out(is_instance=ChoiceEdge)
        if edge.destination is not None
    ]
```

**Example:**
```
Current State:
  cursor = hallway  # Where we are NOW

Frontier (next possible locations):
  frontier = [kitchen, bedroom, basement]
  # Each reached via ChoiceEdge from hallway

Planning Phase:
  - Provisions ALL frontier nodes before user chooses
  - Detects if any node has unsatisfied hard requirements
  - Marks choices as available/unavailable
```

**Fallback:** If no frontier exists (terminal node), planning provisions the cursor itself.

### Structural vs Concept Layers

**Structural Layer (Episodes/Scenes/Blocks):**
- Locations in the story graph
- Form a DAG representing narrative flow
- Traversed during play

**Concept Layer (Characters/Items/Resources):**
- Things referenced by structure
- Shared across multiple scenes
- Created/bound by planning

**Connection Pattern:**
```
[Scene: Kitchen] ──needs──> [Item: Golden Key]
[Scene: Bedroom] ──actor──> [Character: Alice]
[Scene: Basement] ──requires──> [Item: Torch]

(structural)                (concept)
```

### Requirements & Open Edges

**Requirement:** Specification of what's needed and how to obtain it.

```python
Requirement(
    graph=graph,
    identifier="key",                           # What to look for
    criteria={"has_tags": {"key", "item"}},     # Selection criteria
    template={"label": "golden_key", ...},      # How to create if needed
    policy=ProvisioningPolicy.ANY,              # Strategy (see below)
    hard_requirement=True                       # Blocks choice if unmet
)
```

**Provisioning Policies:**
- `EXISTING` - Must find in graph (cheapest: cost=10)
- `CREATE` - Build from template (expensive: cost=200)
- `UPDATE` - Find and modify existing (cost=50)
- `CLONE` - Copy and evolve existing (cost=100)
- `ANY` - Try EXISTING first, fall back to CREATE

**Open Edges:**

**Dependency (Pull Pattern):** Known source, open destination
```python
Dependency(
    graph=graph,
    source_id=locked_door.uid,   # This scene
    destination_id=None,          # To be resolved
    requirement=key_requirement,
    label="needs_key"
)
# "Locked door scene needs a key"
```

**Affordance (Push Pattern):** Open source, known destination
```python
Affordance(
    graph=graph,
    source_id=None,              # To be resolved
    destination_id=dragon.uid,   # This resource
    requirement=scene_requirement,
    label="dragon"
)
# "Dragon can appear in scenes with 'wants_dragon' tag"
```
### Protocol / Constraint-Satisfaction View

The same planning mechanics can be viewed through a more standard
**protocol / CSP** vocabulary. This is useful if you think in terms of
queries, proposals, and commitments:

- **Constraint**  
  Each :class:`Requirement` attached to an open edge (Dependency or
  Affordance) is the VM's constraint object: it combines a *selector*
  (``identifier`` / ``criteria``) with a *provisioning contract*
  (``policy``, ``template``, ``reference_id``, ``hard_requirement``).

- **Selector**  
  The selector surface is the subset of fields used by
  ``Requirement.get_selection_criteria()`` and ``Requirement.satisfied_by()``.
  Anything that can produce equivalent selection criteria and answer
  "does this node satisfy me?" can conceptually play the same role.

- **Proposals (Offers)**  
  Provisioners respond to constraints by emitting
  :class:`ProvisionOffer` instances (and their specializations
  ``DependencyOffer`` / ``AffordanceOffer``). These are *lazy* proposals:
  they describe how the constraint *could* be satisfied, but defer the
  actual work to an accept callback.

- **Negotiation (Planning pass)**  
  The planning layer collects all offers for the frontier, deduplicates
  candidate providers, applies a cost model
  (:class:`ProvisionCost` + proximity), and selects exactly one accepted
  offer per requirement. This is the negotiation step.

- **Commitments**  
  When the selected :class:`PlannedOffer` instances are executed, they
  produce :class:`BuildReceipt` objects. A :class:`PlanningReceipt`
  aggregates these to describe what was actually committed for a given
  planning cycle.

- **Failure modes**  
  ``Requirement.hard_requirement`` plus ``Requirement.is_unresolvable``
  capture the current binary failure semantics: hard unresolved
  requirements are reported and can softlock a frontier; soft ones are
  treated as waived.

This mapping is intentionally descriptive: it names the roles that
existing types already play without changing the implementation.

#### Possible Future Extensions (Not Yet Implemented)

These are design opportunities that fall naturally out of the protocol
view but are *deliberately* deferred until real use cases appear:

- **Selector protocol**  
  Today, anything that wants to behave like a selector reuses the
  ``selection_criteria`` shape and/or ``get_selection_criteria`` /
  ``satisfied_by`` methods. In the future we may introduce a small
  :pep:`544` ``Protocol`` (e.g. ``Selector``) that formalizes this
  surface for better static typing and reuse, without forcing inheritance
  from :class:`Requirement`.

- **Richer failure modes**  
  At present, the only distinction is hard vs soft
  (block vs waive). If a story or μ-layer feature needs finer-grained
  behavior (e.g. "fall back to a different requirement", "log and
  degrade", "escalate to UI"), we can extend the failure semantics with
  a small enum (e.g. ``FailureMode``) and optional fallback requirement
  references. Until a concrete need arises, the simple hard/soft model
  keeps the implementation smaller and easier to reason about.

The core takeaway is that the **constraint → proposals → negotiation →
commitment** pipeline is already encoded in the current types; this
section just names that structure in protocol terms and sketches where
we might extend it later.

---

## Architecture Overview

### Component Layers

```
┌─────────────────────────────────────────────────────────┐
│                     Story Layer                         │
│  (tangl.story.fabula.world, tangl.story.episode)        │
│                                                         │
│  • Compiles scripts into StoryGraph                     │
│  • Creates structural nodes (scenes, blocks)            │
│  • TODO: Wire roles/settings to Dependencies            │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      VM Layer                           │
│  (tangl.vm.frame, tangl.vm.dispatch.planning)           │
│                                                         │
│  • Orchestrates phase pipeline                          │
│  • Triggers planning on frontier                        │
│  • Applies provisioning plans                           │
│  • Aggregates PlanningReceipt                           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 Provision Layer                         │
│  (tangl.vm.provision)                                   │
│                                                         │
│  • Pure provisioning logic (provision_node)             │
│  • Provisioner implementations                          │
│  • Offer generation and selection                       │
│  • Cost-based arbitration                               │
└─────────────────────────────────────────────────────────┘
```

### Key Classes

**Core Types:**
- `Requirement` - What's needed and how to get it
- `Dependency` - Outbound requirement edge (pull)
- `Affordance` - Inbound offer edge (push)

**Provisioners:**
- `GraphProvisioner` - Searches existing nodes
- `TemplateProvisioner` - Creates from templates
- `UpdatingProvisioner` - Modifies existing nodes
- `CloningProvisioner` - Duplicates and evolves nodes
- `CompanionProvisioner` - Special-case for companions

**Offers & Results:**
- `DependencyOffer` / `AffordanceOffer` - Lazy proposals
- `BuildReceipt` - Result of accepting one offer
- `ProvisioningPlan` - Sequence of PlannedOffers
- `ProvisioningResult` - Per-node provisioning summary
- `PlanningReceipt` - Aggregate summary for the step

---

## The Planning Cycle

Planning executes in two phases: **PLANNING** (phase 30) and **FINALIZE** (phase 50).

### Phase 1: PLANNING (Collect and Plan)

**Handler 1: `_planning_orchestrate_frontier` (Priority: FIRST)**

```python
def _planning_orchestrate_frontier(cursor: Node, *, ctx: Context):
    """Provision all frontier nodes using the pure resolver."""
    
    # 1. Get frontier nodes
    frontier = _iter_frontier(cursor)
    if not frontier:
        frontier = [cursor]  # Fallback for terminal nodes
    
    # 2. Get provisioners
    provisioners = do_get_provisioners(cursor, ctx=ctx)
    
    # 3. Provision each frontier node
    frontier_results: dict[UUID, ProvisioningResult] = {}
    for node in frontier:
        result = provision_node(node, provisioners, ctx=prov_ctx)
        frontier_results[node.uid] = result
    
    # 4. Cache results
    ctx.frontier_provision_results.update(frontier_results)
    
    return frontier_results
```

**What `provision_node` does:**
```python
def provision_node(node, provisioners, *, ctx):
    """Pure provisioning logic for a single node."""
    
    result = ProvisioningResult(node=node)
    
    # 1. Find all dependencies and affordances on this node
    dependencies = list(Dependency.get_dependencies(node))
    affordances = list(node.edges_in(is_instance=Affordance))
    
    # 2. Collect offers from all provisioners
    offer_map: dict[UUID, list[DependencyOffer]] = {}
    for dep in dependencies:
        for provisioner in provisioners:
            offers = provisioner.get_dependency_offers(dep.requirement, ctx=ctx)
            offer_map[dep.requirement.uid].extend(offers)
    
    for aff in affordances:
        for provisioner in provisioners:
            offers = provisioner.get_affordance_offers(node, ctx=ctx)
            result.affordance_offers.extend(offers)
    
    # 3. Deduplicate EXISTING offers (same provider)
    for req_id, offers in offer_map.items():
        offer_map[req_id] = _deduplicate_offers(offers)
    
    # 4. Select best offer per requirement
    plan = ProvisioningPlan(node=node)
    for req_id, offers in offer_map.items():
        best = _select_best_offer(offers)  # By (cost, proximity, index)
        if best:
            plan.steps.append(PlannedOffer(offer=best, requirement=...))
        else:
            # No offer available
            if requirement.hard_requirement:
                result.unresolved_hard_requirements.append(req_id)
            else:
                result.waived_soft_requirements.append(req_id)
    
    result.plans.append(plan)
    result.dependency_offers = offer_map
    
    return result
```

**Handler 2: `_planning_index_frontier_plans` (Priority: LATE)**

Caches the primary plan for each frontier node:
```python
def _planning_index_frontier_plans(cursor: Node, *, ctx: Context):
    """Cache primary provisioning plans for finalize phase."""
    for node_uid, result in ctx.frontier_provision_results.items():
        plan = result.primary_plan
        if plan:
            ctx.frontier_provision_plans[node_uid] = plan
```

### Phase 2: FINALIZE (Execute and Record)

**Handler 1: `_finalize_apply_frontier_provisions` (Priority: FIRST)**

```python
def _finalize_apply_frontier_provisions(cursor: Node, *, ctx: Context):
    """Execute cached provisioning plans and record receipts."""
    
    all_builds: list[BuildReceipt] = []
    
    for node_uid, result in ctx.frontier_provision_results.items():
        plan = ctx.frontier_provision_plans.get(node_uid)
        if not plan:
            continue
        
        # Execute all planned offers
        receipts = plan.execute(ctx=ctx)
        all_builds.extend(receipts)
    
    ctx.provision_builds.extend(all_builds)
    return all_builds
```

**Handler 2: `_planning_job_receipt` (Priority: LAST)**

```python
def _planning_job_receipt(cursor: Node, *, ctx: Context):
    """Summarize planning results into a PlanningReceipt."""
    
    frontier_results = ctx.frontier_provision_results
    builds = ctx.provision_builds
    
    # Aggregate statistics
    viable_count = sum(1 for r in frontier_results.values() if r.is_viable)
    softlock_detected = bool(frontier_results) and viable_count == 0
    
    receipt = PlanningReceipt(
        cursor_id=cursor.uid,
        frontier_node_ids=list(frontier_results.keys()),
        builds=builds,
        unresolved_hard_requirements=[...],
        waived_soft_requirements=[...],
        softlock_detected=softlock_detected,
    )
    
    # Cleanup context
    ctx.provision_offers.clear()
    ctx.provision_builds.clear()
    ctx.frontier_provision_results.clear()
    
    return receipt
```

---

## Provisioning Mechanics

### Cost-Based Selection

Offers are selected by `(cost, proximity, registration_order)`:

**Cost Hierarchy:**
1. `DIRECT` (10) - Already exists
2. `LIGHT_INDIRECT` (50) - Modify existing
3. `HEAVY_INDIRECT` (100) - Clone and modify
4. `CREATE` (200) - Build from scratch

**Proximity:** Distance from cursor (0 = immediate neighbor)

**Example:**
```python
# Given two offers:
offer1 = DependencyOffer(cost=DIRECT, proximity=2)      # Existing, far away
offer2 = DependencyOffer(cost=CREATE, proximity=0)      # New, right here

# Selection: offer1 wins (cost trumps proximity)
```

### Deduplication

Multiple provisioners may offer the same existing node:

```python
# GraphProvisioner finds "rusty_key"
offer1 = DependencyOffer(provider_id=rusty_key.uid, cost=DIRECT, proximity=0)

# Another GraphProvisioner finds same key
offer2 = DependencyOffer(provider_id=rusty_key.uid, cost=DIRECT, proximity=1)

# Deduplication: Keep offer1 (better proximity)
```

### Hard vs Soft Requirements

**Hard Requirement (blocks choice):**
```python
Requirement(..., hard_requirement=True)

# If unsatisfied:
# - Added to result.unresolved_hard_requirements
# - result.is_viable = False
# - Softlock detected if ALL frontier nodes non-viable
# - Choice should be unavailable (TODO: mark instead of filter)
```

**Soft Requirement (best effort):**
```python
Requirement(..., hard_requirement=False)

# If unsatisfied:
# - Added to result.waived_soft_requirements
# - result.is_viable still True
# - Choice remains available
# - No warning/error
```

---

## What's Implemented ✅

### Core Infrastructure

- ✅ **Frontier identification** - `_iter_frontier` correctly returns choice destinations
- ✅ **Pure provisioning** - `provision_node` function with full logic
- ✅ **All provisioner types** - Graph, Template, Updating, Cloning, Companion
- ✅ **Offer system** - DependencyOffer, AffordanceOffer with metadata
- ✅ **Cost-based selection** - `_select_best_offer` by (cost, proximity, index)
- ✅ **Deduplication** - `_deduplicate_offers` for EXISTING offers
- ✅ **Open edges** - Dependency and Affordance classes
- ✅ **Requirements** - Full Requirement model with policy validation

### Planning Pipeline

- ✅ **Phase integration** - PLANNING (30) and FINALIZE (50) handlers
- ✅ **Frontier provisioning** - `_planning_orchestrate_frontier` processes all frontier nodes
- ✅ **Plan caching** - `_planning_index_frontier_plans` stores plans
- ✅ **Plan execution** - `_finalize_apply_frontier_provisions` applies changes
- ✅ **Receipt generation** - `_planning_job_receipt` aggregates results

### Quality Features

- ✅ **Softlock detection** - Detects when no frontier node is viable
- ✅ **Hard requirement enforcement** - Tracks unresolved hard requirements
- ✅ **Soft requirement waiving** - Gracefully handles optional dependencies
- ✅ **Build receipts** - Records what happened during provisioning
- ✅ **Planning receipts** - Aggregates per-step provisioning summary
- ✅ **Deterministic RNG** - ProvisioningContext uses step-seeded random

### Related Systems

- ✅ **PREREQS/POSTREQS** - Automatic redirect edges work correctly
- ✅ **Choice availability** - Conditional edges (limited, see below)
- ✅ **Event sourcing** - Planning integrates with patch/replay system

---

## What's Missing ⚠️

### P1 - High Priority (Reduces Power)

#### 1. World Creation Doesn't Wire Requirements

**Status:** Scripts parse roles/settings but World drops them

```yaml
# In script (PARSED):
scenes:
  tavern:
    roles:
      - bartender  # This is read...
    settings:
      - interior  # ...and these are read...
    blocks:
      - start: ...

# In World.create_story (IGNORED):
# roles and settings are not turned into Dependency edges
```

**Impact:** Dynamic actor/location provisioning not possible from scripts

**Fix Location:** `engine/src/tangl/story/fabula/world.py:_compile_scenes()`

**Required Work:**
```python
# In World.create_story, after creating scene node:
for role_data in scene_data.get("roles", []):
    requirement = Requirement(
        graph=graph,
        criteria={"has_identifier": role_data["actor_ref"]},
        template=role_data.get("actor_template"),
        policy=ProvisioningPolicy.ANY,
        hard_requirement=role_data.get("hard", True)
    )
    Dependency(
        graph=graph,
        source_id=scene.uid,
        requirement=requirement,
        label=role_data.get("label", "actor")
    )
```

#### 2. TemplateProvisioner Not Connected to ScriptManager

**Status:** Works with inline templates, but not reusable templates

```python
# Current (WORKS):
Requirement(
    template={"obj_cls": "Node", "label": "key", ...}  # Inline template
)

# Not connected (DOESN'T WORK):
# In script:
templates:
  golden_key:
    obj_cls: "Item"
    label: "golden_key"
    tags: ["key", "item"]

# In Requirement:
Requirement(
    template_ref="golden_key"  # Can't resolve this
)
```

**Fix Location:** `engine/src/tangl/vm/provision/provisioner.py:TemplateProvisioner`

**Required Work:**
```python
class TemplateProvisioner(Provisioner):
    def __init__(self, *, template_registry: dict | None = None, ...):
        self.template_registry = template_registry or {}
    
    def get_dependency_offers(self, requirement, *, ctx):
        # Look up template from registry if template_ref provided
        if requirement.template_ref:
            template = self.template_registry.get(requirement.template_ref)
        else:
            template = requirement.template
        
        if not template:
            return
        
        # ... rest of logic
```

#### 3. Availability Metadata Not Implemented

**Status:** Choices filtered rather than marked

**Current Behavior:**
```python
# If hard requirement unmet:
available_choices = [
    choice for choice in all_choices
    if choice.destination in viable_frontier_nodes
]
# Non-viable choices just disappear
```

**Desired Behavior:**
```python
# Mark availability on edge itself:
choice.available = False
choice.reason_unavailable = "Missing required key"

# Renderer decides what to do:
# - Gray out
# - Show with lock icon
# - Hide completely
# - Show tooltip
```

**Fix Location:** 
- Add fields to `engine/src/tangl/vm/frame.py:ChoiceEdge`
- Update `engine/src/tangl/vm/dispatch/planning.py` to populate
- Update `Frame.get_available_choices()` to mark instead of filter

### P2 - Medium Priority (Polish)

#### 4. No Tiered Lookahead Validation

**Current:** Single-step lookahead (frontier only)

**Design Target:** Multi-tier validation
- Tier 1: Validate frontier (current)
- Tier 2: Validate frontier + 1 (next choices from frontier)
- Tier 3: Full subtree validation

**Use Case:** Prevent choices that lead to dead ends 2+ steps ahead

#### 5. Affordance Lifecycle Management

**Missing:**
- Exemplar vs duplicate distinction
- Scoping strategy (when does affordance expire?)
- Garbage collection of unused duplicates

**Current:** All affordances persist forever

### P3 - Low Priority (Future)

#### 6. Resource Garbage Collection

**Missing:** No cleanup of unused concept nodes

**Impact:** Memory leak over long sessions

#### 7. Structural Domain Abstraction

**Missing:** No concept of "episodes" as provisioning scopes

**Impact:** Can't do episode-scoped resource management

---

## Integration Points

### How to Use in Story Code

**1. Add Requirements to Nodes:**

```python
from tangl.vm.provision import Requirement, Dependency, ProvisioningPolicy

# In your story creation code:
locked_door = Block(label="locked_door", graph=graph)

key_requirement = Requirement(
    graph=graph,
    identifier="golden_key",
    criteria={"has_tags": {"key", "item"}},
    template={
        "obj_cls": "tangl.story.concepts.item.Item",
        "label": "golden_key",
        "name": "Golden Key",
        "tags": {"key", "item"}
    },
    policy=ProvisioningPolicy.ANY,
    hard_requirement=True
)

dependency = Dependency(
    graph=graph,
    source_id=locked_door.uid,
    requirement=key_requirement,
    label="needs_key"
)
```

**2. Register Custom Provisioners:**

```python
from tangl.vm.provision import Provisioner, DependencyOffer

class MyCustomProvisioner(Provisioner):
    def get_dependency_offers(self, requirement, *, ctx):
        # Custom logic to create offers
        if requirement.identifier == "magic_item":
            yield DependencyOffer(
                requirement_id=requirement.uid,
                operation=ProvisioningPolicy.CREATE,
                cost=ProvisionCost.CREATE,
                accept_func=lambda ctx: self._create_magic_item(ctx),
            )

# Register via dispatch:
@frame.local_behaviors.register(task="get_provisioners", priority=50)
def _my_provisioners(*_, **__):
    return [MyCustomProvisioner(layer="story")]
```

**3. Check Planning Receipts:**

```python
frame = ledger.get_frame()
receipt = frame.run_phase(ResolutionPhase.FINALIZE)

if receipt.softlock_detected:
    print("WARNING: No viable path forward!")
    print(f"Unresolved requirements: {receipt.unresolved_hard_requirements}")

print(f"Resources created: {receipt.created}")
print(f"Resources attached: {receipt.attached}")
```

---

## Usage Examples

### Example 1: Simple Key-Door Scenario

```python
# Setup
graph = StoryGraph()
hallway = Block(label="hallway", graph=graph)
locked_room = Block(label="locked_room", graph=graph)

# Room needs key
key_req = Requirement(
    graph=graph,
    identifier="key",
    criteria={"has_tags": {"key"}},
    template={"label": "rusty_key", "tags": {"key"}},
    policy=ProvisioningPolicy.ANY,
    hard_requirement=True
)
Dependency(graph=graph, source_id=locked_room.uid, requirement=key_req)

# Create choice
ChoiceEdge(
    graph=graph,
    source_id=hallway.uid,
    destination_id=locked_room.uid,
    label="Enter locked room"
)

# Provision
frame = Frame(graph=graph, cursor_id=hallway.uid)
frame.run_phase(P.PLANNING)
receipt = frame.run_phase(P.FINALIZE)

# Results:
# - Key created (if didn't exist)
# - key_req.provider set to key node
# - receipt.created == 1
# - Choice is available
```

### Example 2: Soft vs Hard Requirements

```python
# Hard requirement (blocks choice)
hard_req = Requirement(
    identifier="sword",
    policy=ProvisioningPolicy.EXISTING,  # Must already exist
    hard_requirement=True
)

# Soft requirement (nice to have)
soft_req = Requirement(
    identifier="shield",
    policy=ProvisioningPolicy.EXISTING,
    hard_requirement=False
)

# If neither exists:
# - Battle scene NOT viable (sword missing)
# - Choice to enter battle unavailable
# - Shield requirement waived silently
```

### Example 3: Prefer Existing Over Create

```python
# Existing key in graph
existing_key = Node(label="old_key", graph=graph, tags={"key"})

# Requirement with CREATE fallback
req = Requirement(
    criteria={"has_tags": {"key"}},
    template={"label": "new_key", "tags": {"key"}},
    policy=ProvisioningPolicy.ANY
)

# Planning:
# - GraphProvisioner offers existing_key (cost=10)
# - TemplateProvisioner offers new_key (cost=200)
# - Selection picks existing_key (lower cost)
# - No new key created
```

---

## Testing Strategy

### Unit Tests

**Location:** `engine/tests/vm/provision/`

- ✅ `test_provisioner2.py` - Provisioner behavior in isolation
- ✅ `test_provision_pure.py` - Pure `provision_node` logic
- ✅ `test_provision_int1.py` - Integration with Frame

### Integration Tests

**Location:** `engine/tests/vm/planning/`

- ✅ `test_planning_refactored.py` - Full planning pipeline
- ⚠️ **MISSING:** Test with dynamic requirements from World
- ⚠️ **MISSING:** Test with roles/settings from scripts

### Recommended New Tests

**Test 1: Locked Door Story**
```python
def test_locked_door_dynamic_provisioning():
    """End-to-end test of hard requirement gating."""
    # Create story with locked room requiring key
    # Key doesn't exist initially
    # Planning should create it
    # Choice should become available
```

**Test 2: Role Provisioning from Script**
```python
def test_scene_role_creates_dependency():
    """Test that script roles wire to Dependency edges."""
    # Load script with scene.roles
    # Verify Dependency edges created
    # Verify actor provisioned
```

**Test 3: Softlock Detection**
```python
def test_softlock_with_impossible_requirement():
    """Test softlock detection with EXISTING-only policy."""
    # Requirement needs existing key
    # No key in graph
    # Can't create (policy=EXISTING)
    # Should detect softlock
```

---

## References

### Implementation Files

- **Core:** `engine/src/tangl/vm/provision/`
  - `requirement.py` - Requirement model
  - `open_edge.py` - Dependency, Affordance
  - `provisioner.py` - All provisioner classes
  - `offer.py` - Offer types and receipts
  - `resolver.py` - Pure provisioning logic

- **Planning:** `engine/src/tangl/vm/dispatch/planning.py`
  - Phase handlers (orchestrate, index, apply, summarize)
  - Helper functions (_iter_frontier, do_get_provisioners)

- **VM:** `engine/src/tangl/vm/frame.py`
  - Frame class with phase execution
  - ChoiceEdge with trigger_phase

### Test Files

- `engine/tests/vm/provision/test_*.py`
- `engine/tests/vm/planning/test_*.py`
- `engine/tests/story/concepts/test_actor.py` (Role provisioning)

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 3.7.0 | Nov 2025 | Consolidated from outdated notes. Reflects actual implementation. |

---

**Document Status:** ✅ **CURRENT AND ACCURATE**

This document reflects the actual state of the codebase as of November 2025. All claims about implementation status have been verified against source code.
