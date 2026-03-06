Concept Provisioning Design
===========================

**Document Version:** 2.1
**Last Updated:** December 2025
**Status:** ✅ IMPLEMENTATION COMPLETE

## Core Philosophy

StoryTangl distinguishes between **named individuals** (unique entities with identity) and **generic templates** (fungible role-fillers). This distinction drives the entire provisioning architecture:

- **Named individuals** → Declared as **affordances** (unique, persistent, discoverable)
- **Generic templates** → Stored as **script records in registries** (fungible, scope-filtered, created on-demand)

The system provides both convenient shortcuts for common cases and explicit long-form syntax for complex scenarios.

---

## Declaration Semantics

### Named Individuals: Affordances

**Named concepts have identity and should exist uniquely in the story world.**

```yaml
# In script YAML
actors:
  bob:
    name: "Bob Smith"
    profession: "blacksmith"
    personality: "gruff"
  
  alice:
    name: "Alice Chen"
    archetype: "scholar"
    specialty: "ancient_history"

locations:
  forge:
    name: "The Old Forge"
    atmosphere: "smoky"
```

**What gets created:**

Depending on world creation mode (see World Creation Modes below):

**Eager destination (mode="full" or mode="hybrid"):**
```python
# Concrete node created immediately
bob_actor = Actor(name="Bob Smith", profession="blacksmith", personality="gruff")

# Affordance points to existing node
bob_affordance = Affordance(
    graph=graph,
    source_id=None,  # Available globally
    destination_id=bob_actor.uid,  # Points to concrete node
    requirement=Requirement(
        identifier="bob",
        policy=ProvisioningPolicy.EXISTING
    ),
    label="bob"
)
```

**Lazy destination (mode="lazy"):**
```python
# No concrete node yet
bob_affordance = Affordance(
    graph=graph,
    source_id=None,  # Available globally
    destination_id=None,  # Will create when claimed
    requirement=Requirement(
        identifier="bob",
        template={"name": "Bob Smith", "profession": "blacksmith", ...},
        policy=ProvisioningPolicy.CREATE
    ),
    label="bob"
)

# When a scene claims Bob:
# Planner instantiates from template
# Sets affordance.destination = bob_actor
# Subsequent scenes reuse the same Bob
```

**Semantic properties:**
- Bob has persistent identity across scenes
- Creating multiple Bobs is an error
- Bob is discoverable via identifier or criteria matching
- Bob persists in graph until explicitly removed
- Scope: available to all scenes (world-scoped affordances)

**Scene-scoped affordances:**
```yaml
scenes:
  village:
    actors:
      mayor:
        name: "Mayor Johnson"
        role: "village_leader"
    
    blocks:
      town_hall:
        # Mayor available here (inherited from scene)
```

Scope determines visibility:
- World-scoped affordances → available to all scenes
- Scene-scoped affordances → available to blocks in that scene
- Block-scoped affordances → available only in that block

---

### Generic Templates: Script Records in Registry

**Generic templates are validated script objects (ActorScript, LocationScript, etc.) stored as Record entities in a Registry with scope-based selection.**

#### Template Structure

Templates are `BaseScriptItem` subclasses (which inherit from `Record`):

```python
# Templates are Record entities with UIDs, labels, tags
class ActorScript(BaseScriptItem):  # BaseScriptItem extends Record
    uid: UUID  # From Record
    label: UniqueLabel  # From Record
    obj_cls: str = "Actor"
    name: Optional[str] = None
    archetype: Optional[str] = None
    tags: Optional[set[str]] = None
    
    # Scope constraint - inferred from declaration or explicit
    scope: Optional[ScopeSelector] = None

class ScopeSelector(BaseModel):
    """Declares where a template is valid."""
    source_label: Optional[str] = None  # Exact block/scene label
    parent_label: Optional[str] = None  # Direct parent label
    ancestor_tags: Optional[set[str]] = None  # Tags in ancestor chain
    ancestor_labels: Optional[set[str]] = None  # Labels in ancestor chain
```

#### Declaration and Scope Inference

**Templates can be declared at any level. The parser infers scope from declaration location:**

```yaml
# World-level templates (no scope constraint)
templates:
  generic_guard:
    obj_cls: Actor
    archetype: "guard"
    hp: 50
    tags: ["npc"]
  # Inferred: scope = None (available everywhere)

scenes:
  village:
    # Scene-level templates (parent scope)
    templates:
      village_elder:
        obj_cls: Actor
        name: "Village Elder"
        archetype: "elder"
      # Inferred: scope.parent_label = "village"
    
    blocks:
      smithy:
        # Block-level templates (source scope)
        templates:
          forge_apprentice:
            obj_cls: Actor
            name: "Apprentice"
            profession: "blacksmith"
        # Inferred: scope.source_label = "village.smithy"
```

**Explicit scope override:**
```yaml
scenes:
  village:
    templates:
      # Override inferred scope - make globally available
      wandering_merchant:
        obj_cls: Actor
        archetype: "merchant"
        scope: null  # Explicit: available everywhere
      
      # Override with custom scope
      secret_contact:
        obj_cls: Actor
        scope:
          ancestor_tags: ["conspiracy", "hidden"]
```

