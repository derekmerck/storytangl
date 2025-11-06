# Planning & Provisioning System Design (v3.7)

## Document Purpose

This document describes the **intended architecture** of StoryTangl's planning and provisioning system. It captures the sophisticated narrative resolution strategy that enables:
- Dynamic graph construction
- Frontier-based dependency resolution  
- Proactive resource management
- Softlock prevention
- Flexible narrative complexity scaling

**Status:** This represents the design target. Current implementation (v372) has core mechanics working but lacks some of the power and subtlety described here. Use this document to identify gaps and guide refactoring.

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Architectural Principles](#architectural-principles)
3. [The Planning Cycle](#the-planning-cycle)
4. [Dependencies vs Affordances](#dependencies-vs-affordances)
5. [Lookahead Strategies](#lookahead-strategies)
6. [Resource Lifecycle](#resource-lifecycle)
7. [Implementation Strategy](#implementation-strategy)
8. [Current Status & Gaps](#current-status--gaps)

---

## Core Concepts

### The Frontier

**The frontier is the set of NEXT structural nodes reachable from the current cursor.**

```python
# Current state
cursor = scene_A  # Where we are NOW (already resolved)

# Frontier  
frontier = [scene_B, scene_C, scene_D]  # Where we MIGHT go next
# Each reached via ChoiceEdge from cursor

# Planning resolves frontier nodes BEFORE user chooses
```

**Key insight:** Planning happens in anticipation of movement, not in response to it. By the time the user sees choices, all reachable nodes are already resolved (or marked unavailable).

### Structural vs Concept Nodes

StoryTangl maintains two logical layers:

**Structural Layer (Episodes/Scenes/Blocks):**
- Forms a tree/DAG representing narrative flow
- Nodes are locations in the story graph
- Traversed during play

**Concept Layer (Characters/Items/Resources):**
- Shared resources referenced by structure
- Nodes are "things" in the world
- Populated by planning

**Directionality Rule:** All edges connecting layers flow **structural → concept**. This preserves DAG properties and makes reasoning tractable.

```
[Scene A] ──needs_key──> [Golden Key]
[Scene B] ──dragon────> [Smaug]
[Scene C] ──companion──> [Gandalf]

(structural)            (concept)
```

Never: `[Key] ──used_in──> [Scene]` (no back-pointers)

### Requirements

A **Requirement** expresses what a structural node needs or permits, along with how to obtain it.

```python
Requirement(
    identifier="key",           # What we're looking for
    criteria={"has_tags": {...}},  # Selection criteria
    template={"label": "key", ...},  # How to create if needed
    policy=ProvisioningPolicy.ANY,   # EXISTING | CREATE | UPDATE | CLONE
    hard_requirement=True        # Gates choice availability?
)
```

**Hard vs Soft:**
- **Hard requirement:** Must be satisfied for choice to be AVAILABLE
- **Soft requirement:** Nice to have, satisfied opportunistically

**Policy determines provisioning strategy:**
- `EXISTING`: Find it
- `CREATE`: Make it from template
- `UPDATE`: Find it and modify it
- `CLONE`: Copy an existing one and evolve it
- `ANY`: Try EXISTING first, fall back to CREATE

### Open Edges

**Open edges** are graph edges with one endpoint unbound, representing relationships to be resolved during planning.

#### Dependency (Pull Pattern)

**Known source, open destination:**

```python
Dependency(
    source=door_scene,      # Known: this structural node
    destination=None,       # Open: to be resolved
    requirement=Requirement(identifier="key"),
    label="needs_key"
)
# "Door scene needs a key (any key that matches)"
```

Direction: `[Door Scene] ──needs_key──> [Key?]`

#### Affordance (Push Pattern)

**Open source, known destination:**

```python
Affordance(
    source=None,           # Open: to be resolved
    destination=dragon,    # Known: this concept exists
    requirement=Requirement(criteria={"has_tags": {"wants_dragon"}}),
    label="dragon"
)
# "Dragon can appear in scenes tagged 'wants_dragon'"
```

Direction: `[Scene?] ──dragon──> [Smaug]`

### Provisioners

**Provisioners** are entities that generate **offers** - proposals for how to satisfy requirements.

```python
class Provisioner:
    def get_dependency_offers(requirement, *, ctx) -> Iterator[DependencyOffer]:
        """Respond to a specific need (pull)."""
        
    def get_affordance_offers(node, *, ctx) -> Iterator[AffordanceOffer]:
        """Proactively offer resources (push)."""
```

**Standard types:**
- `GraphProvisioner`: Search existing nodes (cheapest)
- `TemplateProvisioner`: Create from templates
- `UpdatingProvisioner`: Find and modify existing
- `CloningProvisioner`: Copy and evolve existing

### Offers

**Offers** are lazy proposals with callbacks:

```python
DependencyOffer(
    requirement_id=UUID,
    operation=ProvisioningPolicy.EXISTING,
    cost=ProvisionCost.DIRECT,  # 10
    proximity=2,  # Distance from cursor
    accept_func=lambda ctx: existing_key,  # Lazy execution
)
```

**Cost hierarchy:**
1. `DIRECT` (10): Already exists
2. `LIGHT_INDIRECT` (50): Modify existing  
3. `HEAVY_INDIRECT` (100): Clone and modify
4. `CREATE` (200): Build from scratch

**Selection criteria:** `(cost, proximity, registration_order)`

Nothing happens until `offer.accept(ctx=ctx)` is called.

---

## Architectural Principles

### Principle 1: Three-Layer Separation

**Layer 1: Structure (Graph)**
- Nodes and edges exist
- Represents possibility space
- Independent of state

**Layer 2: State (Planning)**  
- Requirements satisfied or not
- Availability calculated
- Resources provisioned

**Layer 3: Presentation (Rendering)**
- Show/hide/gray-out choices
- Explain why things are locked
- Client-side policy

**Planning sits at Layer 2.** It populates state but doesn't filter structure or dictate presentation.

### Principle 2: Existence ≠ Availability

Planning creates ALL choices in the graph, then marks their availability.

```python
# All choices exist structurally
choices = [
    ChoiceEdge(source=cursor, destination=scene_B, label="Take the key"),
    ChoiceEdge(source=cursor, destination=scene_C, label="Force the door"),
]

# Planning marks availability
choices[0].available = has_key  # True/False
choices[0].reason_unavailable = "You don't have the key" if not has_key else None

# Renderer decides what to show
# - Gray out unavailable choices
# - Hide them completely  
# - Show with 🔒 icon
# - etc.
```

**Why this matters:**
- Players can see locked content (motivation)
- Reduces confusion ("why isn't this an option?")
- Supports progressive disclosure
- Matches game UX patterns (skill trees, etc.)

### Principle 3: Lookahead Planning

**Planning resolves frontier nodes BEFORE user chooses.**

```
Step 1: User at A
    ↓
Step 2: Planning resolves [B, C, D]
    - Collect offers
    - Select and accept best offers  
    - Mark availability
    - Validate at least one path forward
    ↓
Step 3: Present choices to user
    - "Go to B" (available)
    - "Go to C" (locked: missing key)
    - "Go to D" (available)
    ↓
Step 4: User chooses B
    ↓
Step 5: Move cursor to B (already resolved!)
    ↓
Repeat with B as new cursor
```

**Benefits:**
- No loading/blocking when user makes choice
- All visible choices are "ready"
- Can detect softlocks proactively
- Enables cost-based resource sharing

### Principle 4: Persistent Speculation

Resources created during planning persist even if that path isn't taken.

```python
# Planning resolves frontier [B, C]
# Creates dragon to satisfy B's dependency
dragon = create_from_template({"label": "Smaug"})

# User chooses C instead
# Dragon still exists!

# Later, D also needs a dragon
# Planning reuses existing dragon (cheaper than creating new one)
```

**Why this matters:**
- Consistent world state
- Resource sharing across paths
- Cheaper provisioning
- Richer world (more things exist)

**With eventual GC:**
```python
# After retention window, if dragon never referenced again:
if dragon.last_seen < current_step - RETENTION_WINDOW:
    if not any(node.might_use(dragon) for node in reachable_nodes):
        gc_collect(dragon)
```

---

## The Planning Cycle

### Overview

Planning happens during the `PLANNING` phase of frame resolution:

```
Frame.follow_edge(edge_to_B):
    1. Move cursor to B
    2. Set step marker
    3. Invalidate context (new scope)
    
    4. VALIDATE phase
       - Check if cursor is allowed
    
    5. PLANNING phase ← WE ARE HERE
       a. Discover provisioners
       b. Identify frontier nodes
       c. Collect offers (dependencies + affordances)
       d. Deduplicate EXISTING offers
       e. Select best offer per requirement
       f. Accept offers (lazy execution)
       g. Mark choice availability
       h. Validate path forward
       i. Return PlanningReceipt
    
    6. UPDATE phase
       - Execute effects
    
    7. JOURNAL phase  
       - Generate content fragments
       - Include available choices
    
    8. FINALIZE phase
       - Create patch if event_sourced
```

### Step-by-Step Breakdown

#### 5a. Discover Provisioners

```python
def do_get_provisioners(anchor: Node, *, ctx: Context) -> list[Provisioner]:
    """Walk scope hierarchy to gather provisioners."""
    
    # Via scoped_dispatch with task="get_provisioners"
    # Discovery order:
    # 1. LOCAL: anchor.provisioners (if hasattr)
    # 2. AUTHOR: graph.provisioners  
    # 3. APPLICATION: app-level provisioners
    # 4. GLOBAL: vm_dispatch registered defaults
    
    receipts = scoped_dispatch(
        caller=anchor,
        ctx=ctx,
        task="get_provisioners",
    )
    return CallReceipt.merge_results(*receipts)
```

Default provisioners injected by `vm_dispatch`:
- `GraphProvisioner` (search existing)
- `TemplateProvisioner` (create new)
- `UpdatingProvisioner` (modify existing)
- `CloningProvisioner` (copy and evolve)

#### 5b. Identify Frontier Nodes

```python
def _iter_frontier(cursor: Node) -> list[Node]:
    """Return reachable next-nodes that need provisioning."""
    
    frontier = [
        edge.destination 
        for edge in cursor.edges_out(is_instance=ChoiceEdge)
        if edge.destination is not None
    ]
    
    # If no explicit choices, cursor is terminal
    return frontier if frontier else []
```

**Current implementation:** Returns `[cursor]` - this is WRONG. Needs to return frontier.

#### 5c. Collect Offers

For each frontier node, collect both dependency and affordance offers:

```python
def _planning_collect_offers(cursor: Node, *, ctx: Context):
    provisioners = do_get_provisioners(cursor, ctx=ctx)
    offers = defaultdict(list)  # keyed by requirement_id or "*"
    
    frontier = _iter_frontier(cursor)
    
    # Collect affordance offers (push pattern)
    # "What resources can proactively attach to these nodes?"
    for proximity, provisioner in enumerate(provisioners):
        for frontier_node in frontier:
            for offer in provisioner.get_affordance_offers(frontier_node, ctx=ctx):
                # Affordance exemplar has open source
                # Check if it can attach to this frontier_node
                if offer.requirement.satisfied_by(frontier_node):
                    offer.proximity = proximity
                    offers["*"].append(offer)
    
    # Collect dependency offers (pull pattern)  
    # "How can we satisfy the needs of these nodes?"
    for frontier_node in frontier:
        for dep in get_dependencies(frontier_node, satisfied=False):
            req = dep.requirement
            
            for proximity, provisioner in enumerate(provisioners):
                for offer in provisioner.get_dependency_offers(req, ctx=ctx):
                    offer.proximity = proximity
                    offers[dep.uid].append(offer)
    
    ctx.provision_offers = offers
    return offers
```

#### 5d. Deduplicate EXISTING Offers

Multiple provisioners might offer the same existing node:

```python
def _deduplicate_offers(offers: list[ProvisionOffer]) -> list[ProvisionOffer]:
    """Keep only best EXISTING offer per provider."""
    
    existing_by_provider = defaultdict(list)
    non_existing = []
    
    for idx, offer in enumerate(offers):
        if (offer.operation == EXISTING and offer.provider_id):
            existing_by_provider[offer.provider_id].append((idx, offer))
        else:
            non_existing.append((idx, offer))
    
    # For each provider, keep cheapest/closest offer
    deduplicated = []
    for provider_offers in existing_by_provider.values():
        best = min(provider_offers, key=lambda x: (x[1].cost, x[1].proximity, x[0]))
        deduplicated.append(best)
    
    deduplicated.extend(non_existing)
    deduplicated.sort(key=lambda x: (x[1].cost, x[1].proximity, x[0]))
    
    return [offer for _, offer in deduplicated]
```

#### 5e. Select Best Offer

For each requirement, pick the best offer:

```python
def _select_best_offer(offers: list[ProvisionOffer]) -> ProvisionOffer | None:
    """Select by (cost, proximity, registration_order)."""
    
    if not offers:
        return None
    
    return min(
        enumerate(offers),
        key=lambda x: (x[1].cost, x[1].proximity, x[0])
    )[1]
```

#### 5f. Accept Offers

Execute the lazy callbacks:

```python
def _planning_link_dependencies(cursor: Node, *, ctx: Context):
    builds = []
    
    for frontier_node in _iter_frontier(cursor):
        for dep in get_dependencies(frontier_node, satisfied=False):
            req = dep.requirement
            offers = ctx.provision_offers.get(dep.uid, [])
            
            best_offer = _select_best_offer(offers)
            
            if best_offer:
                # Execute lazy callback
                provider = best_offer.accept(ctx=ctx)
                
                # Bind to requirement
                req.provider = provider
                dep.destination = provider  # Close the open edge
                
                # Record success
                build = BuildReceipt(
                    provisioner_id=best_offer.source_provisioner_id,
                    requirement_id=req.uid,
                    provider_id=provider.uid,
                    operation=best_offer.operation,
                    accepted=True,
                    hard_req=req.hard_requirement,
                )
            else:
                # Record failure
                build = BuildReceipt(
                    provisioner_id=None,
                    requirement_id=req.uid,
                    provider_id=None,
                    operation=req.policy,
                    accepted=False,
                    hard_req=req.hard_requirement,
                    reason="no_viable_offers",
                )
            
            builds.append(build)
    
    return builds
```

#### 5g. Mark Choice Availability

Based on requirement satisfaction:

```python
def _mark_choice_availability(cursor: Node):
    """Update metadata on ChoiceEdges."""
    
    for edge in cursor.edges_out(is_instance=ChoiceEdge):
        dest = edge.destination
        
        # Check hard requirements
        hard_deps = get_dependencies(dest, hard_only=True)
        unsatisfied = [dep for dep in hard_deps if not dep.satisfied]
        
        if unsatisfied:
            edge.available = False
            edge.reason_unavailable = (
                f"Missing: {', '.join(dep.label for dep in unsatisfied)}"
            )
        else:
            edge.available = True
            edge.reason_unavailable = None
```

#### 5h. Validate Path Forward

**Softlock prevention:**

```python
def _validate_path_forward(cursor: Node) -> bool:
    """Ensure at least one frontier node is reachable."""
    
    frontier = _iter_frontier(cursor)
    
    valid_nodes = [
        node for node in frontier
        if all(dep.satisfied for dep in get_dependencies(node, hard_only=True))
    ]
    
    if len(valid_nodes) == 0:
        # SOFTLOCK DETECTED
        # Could try emergency measures here:
        # - Force-create soft requirements
        # - Relax constraints
        
        raise SoftlockError(
            f"No valid paths from {cursor.label}. "
            f"All choices have unsatisfied hard requirements."
        )
    
    return True
```

#### 5i. Return PlanningReceipt

Summarize the planning outcome:

```python
@on_planning(priority=Prio.LAST)
def _planning_job_receipt(cursor: Node, *, ctx: Context):
    builds = ctx.provision_builds
    
    receipt = PlanningReceipt(
        created=sum(1 for b in builds if b.operation == CREATE and b.accepted),
        attached=sum(1 for b in builds if b.operation == EXISTING and b.accepted),
        updated=sum(1 for b in builds if b.operation == UPDATE and b.accepted),
        cloned=sum(1 for b in builds if b.operation == CLONE and b.accepted),
        unresolved_hard_requirements=[
            b.requirement_id for b in builds
            if not b.accepted and b.hard_req
        ],
        waived_soft_requirements=[
            b.requirement_id for b in builds  
            if not b.accepted and not b.hard_req
        ],
    )
    
    return receipt
```

---

## Dependencies vs Affordances

### Symmetric but Opposite

| Aspect | Dependency | Affordance |
|--------|-----------|-----------|
| **Pattern** | Pull | Push |
| **Known endpoint** | Source (structural) | Destination (concept) |
| **Open endpoint** | Destination (concept) | Source (structural) |
| **Semantics** | "I need X" | "X is available" |
| **Initiator** | Destination pulls | Source offers |
| **Planning** | Find/create resource | Attach to compatible nodes |

### Dependency Example

```python
# Door scene needs a key
door_scene = Node(label="Locked Door")

requirement = Requirement(
    identifier="key",
    criteria={"has_tags": {"key", "golden"}},
    template={"label": "Golden Key", "tags": {"key", "golden"}},
    policy=ProvisioningPolicy.ANY,  # Try EXISTING, fall back to CREATE
    hard_requirement=True,  # Must have key to open door
)

dependency = Dependency(
    source=door_scene,  # Known
    destination=None,   # Open - to be resolved
    requirement=requirement,
    label="needs_key"
)

# During planning:
# 1. GraphProvisioner searches for existing keys
#    - Offers: [existing_key_1, existing_key_2]
# 2. TemplateProvisioner offers to create new key
#    - Offers: [create_new_key]
# 3. Select best (EXISTING is cheapest)
# 4. Accept: dependency.destination = existing_key_1
# 5. Result: ns['needs_key'] = existing_key_1
```

Direction: `[Locked Door] ──needs_key──> [Golden Key]`

### Affordance Example

```python
# Dragon can appear in dragon-wanting scenes
dragon = Node(label="Smaug", tags={"dragon", "villain"})

requirement = Requirement(
    criteria={"has_tags": {"wants_dragon"}},
    policy=ProvisioningPolicy.EXISTING,
)

# Affordance exemplar (template)
dragon_affordance = Affordance(
    source=None,        # Open - to be filled during planning
    destination=dragon, # Known
    requirement=requirement,
    label="dragon"
)

# During planning for frontier:
mountain_scene = Node(label="Mountain Path", tags={"wants_dragon"})
village_scene = Node(label="Village", tags={"peaceful"})

# Check each frontier node
if requirement.satisfied_by(mountain_scene):
    # Duplicate affordance with concrete source
    duplicate = Affordance(
        source=mountain_scene,
        destination=dragon,
        requirement=requirement,
        label="dragon"
    )
    graph.add(duplicate)
    # Result: ns['dragon'] = Smaug (at mountain)

if requirement.satisfied_by(village_scene):
    # Doesn't match - no dragon in village
    pass
```

Direction: `[Mountain Path] ──dragon──> [Smaug]`

### Namespace Population

Both populate the rendering namespace:

```jinja2
{# At Mountain Path #}
You climb the treacherous path.
{% if dragon %}
    Smoke rises ahead - {{ dragon.name }} awaits.
{% endif %}

{# At Village #}  
You enter the peaceful village.
{% if dragon %}
    {# This won't render - no dragon affordance here #}
{% endif %}
```

### Key Difference: Reference vs Presence

**Affordances enable reference without physical presence:**

```python
# Dragon exists globally
dragon = Node(label="Smaug", hit_points=100)

# Referenced in many scenes via affordances
scene_1.add_affordance(dragon, label="dragon")  
scene_2.add_affordance(dragon, label="dragon")
scene_3.add_affordance(dragon, label="dragon")

# But only physically present in one
encounter_scene.add_dependency(dragon, label="boss")

# Narrator can reference dragon anywhere it's afforded:
# "You must defeat {{ dragon.name }} eventually..."
# Even though you haven't encountered it yet
```

**Dependencies create existential constraints:**

```python
# For this choice to EXIST, door must exist
locked_door_scene.add_dependency(door, hard_requirement=True)

# If door can't be provisioned:
# - Choice doesn't appear, OR  
# - Choice appears but marked unavailable
```

---

## Lookahead Strategies

Planning complexity scales with narrative type.

### Tier 1: Linear/Deterministic (No Lookahead)

**Use case:** Novels, kinetic visual novels, single-path stories

**Strategy:** Single frontier node, no branching

```python
if len(frontier) == 1 and frontier[0].is_deterministic:
    # Just resolve dependencies for the single next node
    # By induction, will reach end if end exists
    return ALWAYS_VALID
```

**Example:**
```
A → B → C → D → END
```

No choices to validate, just ensure each node's dependencies are satisfiable.

### Tier 2: Static Graph (Exhaustive Analysis)

**Use case:** Classic CYOA, branching narratives with fixed structure

**Strategy:** Enumerate all paths, prove all lead to sink

```python
def validate_static_graph(root: Node, sinks: list[Node]) -> bool:
    """Prove every path from root reaches a sink."""
    
    # Build reachability matrix
    all_nodes = enumerate_all_nodes(root)
    
    for node in all_nodes:
        paths = find_paths(node, sinks)
        if len(paths) == 0:
            raise SoftlockError(f"Dead end at {node.label}")
    
    return True
```

**Example:**
```
      ┌─→ B ─→ D ─┐
A ────┤           ├─→ END
      └─→ C ─→ E ─┘
```

Validate that from any node, there exists at least one path to END.

### Tier 3: Dynamic Graph (EM-Style Probabilistic)

**Use case:** Procedural narratives, emergent stories, dynamic content

**Strategy:** Lookahead N steps, check reverse reachability from sinks

```python
def validate_dynamic_frontier(
    cursor: Node,
    frontier: list[Node],
    depth: int = 2
) -> bool:
    """
    Check if frontier nodes are reachable from nearest sinks.
    
    Uses EM-like algorithm:
    1. Look ahead N steps (Expectation)
    2. Check reverse reachability from sinks (Maximization)
    3. Repeat until convergence or failure
    """
    
    # Find nearest structural sinks
    sinks = find_nearest_sinks(cursor, max_distance=10)
    
    for frontier_node in frontier:
        # Use dominating source/sink abstraction
        episode = frontier_node.get_containing_episode()
        episode_source = episode.get_dominating_source()
        episode_sink = episode.get_dominating_sink()
        
        # Can we reach episode_sink from episode_source?
        reachable = check_reachability(
            episode_source,
            episode_sink,
            under_any_condition=True
        )
        
        if not reachable:
            # This frontier node leads nowhere
            frontier_node.available = False
            frontier_node.reason_unavailable = "Path leads to dead end"
    
    # Ensure at least one path forward
    valid_nodes = [n for n in frontier if n.available]
    if len(valid_nodes) == 0:
        raise SoftlockError("No viable paths forward")
    
    return True
```

**Example:**
```
A → [B₁, B₂, B₃] (dynamically generated)
     ↓    ↓    ↓
    ???  ???  ???
     ↓    ↓    ↓
    END  END  END
```

For each frontier node, prove there exists SOME path to a sink, even if internal structure is partially materialized.

### Cardinal Form Abstraction

For dynamic graphs, episodes use **dominating source/sink** nodes:

```python
class Episode(Subgraph):
    """
    Episode with abstract entry/exit points.
    
    Internal structure may be partially materialized,
    but we can reason about reachability abstractly.
    """
    
    @property
    def dominating_source(self) -> Node:
        """Abstract entry point. All entry events connect here."""
        if not self._source:
            self._source = Node(label=f"{self.label}:source", 
                              tags={"abstract", "source"})
            self.add(self._source)
        return self._source
    
    @property
    def dominating_sink(self) -> Node:
        """Abstract exit point. All exit events connect here."""
        if not self._sink:
            self._sink = Node(label=f"{self.label}:sink",
                            tags={"abstract", "sink"})
            self.add(self._sink)
        return self._sink
    
    def prove_reachability(self) -> bool:
        """Can we get from source to sink under SOME condition?"""
        # Use graph traversal on abstract structure
        # Don't need every internal node to exist
        return has_path(self.dominating_source, self.dominating_sink)
```

**Benefits:**
- Reason about episodes as black boxes
- Prove soundness without full materialization
- Support incremental graph construction
- Enable compositional reasoning

---

## Resource Lifecycle

### Creation

Resources are created speculatively during planning:

```python
# Planning resolves frontier [B, C, D]
# B needs a dragon
dragon = create_from_template({"label": "Smaug", "tags": {"dragon"}})

# Dragon exists now, even though user hasn't chosen B yet
```

### Persistence

Created resources persist across planning cycles:

```python
# Step 1: User chooses C (not B)
# Dragon still exists

# Step 5: User encounters node E that also wants dragon  
# Planning finds existing dragon (cheaper than creating new)
dragon_offers = graph_provisioner.get_dependency_offers(req_dragon)
# Returns: [EXISTING: Smaug (cost=10)]
```

### Sharing

Same resource can satisfy multiple requirements:

```python
# Scene B: "A dragon blocks the path"
dependency_B = Dependency(source=scene_B, requirement=req_dragon)

# Scene F: "You face the dragon again"
dependency_F = Dependency(source=scene_F, requirement=req_dragon)

# Both resolve to same dragon instance
dependency_B.destination = dragon
dependency_F.destination = dragon

# Dragon state persists between encounters
dragon.hit_points -= 20  # Damaged in scene B
# Scene F sees injured dragon
```

### Garbage Collection

**Eventually, unused resources should be collected:**

```python
class ResourceGarbageCollector:
    RETENTION_WINDOW = 20  # steps
    
    def collect_garbage(self, graph: Graph, current_step: int):
        """Remove resources that are no longer reachable."""
        
        for concept in graph.find_nodes(is_concept=True):
            # Check if referenced
            incoming = list(concept.edges_in())
            
            if len(incoming) == 0:
                # No structural nodes reference this
                self._mark_for_collection(concept)
                continue
            
            # Check last seen
            if concept.last_referenced_step < current_step - self.RETENTION_WINDOW:
                # Old and might not be needed
                reachable_nodes = self._find_reachable_from_cursor()
                might_use = any(
                    self._might_reference(node, concept)
                    for node in reachable_nodes
                )
                
                if not might_use:
                    self._collect(concept)
```

**Special handling for "generic" extras:**

```python
# Extras can be retired aggressively
if "generic" in node.tags and node not in active_scene:
    gc_collect(node)

# But can be promoted if interacted with
if user_interacts_with(extra):
    extra.tags.remove("generic")
    extra.tags.add("named")
    # Now persists like any other concept
```

### Affordance Lifecycle

**Exemplar vs Duplicates:**

```python
# Exemplar (template, persistent)
dragon_affordance = Affordance(
    source=None,
    destination=dragon,
    requirement=req_wants_dragon,
    label="dragon"
)
# Lives in provisioner or graph root

# Duplicates (instances, collectible)
for frontier_node in planning:
    if req_wants_dragon.satisfied_by(frontier_node):
        duplicate = dragon_affordance.clone()
        duplicate.source = frontier_node
        graph.add(duplicate)
        # Lives temporarily

# Exemplar persists, duplicates can be GC'd
```

---

## Implementation Strategy

### Phase 1: Fix Frontier Resolution ✅

**Current:** Planning operates on cursor (wrong)  
**Target:** Planning operates on frontier (correct)

```python
# Fix _iter_frontier
def _iter_frontier(cursor: Node) -> list[Node]:
    return [
        edge.destination
        for edge in cursor.edges_out(is_instance=ChoiceEdge)
        if edge.destination is not None
    ] or []

# Update _planning_collect_offers
for frontier_node in _iter_frontier(cursor):
    # Collect offers for frontier_node, not cursor
    ...
```

### Phase 2: Add Availability Metadata ✅

**Target:** Choices exist but marked available/unavailable

```python
class ChoiceEdge(Edge, Conditional):
    available: bool = True
    reason_unavailable: str | None = None
```

Update planning to set these fields based on requirement satisfaction.

### Phase 3: Implement Tier 1 Lookahead ✅

**Target:** Linear narratives work without softlock checks

```python
def _validate_lookahead_tier1(cursor: Node, frontier: list[Node]) -> bool:
    """For linear/deterministic stories."""
    if len(frontier) <= 1:
        # Single path forward, always valid
        return True
    return False  # Fall through to more sophisticated validation
```

### Phase 4: Add Structural Domains 🔲

**Target:** Episode abstraction with source/sink

```python
# New module: tangl.vm.structural

class StructuralDomain:
    def get_dominating_source(self, subgraph: Subgraph) -> Node:
        ...
    
    def get_dominating_sink(self, subgraph: Subgraph) -> Node:
        ...
    
    def prove_reachability(self, source: Node, sink: Node) -> bool:
        ...
```

### Phase 5: Implement Tier 2 Lookahead 🔲

**Target:** Static graph validation

```python
def _validate_lookahead_tier2(cursor: Node, frontier: list[Node]) -> bool:
    """For static CYOA-style narratives."""
    # Find sinks
    sinks = find_terminal_nodes(cursor.get_root())
    
    # Check each frontier node
    for node in frontier:
        if not has_path_to_any(node, sinks):
            node.available = False
            node.reason_unavailable = "Dead end"
    
    return any(n.available for n in frontier)
```

### Phase 6: Implement GC Strategy 🔲

**Target:** Unused resources eventually cleaned up

```python
# Add to Frame or Ledger
gc_collector = ResourceGarbageCollector()

# After each step
if frame.step % GC_INTERVAL == 0:
    gc_collector.collect_garbage(frame.graph, frame.step)
```

### Phase 7: Polish Affordance System 🔲

**Target:** Exemplar/duplicate tracking, scoping

```python
class Affordance(Edge):
    is_exemplar: bool = False  # Template vs instance
    
    def clone(self) -> Affordance:
        duplicate = super().clone()
        duplicate.is_exemplar = False
        return duplicate
```

---

## Current Status & Gaps

### What's Working (v372) ✅

1. **Core provisioning loop:**
   - Provisioner discovery via scoped_dispatch ✅
   - Offer collection (dependencies + affordances) ✅
   - Offer deduplication (EXISTING by provider_id) ✅
   - Selection by (cost, proximity, registration) ✅
   - Lazy execution via accept() ✅
   - BuildReceipt generation ✅

2. **Standard provisioner types:**
   - GraphProvisioner ✅
   - TemplateProvisioner ✅
   - UpdatingProvisioner ✅
   - CloningProvisioner ✅

3. **Testing:**
   - Unit tests for each provisioner ✅
   - Integration tests for planning cycles ✅
   - Deduplication tests ✅
   - Requirement satisfaction tests ✅

### What's Missing/Wrong 🚧

1. **Frontier iteration:**
   - `_iter_frontier` returns `[cursor]` instead of choice destinations
   - Planning operates on current node, not next nodes
   - **Impact:** HIGH - fundamentally wrong timing

2. **Availability metadata:**
   - No `edge.available` field
   - No `edge.reason_unavailable` field  
   - Choices are filtered by planning, not marked
   - **Impact:** MEDIUM - reduces flexibility

3. **Lookahead strategy:**
   - No tier-based validation
   - No softlock detection beyond "no offers"
   - No structural domain abstraction
   - **Impact:** MEDIUM - limits narrative complexity

4. **Affordance mechanics:**
   - Works but not exemplar/duplicate separation
   - No explicit scoping strategy
   - **Impact:** LOW - functional but not elegant

5. **Resource lifecycle:**
   - No garbage collection
   - No retention strategy
   - No "generic" extra handling
   - **Impact:** LOW - memory leak over long sessions

6. **Documentation:**
   - Current design doc (`provisioner_design.md`) says "not implemented yet"
   - Code comments refer to future work
   - No usage guide
   - **Impact:** MEDIUM - maintainability

### Priority Fixes

**P0 (Critical - breaks design intent):**
1. Fix `_iter_frontier` to return frontier, not cursor
2. Update planning handlers to iterate frontier
3. Update tests to verify frontier resolution

**P1 (High - reduces power):**
4. Add availability metadata to ChoiceEdge
5. Update planning to mark instead of filter
6. Implement Tier 1 lookahead validation

**P2 (Medium - polish):**
7. Add structural domain abstraction
8. Implement Tier 2 lookahead
9. Clean up affordance exemplar/duplicate pattern

**P3 (Low - future):**
10. Add garbage collection
11. Implement Tier 3 lookahead
12. Add generic extra promotion

---

## Examples

### Example 1: Simple Dependency

```python
# Author creates a locked door scene
door_scene = graph.add_node(label="Locked Door")

# Door requires a key (hard requirement)
key_req = Requirement(
    identifier="key",
    criteria={"has_tags": {"key"}},
    template={"label": "Golden Key", "tags": {"key"}},
    policy=ProvisioningPolicy.ANY,
    hard_requirement=True,
)

dependency = Dependency(
    source=door_scene,
    destination=None,  # Open
    requirement=key_req,
    label="needs_key"
)

# During planning (user is one step away from door):
# 1. Frontier includes door_scene
# 2. GraphProvisioner searches for existing keys
#    - Found: rusty_key
# 3. TemplateProvisioner offers to create golden_key
# 4. Selection picks rusty_key (EXISTING cheaper than CREATE)
# 5. dependency.destination = rusty_key
# 6. Choice to enter door_scene marked available

# User sees: "Enter the locked door" (clickable)
```

### Example 2: Affordance Reference

```python
# Author creates dragon (concept)
dragon = graph.add_node(label="Smaug", tags={"dragon", "villain"})

# Dragon offers itself to dragon-wanting scenes
dragon_aff = Affordance(
    source=None,  # Open
    destination=dragon,
    requirement=Requirement(criteria={"has_tags": {"wants_dragon"}}),
    label="dragon"
)

# Scene 1: Mountain path (wants dragon)
mountain = graph.add_node(label="Mountain Path", tags={"wants_dragon"})

# Scene 2: Village (doesn't want dragon)
village = graph.add_node(label="Village", tags={"peaceful"})

# During planning with frontier [mountain, village]:
# 1. Check dragon_aff against mountain
#    - Requirement satisfied ✓
#    - Duplicate: mountain ──dragon──> Smaug
# 2. Check dragon_aff against village  
#    - Requirement NOT satisfied ✗
#    - No duplicate

# Rendering mountain scene:
# ns['dragon'] = Smaug
# "Smoke rises from the peak where {{ dragon.name }} awaits."

# Rendering village scene:
# 'dragon' not in ns
# No dragon reference possible
```

### Example 3: Resource Sharing

```python
# Multiple scenes need villains
scene_A = graph.add_node(label="Forest")
scene_B = graph.add_node(label="Cave")
scene_C = graph.add_node(label="Castle")

req_villain = Requirement(
    criteria={"has_tags": {"villain"}},
    template={"label": "Dark Lord", "tags": {"villain"}},
    policy=ProvisioningPolicy.ANY,
)

Dependency(source=scene_A, requirement=req_villain, label="villain")
Dependency(source=scene_B, requirement=req_villain, label="villain")
Dependency(source=scene_C, requirement=req_villain, label="villain")

# Step 1: Planning for frontier [A]
#   - No existing villain
#   - CREATE Dark Lord (cost=200)
#   - scene_A.villain = dark_lord

# Step 2: Planning for frontier [B]
#   - Existing villain: dark_lord
#   - EXISTING dark_lord (cost=10)
#   - scene_B.villain = dark_lord (same instance)

# Step 3: Planning for frontier [C]
#   - Still existing: dark_lord
#   - scene_C.villain = dark_lord (still same instance)

# All three scenes reference the same villain
# State persists: dark_lord.hit_points = 80 (damaged in A)
# Scene B sees injured villain
# Scene C sees same injured villain
```

---

## Glossary

**Affordance:** Open-source edge offering a concept to compatible structural nodes. Push pattern.

**Availability:** Whether a choice can be selected (different from existence).

**Build Receipt:** Record of one provisioning action (success or failure).

**Cardinal Form:** Episode abstraction with dominating source and sink nodes.

**Choice Edge:** Graph edge representing a navigational option for the player.

**Concept Node:** Resource/thing in the world (character, item, etc.). Referenced by structure.

**Cursor:** Current position in the story graph.

**Dependency:** Open-destination edge requesting a concept for a structural node. Pull pattern.

**Exemplar:** Template affordance with open source. Persists.

**Duplicate:** Instance affordance with bound source. Can be GC'd.

**Frontier:** Set of next structural nodes reachable from cursor.

**Hard Requirement:** Must be satisfied for choice to be available.

**Offer:** Lazy proposal for how to satisfy a requirement.

**Planning Phase:** VM phase that resolves frontier dependencies and affordances.

**Planning Receipt:** Summary of all provisioning actions in a planning cycle.

**Provisioner:** Entity that generates offers.

**Requirement:** Specification of what's needed and how to obtain it.

**Soft Requirement:** Nice to have, satisfied opportunistically.

**Softlock:** State where no valid path forward exists.

**Structural Node:** Location in the story graph (episode, scene, block).

**Template:** Blueprint for creating a new node.

---

## References

- Implementation: `engine/src/tangl/vm/provision/`
- Planning handlers: `engine/src/tangl/vm/dispatch/planning_v372.py`
- Tests: `engine/tests/vm/provision/`, `engine/tests/vm/planning/`
- Original design notes: `docs/notes/provisioner_design.md`
- Legacy inventory: `docs/notes/legacy_feature_inventory.md`

---

**Document Version:** 1.0  
**Date:** 2024-11-06  
**Status:** Design Target (implementation in progress)