#### Storage: Single World Registry

**All templates stored in one `world.template_registry` regardless of declaration location:**

```python
# In World.__init__
class World:
    def __init__(self, label: str, script_manager: ScriptManager):
        # Single registry for all templates
        self.template_registry = Registry(label=f"{label}_templates")
        
        # Compile templates from entire script hierarchy
        self._compile_templates()
    
    def _compile_templates(self):
        """Traverse script and add all templates to registry."""
        script = self.script_manager.master_script
        
        # Helper to add templates with inferred scope
        def add_templates(templates_dict, scope_context=None):
            if not templates_dict:
                return
            
            for label, template_data in templates_dict.items():
                # Parse into typed script (ActorScript, LocationScript, etc.)
                template = self._parse_template_script(template_data)
                
                # Infer scope if not explicit
                if template.scope is None and scope_context:
                    template.scope = ScopeSelector(**scope_context)
                
                # Add to registry (templates are Records)
                self.template_registry.add(template)
        
        # World level - no scope
        add_templates(script.templates)
        
        # Scene level - infer parent_label
        for scene_label, scene_data in script.scenes.items():
            add_templates(
                scene_data.templates,
                scope_context={'parent_label': scene_label}
            )
            
            # Block level - infer source_label
            for block_label, block_data in scene_data.blocks.items():
                qualified_label = f"{scene_label}.{block_label}"
                add_templates(
                    block_data.templates,
                    scope_context={'source_label': qualified_label}
                )
```

#### Queries: Standard Registry API

**Templates are Records, so use standard Registry queries:**

```python
# By label
guard_template = world.template_registry.find_one(
    label="generic_guard"
)

# By type
all_actors = world.template_registry.find_all(
    is_instance=ActorScript
)

# By tags
npc_templates = world.template_registry.find_all(
    is_instance=ActorScript,
    has_tags={"npc"}
)

# By attributes
smith_template = world.template_registry.find_one(
    is_instance=ActorScript,
    profession="blacksmith"
)

# Combined
city_guards = world.template_registry.find_all(
    is_instance=ActorScript,
    has_tags={"guard", "city"}
)
```

**Optional convenience views:**
```python
# Type-filtered properties (like graph.nodes, graph.edges)
@property
def actor_templates(self) -> list[ActorScript]:
    return list(self.template_registry.find_all(is_instance=ActorScript))

@property
def location_templates(self) -> list[LocationScript]:
    return list(self.template_registry.find_all(is_instance=LocationScript))
```

#### Scope-Based Selection

**Provisioners filter templates by scope before offering:**

```python
class TemplateProvisioner(Provisioner):
    def get_dependency_offers(self, requirement, *, ctx):
        """Find templates valid in current context."""
        registry = ctx.graph.world.template_registry
        
        # Find matching templates
        candidates = self._find_matching_templates(requirement, registry)
        
        # Filter by scope
        valid = [t for t in candidates if self._is_in_scope(t, ctx)]
        
        if not valid:
            return
        
        # Yield one offer per valid template
        for template in valid:
            yield DependencyOffer(
                requirement_id=requirement.uid,
                operation=ProvisioningPolicy.CREATE,
                cost=ProvisionCost.CREATE,
                proximity=0,
                provider_uid=template.uid,  # template UID used for deterministic tie-breaking
                accept_func=lambda ctx, t=template: self._instantiate(t, ctx)
            )
```

**Multiple template matches:**

- For `template_ref`, the expectation is that exactly one template matches. If no templates match, no offers are generated and a warning or validation error should be logged. If more than one template matches a given `template_ref`, this is treated as an **authoring error** and should be surfaced during validation.
- For criteria-only requirements (no `template_ref`), it is valid for multiple templates to match; one offer is produced per matching template and the global cost-based selection logic chooses the winner.

```python
    def _is_in_scope(self, template: ActorScript, ctx) -> bool:
        """Check if template's scope selector matches context."""
        if template.scope is None:
            return True  # No constraint = always valid
        
        scope = template.scope
        source = ctx.cursor  # Node being provisioned for
        
        # Check source label (exact match)
        if scope.source_label:
            if source.label != scope.source_label:
                return False
        
        # Check parent label
        if scope.parent_label:
            parent = getattr(source, 'parent', None)
            if not parent or parent.label != scope.parent_label:
                return False
        
        # Check ancestor tags
        if scope.ancestor_tags:
            required = set(scope.ancestor_tags)
            ancestors = self._get_ancestors(source)
            found = set()
            for ancestor in ancestors:
                found.update(getattr(ancestor, 'tags', set()))
            if not required.issubset(found):
                return False
        
        # Check ancestor labels
        if scope.ancestor_labels:
            required = set(scope.ancestor_labels)
            ancestors = self._get_ancestors(source)
            found = {a.label for a in ancestors}
            if not required.issubset(found):
                return False
        
        return True
    
    def _get_ancestors(self, node) -> list[Node]:
        """Walk up parent chain."""
        ancestors = []
        current = node
        while hasattr(current, 'parent') and current.parent:
            current = current.parent
            ancestors.append(current)
        return ancestors
```

#### Semantic Properties

- Templates are **immutable Record entities** (Pydantic models)
- Validated using same schema as world actors/locations (ActorScript, LocationScript)
- Stored in single `world.template_registry` (shared across all story instances)
- Queryable by label, type, tags, attributes using Registry API
- Filtered by scope at provision time
- Each instantiation creates independent node copy
- Instantiation uses `World._prepare_payload` for consistency

**Lifecycle:**
- Created once during `World.__init__` from parsed script
- Immutable at runtime (use `template.model_copy()` for variations)
- Shared across all story instances from same world
- Template modifications require world recompilation

**Provenance tracking:**
```python
# BuildReceipt records which template created which node
receipt.template_ref = template.label
receipt.template_hash = hash(template.model_dump_json())
```

---

## Reference Semantics in Roles/Settings

**Roles and Settings are Dependency edges** that specify what concept they need. The syntax determines provisioning behavior:

### 1. actor_ref: Named Reference

**"Find the specific named individual"**

```yaml
roles:
  blacksmith: {actor_ref: "bob"}
```

**Provisioning:**
- GraphProvisioner searches for bob affordance/node
- If found: cost=10 (EXISTING)
- If not found: **no offers** (error condition)

**Use when:**
- You need a specific named character
- Missing the character is an authoring error
- You want clear failure if character is removed

---

### 2. actor_criteria: Pattern Matching

**"Find any actor matching these properties"**

```yaml
roles:
  guard: {actor_criteria: {archetype: "guard", faction: "city"}}
```

**Provisioning:**
- GraphProvisioner searches existing nodes with matching attributes
- If found: cost=10-50 depending on proximity
- If not found: **no offers** (unless combined with template)

**Use when:**
- You need a type of character, not a specific one
- Multiple candidates might exist
- You want to reuse existing entities when possible

---

### 3. actor_template: Inline Creation

**"Create from this embedded blueprint"**

```yaml
roles:
  vendor:
    actor_template:
      name: "Street Vendor"
      inventory: ["apples", "bread"]
```

**Provisioning:**
- GraphProvisioner checks for existing matches (if policy allows)
- TemplateProvisioner creates from inline template: cost=200
- Always creates fresh instance (unless policy=ANY and match found)

**Use when:**
- One-off character specific to this scene
- Don't want to pollute template registry
- Self-contained scene definition

---

### 4. actor_template_ref: Registry Lookup

**"Create from named template in registry"**

```yaml
roles:
  guard: {actor_template_ref: "generic_guard"}
```

**Provisioning:**
- TemplateProvisioner queries `world.template_registry.find_one(label="generic_guard")`
- Filters by scope (checks if template is valid in current context)
- Creates from template: cost=200
- **Defaults to policy=CREATE** (always fresh instance)
- GraphProvisioner doesn't offer (unless policy=ANY)

**Use when:**
- Generic fungible entities
- Want to reuse template definition
- Each usage should be independent

**Scope filtering example:**
```yaml
templates:
  village_guard:
    obj_cls: Actor
    scope: {parent_label: "village"}

scenes:
  village:
    blocks:
      gates:
        roles:
          guard: {actor_template_ref: "village_guard"}  # ✓ In scope
  
  city:
    blocks:
      gates:
        roles:
          guard: {actor_template_ref: "village_guard"}  # ✗ Out of scope (no offer)
```

**Policy override for reuse:**
```yaml
roles:
  guard:
    actor_template_ref: "generic_guard"
    requirement_policy: ANY  # Check existing first, then create
    actor_criteria: {archetype: "guard"}  # Matching criteria for reuse
```

---

### 5. Fallback Chains: Combined Syntax

**"Try these strategies in order"**

```yaml
roles:
  companion:
    actor_ref: "alice"                     # 1. Try specific Alice
    actor_criteria: {archetype: "companion"}  # 2. Then any companion
    actor_template_ref: "companion_template"  # 3. Finally create generic
```

**Provisioning order:**
1. GraphProvisioner finds "alice" affordance (cost=10)
2. GraphProvisioner finds any companion (cost=20)
3. TemplateProvisioner creates from registry (cost=200, scope-filtered)

**Best offer wins** (lowest cost).

**Use when:**
- Preferred entity with graceful degradation
- Robust against missing affordances
- Dynamic casting based on availability

**Validation:**
- Can't specify both `actor_template` and `actor_template_ref`
- Missing `actor_ref` with no fallback is a warning (hard dependency fails)
- Missing `actor_template_ref` in registry is a warning (no offer generated)
- Scope mismatch on `actor_template_ref` prevents offer (logged)

---

## Shorthand Syntax

**For convenience, the parser expands shorthand forms:**

### Simple List → actor_ref

```yaml
# Input
roles: [alice, bob]

# Expands to
roles:
  alice: {actor_ref: "alice"}
  bob: {actor_ref: "bob"}
```

### Null Value → actor_ref from label

```yaml
# Input
roles:
  blacksmith: null

# Expands to
roles:
  blacksmith: {actor_ref: "blacksmith"}
```

### String Value → actor_ref override

```yaml
# Input  
roles:
  smith: bob           # Label is "smith", but references Bob
  protagonist: alice   # Label is "protagonist", but references Alice

# Expands to
roles:
  smith: {actor_ref: "bob"}
  protagonist: {actor_ref: "alice"}
```

**Use case:** Narrative substitution

```yaml
# Bob impersonating Alice
roles:
  alice: bob  # Content says {{ alice }}, but it's Bob!

blocks:
  reveal:
    content: |
      {{ alice.says("I've been Bob all along!") }}
```

### Dict without actor_ref → Infer from label

```yaml
# Input
roles:
  guard:
    actor_criteria: {archetype: "guard"}

# Expands to
roles:
  guard:
    actor_ref: "guard"  # Inferred!
    actor_criteria: {archetype: "guard"}
```

**Rationale:** If you name a role "guard", you probably want a guard affordance if it exists.

**Warning:** May bind to world affordance with same name

```yaml
actors:
  guard: {name: "Captain Guard", rank: "captain"}  # World affordance

scenes:
  gates:
    roles:
      guard: {actor_criteria: {archetype: "guard"}}
      # Parser infers: actor_ref: "guard"
      # Binds to Captain Guard (world affordance), ignoring criteria!

# To avoid: Be explicit
roles:
  guard:
    actor_criteria: {archetype: "guard"}
    actor_template_ref: "guard_template"  # No inference
```

---

## Cost Model & Selection

### Offer Cost Components

**Base costs:**
- `EXISTING`: 10 (node already exists in graph)
- `CREATE`: 200 (instantiate from template)

**Proximity modifier** (added to base):
- Same block: +0
- Same scene: +5
- Same episode: +10
- Elsewhere in graph: +20

**Final cost:** `base + proximity`

**Selection:** Offers sorted by `(cost, provider_uid)`
- Lowest cost wins
- Ties broken by provider_uid for determinism
- All offers and selection recorded in PlanningReceipt for audit

### Example

```python
# Two guards exist in graph:
# - guard_a in current scene (village.gates)
# - guard_b in distant episode

# GraphProvisioner offers:
# - guard_a: cost = 10 + 5 = 15 (existing, same scene)
# - guard_b: cost = 10 + 20 = 30 (existing, distant)

# TemplateProvisioner offers:
# - new guard from template: cost = 200 (create)

# Selection: guard_a wins (cost 15 < 30 < 200)
```

### Deterministic Tie-Breaking

When multiple offers have equal cost + proximity:

```python
# Sort key: (cost, proximity, provider_uid)
offers.sort(key=lambda o: (o.cost, o.proximity, o.provider_uid))
best = offers[0]
```

This ensures:
- Replay determinism (same UIDs = same selection)
- Audit trail (receipt shows all offers and why winner was chosen)
- No random selection

---

## World Creation Modes

World creation can operate in different modes along two orthogonal axes:

### Axis 1: Concept Materialization

**EAGER_CONCEPTS:** Create all actor/location nodes at story creation
```python
# All actors become concrete nodes immediately
bob_actor = Actor(name="Bob Smith", ...)
alice_actor = Actor(name="Alice Chen", ...)

# Affordances point to existing nodes
bob_affordance.destination = bob_actor
```

**LAZY_CONCEPTS:** Create concept nodes only when claimed
```python
# Only affordances exist, no concrete nodes
bob_affordance.destination = None  # Will create when needed

# When scene enters frontier and needs Bob:
bob_actor = Actor(name="Bob Smith", ...)
bob_affordance.destination = bob_actor
```

### Axis 2: Dependency Linking

**EAGER_LINKING:** Resolve all role/setting dependencies at story creation
```python
# Pre-link roles to actors
for role in all_roles:
    offers = collect_offers(role.requirement)
    role.destination = select_best(offers).accept()
```

**LAZY_LINKING:** Resolve dependencies during traversal (planning phase)
```python
# Create open dependencies
role.destination = None  # Will resolve at frontier

# When scene enters frontier:
# Frame.run_phase(PLANNING) provisions
```


### Preset Modes

```python
class WorldMode(Enum):
    FULL = "full"      # EAGER_CONCEPTS + EAGER_LINKING
    LAZY = "lazy"      # LAZY_CONCEPTS + LAZY_LINKING
    HYBRID = "hybrid"  # EAGER_CONCEPTS + LAZY_LINKING
```

**FULL Mode:**
- All concepts materialized as nodes
- All dependencies pre-linked
- Fast traversal (no provisioning overhead)
- High memory footprint
- Templates still in registry (for validation/reference)
- Good for: Small worlds, validation, testing

**LAZY Mode:**
- Concepts stay as templates in affordances
- Dependencies resolved at frontier
- Minimal memory footprint
- Provisioning overhead during play
- Good for: Large worlds, procedural content, unexplored branches

**HYBRID Mode (recommended):**
- All concepts materialized as nodes (known cast)
- Dependencies resolved at frontier (dynamic composition)
- Validates concept data upfront
- Flexible scene-to-concept binding
- Good for: Fixed cast in dynamic story, most branching narratives

### FULL Mode Is Per-Story, Not Global Precomputation

Although FULL mode eagerly resolves concept materialization and dependency linking, it does **not** precompute a permanent “baked graph” for the world as a whole.

Instead:

- FULL mode is executed **per story instance**, **per user**, at `world.create_story()`.
- Decisions are applied only to that story’s initial state.
- These provisioning decisions **do not** produce journal entries; the visible ledger for the player begins *after* initial bindings are made.

This avoids invalidating a global precomputed graph when:

- Users introduce user-specific entities or override templates.
- Branching logic depends on player state or profile.
- Stories require per-user cast composition or visibility rules.

In other words, FULL mode acts as “eager runtime initialization” at story creation time, not as a one-time compile-time bake for all players.

**Usage:**
```python
# Preset
story = world.create_story("story1", mode="hybrid")

# Custom
story = world.create_story("story1", 
    eager_concepts=True,
    eager_linking=False
)
```


## Dependency Retargeting Policy

Role-based dependencies are typically intended to be bound *once* and remain stable for the rest of a story traversal. To make this explicit and catch accidental re-binding, dependency edges may carry a lightweight lock policy:

```python
class DepLockPolicy(Enum):
    OPEN = "open"              # May be re-bound (for affordances / soft deps)
    LOCK_ON_BIND = "lock_on_bind"   # Bind once, then immutable
    CLOSED = "closed"          # Immutable even before binding (rare)
```

A `Dependency` edge then uses this policy to govern binding:

```python
class Dependency(Edge):
    lock_policy: DepLockPolicy = DepLockPolicy.LOCK_ON_BIND

    def bind_provider(self, provider_uid):
        if self.lock_policy is DepLockPolicy.CLOSED:
            raise ValueError("Dependency is CLOSED and cannot be bound.")

        if (
            self.destination is not None and
            self.lock_policy is DepLockPolicy.LOCK_ON_BIND
        ):
            raise ValueError("Dependency already bound (LOCK_ON_BIND).")

        # Normal binding logic
        self.destination = provider_uid
```

**Default intent:**

- **Roles / settings** → `LOCK_ON_BIND`: once the planner selects a provider for this dependency in a given story instance, it should not be silently re-bound.
- **Truly open affordances or soft dependencies** → `OPEN`: may be re-bound if provisioning logic explicitly chooses to do so.
- **Purely structural or system edges** → `CLOSED`: never touched by provisioning.

This keeps the overall graph model mutable (edges are still “state”), while making binding operations intentional and auditable instead of silent side effects.

---

## Provisioner Behavior

### GraphProvisioner

**Searches for existing nodes in the graph.**

```python
class GraphProvisioner(Provisioner):
    def get_dependency_offers(self, requirement, *, ctx):
        """Find existing nodes matching requirement."""
        
        # Build search criteria
        criteria = requirement.criteria or {}
        if requirement.identifier:
            criteria['label'] = requirement.identifier
        
        # Search existing nodes
        for node in ctx.graph.find_all(**criteria):
            if requirement.satisfied_by(node):
                # Calculate proximity
                proximity = self._calculate_proximity(node, ctx.cursor)
                
                yield DependencyOffer(
                    requirement_id=requirement.uid,
                    operation=ProvisioningPolicy.EXISTING,
                    cost=ProvisionCost.DIRECT + proximity,  # 10 + proximity
                    proximity=proximity,
                    provider_uid=node.uid,
                    accept_func=lambda: node
                )
        
        # Note: Does NOT offer for template_ref with policy=CREATE
        # (template_ref defaults to "create new")
```

**Proximity calculation:**
```python
def _calculate_proximity(self, node: Node, cursor: Node) -> int:
    """Calculate graph distance."""
    # Same block
    if node.uid == cursor.uid:
        return 0
    
    # Same scene
    if hasattr(cursor, 'parent') and hasattr(node, 'parent'):
        if cursor.parent == node.parent:
            return 5
    
    # Same episode (walk up parent chain)
    cursor_ancestors = self._get_ancestors(cursor)
    node_ancestors = self._get_ancestors(node)
    if cursor_ancestors and node_ancestors:
        if cursor_ancestors[-1] == node_ancestors[-1]:  # Same root episode
            return 10
    
    # Elsewhere
    return 20
```

### TemplateProvisioner

**Creates new nodes from template registry.**

```python
class TemplateProvisioner(Provisioner):
    def get_dependency_offers(self, requirement, *, ctx):
        """Find templates valid in current context."""
        registry = ctx.graph.world.template_registry
        
        # Find matching template
        template = self._find_template(requirement, registry)
        if not template:
            return
        
        # Check scope
        if not self._is_in_scope(template, ctx):
            logger.debug(
                f"Template '{template.label}' out of scope for {ctx.cursor.label}"
            )
            return
        
        # Offer to instantiate
        yield DependencyOffer(
            requirement_id=requirement.uid,
            operation=ProvisioningPolicy.CREATE,
            cost=ProvisionCost.CREATE,  # 200
            proximity=0,
            provider_uid=template.uid,  # Template's UID (for determinism)
            accept_func=lambda ctx: self._instantiate(template, ctx)
        )
    
    def _find_template(
        self, 
        requirement: Requirement, 
        registry: Registry
    ) -> ActorScript | LocationScript | None:
        """Find template matching requirement."""
        
        # Priority 1: Direct reference
        if requirement.template_ref:
            # Infer type from requirement context
            if hasattr(requirement, '_node_type'):  # Set by Role/Setting
                return registry.find_one(
                    label=requirement.template_ref,
                    is_instance=requirement._node_type
                )
            else:
                # Try both types
                return (
                    registry.find_one(label=requirement.template_ref, is_instance=ActorScript)
                    or registry.find_one(label=requirement.template_ref, is_instance=LocationScript)
                )
        
        # Priority 2: Criteria search
        if requirement.criteria:
            # Search by criteria (tags, attributes)
            return registry.find_one(**requirement.criteria)
        
        return None
    
    def _instantiate(
        self, 
        template: ActorScript | LocationScript, 
        ctx
    ) -> Node:
        """Instantiate concrete node from template."""
        world = ctx.graph.world
        
        # Resolve class
        cls = world.domain_manager.resolve_class(template.obj_cls)
        
        # Prepare payload (handles defaults, validation, graph injection)
        payload = world._prepare_payload(
            cls,
            template.model_dump(exclude={'scope'}),  # Don't pass scope to node
            ctx.graph
        )
        
        # Structure the node
        node = cls.structure(payload)
        
        return node
```

### Provisioner Ordering

```python
# In Frame._planning_collect_offers
provisioners = [
    GraphProvisioner(layer="local"),     # Check existing first
    TemplateProvisioner(layer="author"), # Create second
]

# Collect all offers
offers = []
for provisioner in provisioners:
    offers.extend(provisioner.get_dependency_offers(requirement, ctx=ctx))

# Sort by (cost, proximity, provider_uid)
offers.sort(key=lambda o: (o.cost, o.proximity, o.provider_uid))

# Accept winner
if offers:
    best_offer = offers[0]
    result = best_offer.accept(ctx=ctx)
    
    # Record in receipt
    receipt.offers = offers
    receipt.selected = best_offer
    receipt.provider = result
```

---

## Lifecycle and Persistence

### Named Individuals (Affordances)

**Creation:**
- Eager mode: Created at `World.create_story()`
- Lazy mode: Created when first claimed by a scene

**Persistence:**
- Remain in graph until explicitly removed
- State persists across scenes
- Reused by all scenes that reference them

**Example:**
```python
# Scene 1: Bob takes damage
bob.hp = 50  # Was 100

# Scene 2: Bob still injured
assert bob.hp == 50  # State persists
```

### Generic Template Instances

**Creation:**
- Created during PLANNING phase when scene enters frontier
- Fresh instance per `template_ref` usage (unless policy=ANY finds existing)

**Persistence:**
- Exist as long as scene/block is in scope
- May be garbage collected when scope exits (future feature)
- Changes don't affect other instances or template

**Example:**
```python
# City gates: guard_1 created from template
guard_1.hp = 50  # Player damages guard

# Palace: guard_2 created (different instance)
assert guard_2.hp == 100  # Fresh, undamaged

# Template unchanged
template = world.template_registry.find_one(label="generic_guard")
assert template.hp == 100  # Immutable
```

### Templates (Registry Records)

**Creation:**
- Compiled once during `World.__init__` from script
- All templates loaded into `world.template_registry`

**Persistence:**
- Immutable at runtime (Pydantic frozen models)
- Shared across all story instances from same world
- Live for entire World lifetime

**Modification:**
- Changes require world recompilation
- Use `template.model_copy()` for variations
- Overrides applied at instantiation time (future feature)

---

## Common Patterns

### Pattern 1: Global Characters with Fallback

```yaml
# Known cast of characters
actors:
  alice: {name: "Alice Chen", archetype: "companion"}
  bob: {name: "Bob Smith", archetype: "companion"}

# Generic fallback template
templates:
  companion_template:
    archetype: "companion"
    name: "Stranger"

scenes:
  forest:
    roles:
      companion:
        actor_ref: "alice"           # Try Alice first
        actor_criteria: {archetype: "companion"}  # Then any companion
        actor_template_ref: "companion_template"  # Finally create generic
```

**Behavior:**
- If Alice available: use Alice
- If Alice unavailable but Bob available: use Bob
- If no companions available: create generic from template

### Pattern 2: Scoped Templates for Variety

```yaml
templates:
  # World-level generic
  generic_guard:
    obj_cls: Actor
    archetype: "guard"
    hp: 50

scenes:
  village:
    templates:
      # Village-specific variant
      village_guard:
        obj_cls: Actor
        archetype: "guard"
        hp: 40
        faction: "village_militia"
      # Inferred: scope.parent_label = "village"
    
    blocks:
      gates:
        roles:
          guard: {actor_template_ref: "village_guard"}  # ✓ Uses village variant
  
  palace:
    templates:
      # Palace-specific variant
      palace_guard:
        obj_cls: Actor
        archetype: "guard"
        hp: 80
        faction: "royal_guard"
      # Inferred: scope.parent_label = "palace"
    
    blocks:
      entrance:
        roles:
          guard: {actor_template_ref: "palace_guard"}  # ✓ Uses palace variant
```

### Pattern 3: Dynamic Casting with State

```yaml
# Mission status determines casting
actors:
  alice: {name: "Alice", status: "available"}

scenes:
  briefing:
    roles:
      leader:
        actor_ref: "alice"  # Try Alice
        actor_criteria: {status: "available"}  # Then any available
        actor_template: {name: "Replacement", status: "available"}  # Create fallback
```

**At runtime:**
```python
# Alice sent on mission
alice.status = "on_mission"

# Next briefing scene
# GraphProvisioner can't find alice (wrong identifier) or available leader (criteria unmet)
# TemplateProvisioner creates "Replacement" from inline template
```

### Pattern 4: Aliasing for Perspective

```yaml
# Bob's perspective
scenes:
  bob_chapter:
    roles:
      protagonist: bob
      antagonist: alice

# Alice's perspective  
scenes:
  alice_chapter:
    roles:
      protagonist: alice
      antagonist: bob

# Shared content template uses {{ protagonist }} and {{ antagonist }}
```

### Pattern 5: Block-Local Specialists

```yaml
scenes:
  lab:
    blocks:
      containment:
        # Block-scoped template
        templates:
          containment_specialist:
            obj_cls: Actor
            name: "Dr. Chen"
            specialty: "containment"
          # Inferred: scope.source_label = "lab.containment"
        
        roles:
          expert: {actor_template_ref: "containment_specialist"}
      
      research:
        roles:
          expert: {actor_template_ref: "containment_specialist"}  # ✗ Out of scope!
```

---

## Anti-Patterns

### ❌ Named Individual in Templates

```yaml
# WRONG: Bob should be an affordance
templates:
  bob: {name: "Bob Smith"}

scenes:
  forge:
    roles:
      smith: {actor_template_ref: "bob"}  # Creates Bob_1
  
  tavern:
    roles:
      patron: {actor_template_ref: "bob"}  # Creates Bob_2 (duplicate!)
```

**Fix:** Move to actors (affordances)

```yaml
# RIGHT: Bob as affordance
actors:
  bob: {name: "Bob Smith"}

scenes:
  forge:
    roles:
      smith: {actor_ref: "bob"}  # Same Bob
  
  tavern:
    roles:
      patron: {actor_ref: "bob"}  # Same Bob
```

### ❌ Generic Template as Affordance

```yaml
# WRONG: Guards should use templates
actors:
  guard_1: {archetype: "guard"}
  guard_2: {archetype: "guard"}
  guard_3: {archetype: "guard"}
  # ... manually creating many similar entities
```

**Fix:** Use template with multiple references

```yaml
# RIGHT: Template for fungible guards
templates:
  guard_template: {archetype: "guard"}

scenes:
  gates:
    roles:
      guard: {actor_template_ref: "guard_template"}  # Creates guard_1
  
  palace:
    roles:
      guard: {actor_template_ref: "guard_template"}  # Creates guard_2 (different)
```

### ❌ Implicit Inference Collision

```yaml
# CONFUSING: Same name as world affordance
actors:
  guard: {name: "Captain", rank: "elite"}

scenes:
  gates:
    roles:
      guard: {actor_criteria: {rank: "standard"}}
      # Parser infers: actor_ref: "guard"
      # Binds to Captain, ignores criteria!
```

**Fix:** Be explicit about intent

```yaml
roles:
  guard:
    actor_criteria: {rank: "standard"}
    actor_template_ref: "standard_guard"  # No ambiguity
```

### ❌ Expecting Template Reuse Without policy=ANY

```yaml
# WRONG: Expecting GraphProvisioner to find existing
roles:
  guard: {actor_template_ref: "guard_template"}  # Always creates new!

# Later...
roles:
  another_guard: {actor_template_ref: "guard_template"}  # Creates another!
```

**Fix:** Use policy=ANY if you want reuse

```yaml
roles:
  guard:
    actor_template_ref: "guard_template"
    requirement_policy: ANY  # Check existing first
    actor_criteria: {archetype: "guard"}
```

### ❌ Template Without Scope Override

```yaml
# CONFUSING: Village template used in city
scenes:
  village:
    templates:
      merchant: {name: "Village Merchant"}
    # Inferred: scope.parent_label = "village"

scenes:
  city:
    roles:
      vendor: {actor_template_ref: "merchant"}  # ✗ Out of scope!
```

**Fix:** Make template global if needed elsewhere

```yaml
# Move to world level
templates:
  merchant: {name: "Generic Merchant"}

# OR override scope in village
scenes:
  village:
    templates:
      merchant:
        name: "Merchant"
        scope: null  # Available everywhere
```

---

## Implementation Checklist

### Phase 1: Template Registry ✓

**Core Infrastructure:**
- [x] BaseScriptItem extends Record (gets UID, label, tags)
- [ ] Add `scope: Optional[ScopeSelector]` to ActorScript/LocationScript
- [ ] Add `templates: dict` to SceneScript, BlockScript
- [ ] `World.template_registry = Registry()` in `__init__`
- [ ] `World._compile_templates()` - traverse script hierarchy, infer scope, add to registry

**Schema Support:**
- [ ] `ScopeSelector` model with source_label, parent_label, ancestor_tags, ancestor_labels
- [ ] Validation: templates can't have both template and template_ref
- [ ] Parser expansion: infer scope from declaration location

**Tests:**
- [ ] Template registry populated from world/scene/block templates
- [ ] Scope inference: world (None), scene (parent_label), block (source_label)
- [ ] Scope override: explicit scope replaces inferred
- [ ] Registry queries: by label, type, tags, attributes

### Phase 2: TemplateProvisioner Registry Integration

**Provisioner Updates:**
- [ ] `TemplateProvisioner._find_template()` queries `world.template_registry`
- [ ] Scope filtering: `_is_in_scope(template, ctx)` checks selectors
- [ ] Instantiation: use `World._prepare_payload()` for consistency
- [ ] Provenance: record template_ref and template_hash in BuildReceipt

**Tests:**
- [ ] Template found by template_ref
- [ ] Template filtered by scope (in vs out)
- [ ] Template instantiation creates correct node type
- [ ] Missing template_ref logs warning, no offer

### Phase 3: World Creation Modes

**Mode Support:**
- [ ] `World.create_story(mode="full"|"lazy"|"hybrid")`
- [ ] Or explicit: `eager_concepts=bool, eager_linking=bool`
- [ ] `_build_actors_eager()` - creates nodes + affordances pointing to them
- [ ] `_build_actors_lazy()` - creates affordances with templates only
- [ ] `_build_scenes_full()` - pre-links dependencies
- [ ] `_build_scenes_lazy()` - leaves dependencies open

**Tests:**
- [ ] FULL: all concepts materialized, all deps pre-linked
- [ ] LAZY: no concepts yet, deps open
- [ ] HYBRID: concepts materialized, deps open

### Phase 4: Cost Model & Selection

**Provisioner Refinement:**
- [ ] GraphProvisioner: calculate proximity, add to cost
- [ ] Offer sorting: `(cost, proximity, provider_uid)`
- [ ] PlanningReceipt: record all offers and selected offer
- [ ] GraphProvisioner: don't offer for template_ref with policy=CREATE

**Tests:**
- [ ] Proximity calculation: same block/scene/episode/distant
- [ ] Cost comparison: existing closer < existing farther < create
- [ ] Deterministic tie-break by provider_uid
- [ ] Receipt shows all offers and selection reason

### Phase 5: Shorthand Expansion ✓ (Mostly exists)

**Parser Enhancements:**
- [ ] List → actor_ref expansion
- [ ] Null → actor_ref from label
- [ ] String → actor_ref override
- [ ] Dict → infer actor_ref if missing (with warning for collisions)

**Validation:**
- [ ] Can't have both actor_template and actor_template_ref
- [ ] Warning if inferred actor_ref collides with world affordance

### Phase 6: Documentation & Polish

- [ ] This design doc ✓
- [ ] Usage examples in integration tests
- [ ] Author guide in Sphinx docs
- [ ] Error messages for missing templates, scope violations
- [ ] Logging: debug level for scope checks, info for provisions

---

## Future Enhancements

### Template Overrides

```yaml
roles:
  guard:
    actor_template_ref: "guard_template"
    actor_overrides:
      hp: 75              # Replace value
      equipment: ["spear"]  # Replace array
```

Merge strategy: deep-merge overrides into template at instantiation.

### Garbage Collection

```python
# When exiting episode/scene:
for concept in provisioned_concepts:
    if concept.tags.contains("generic") and not actively_referenced:
        graph.remove(concept)
```

### Template Inheritance

```yaml
templates:
  guard_base: {archetype: "guard", hp: 50}
  
  elite_guard:
    inherits: guard_base
    hp: 100
    equipment: ["steel_armor"]
```

### Multi-Criteria Scope Selectors

```yaml
templates:
  special_npc:
    scope:
      any_of:
        - parent_label: "village"
        - ancestor_tags: ["special_event"]
      context_vars:
        player.faction: "rebels"
```

---

## Implementation Status

### All Core Features: ✅ COMPLETE

Verified implementations:
- Template registry with scope filtering
- TemplateProvisioner creates from templates
- GraphProvisioner binds existing affordances
- Role/Setting edges wire to Dependencies
- World._wire_roles() and ._wire_settings() functional
- Test coverage in test_world_materialization.py

Current runtime behavior wires role and setting edges with attached requirements, leaving
all provisioning to the planning phase:

- GraphProvisioner binds existing affordances that satisfy the requirement.
- TemplateProvisioner materializes nodes from templates when no affordance is available.

World creation does not pre-link destinations. The compiler remains lean and the virtual
machine owns provisioning. A future optimization could add a `pre_plan=True` flag on the
VM to pre-run planning for faster traversal; this would remain outside the World
builder.
