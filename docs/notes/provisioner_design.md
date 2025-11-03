# Provisioner System Design (v3.7)

## Overview

The provisioner system solves the **frontier resolution problem**: when story execution reaches a node with unresolved dependencies or affordances, how do we find or create the nodes needed to continue?

## Core Concepts

### 1. Requirements

A **Requirement** expresses what's needed:
- **identifier**: "door", "companion", UUID
- **criteria**: `{has_tags: ['wooden', 'locked']}`
- **template**: `{label: 'door', locked: True}`
- **policy**: EXISTING | UPDATE | CREATE | CLONE | ANY

Requirements live on **open edges**:
- **Dependency**: edge from source → missing destination
- **Affordance**: edge from missing source → destination

### 2. Provisioners

A **Provisioner** is an entity that knows how to find or create nodes.

**Key insight**: Provisioners don't *resolve* requirements directly. Instead, they **generate offers** - proposals for how the requirement could be satisfied.

```python
class Provisioner:
    def get_dependency_offers(requirement, *, ctx) -> Iterator[DependencyOffer]:
        """Respond to a specific need."""
    
    def get_affordance_offers(node, *, ctx) -> Iterator[AffordanceOffer]:
        """Proactively offer actions/affordances."""
```

Provisioners are **NOT Behaviors**, but follow the `(caller, *, ctx)` convention. They're entities in a registry that get queried by the planning system.

### 3. Offers

An **Offer** is a proposal with a callback:

```python
class DependencyOffer:
    requirement_id: UUID
    operation: str  # 'EXISTING', 'CREATE', etc.
    cost: ProvisionCost  # Lower is better
    accept_func: Callable[[], Node]  # Lazy execution
    
    def accept(*, ctx) -> Node:
        """Execute the callback and return provider."""
```

Offers are **lazy** - no work happens until `.accept()` is called.

### 4. Cost Model

Offers have costs that determine priority:

1. **DIRECT** (10): Node already exists (EXISTING)
2. **LIGHT_INDIRECT** (50): Modify existing node (UPDATE)
3. **HEAVY_INDIRECT** (100): Clone and modify (CLONE)
4. **CREATE** (200): Build from scratch (CREATE)

Direct providers are **always preferred** over indirect ones.

## Design Decisions

### Why separate Provisioner from Behavior?

**Behaviors** are dispatched based on selectors/filters - they're invoked as part of a phase.

**Provisioners** are queried for offers - they're iterated over and asked "what can you do?"

The distinction:
- Behaviors are *reactive* (respond to dispatch)
- Provisioners are *queryable* (generate proposals on demand)

Provisioners follow `(caller, *, ctx)` convention for consistency, but aren't registered in `BehaviorRegistry`.

### Why two modes (dependency vs affordance)?

**Dependency mode** is **responsive**:
```python
# "I need a door here. What are my options?"
requirement = Requirement(identifier='door', policy=ANY)
offers = provisioner.get_dependency_offers(requirement, ctx=ctx)
```

**Affordance mode** is **proactive**:
```python
# "What actions are available at this location?"
offers = provisioner.get_affordance_offers(current_node, ctx=ctx)
```

This mirrors the dual nature of frontier resolution:
- Fill in missing structure (dependencies)
- Reveal available options (affordances)

### Why offers instead of direct resolution?

**Separation of concerns**:
1. **Provisioner** knows *what's possible* (generate offers)
2. **Selector** decides *what to choose* (pick best offer)
3. **Acceptor** executes the choice (call `offer.accept()`)

This allows:
- Multiple provisioners to compete with offers
- Sophisticated selection logic (cost, proximity, constraints)
- Deferred execution (offers can be cached, filtered, sorted)
- Clear audit trail (which offer was selected and why)

### Why unique labels for affordances?

Affordances project into namespaces:
```python
# If there's an affordance labeled "sing"
ns['sing'] = affordance.source  # The singer
```

Multiple affordances with the same label would collide in the namespace, so uniqueness is enforced per destination.

Dependencies *can* have overlapping labels because only one gets satisfied:
```python
# Both possible, but only one will be bound:
Dependency(source=scene, label='villain', identifier='darth_vader')
Dependency(source=scene, label='villain', identifier='starkiller')
```

## Layering

Provisioners are organized in layers:

1. **LOCAL**: Node/subgraph-specific provisioners
2. **AUTHOR**: World/story-specific provisioners  
3. **APPLICATION**: App-level provisioners (asset managers, etc.)
4. **GLOBAL**: Default provisioners (template creation, etc.)

The planning system queries layers in order, with **proximity** as a tiebreaker:
- Closer provisioners (local) win ties over distant ones (global)
- Within a layer, registration order breaks ties

## Standard Provisioner Types

### GraphProvisioner
Searches existing nodes in a registry. Always cheapest.

```python
graph_prov = GraphProvisioner(node_registry=graph, layer='local')
offers = graph_prov.get_dependency_offers(requirement, ctx=ctx)
# Yields EXISTING offers for matching nodes
```

### TemplateProvisioner
Creates new nodes from templates.

```python
template_prov = TemplateProvisioner(
    template_registry={'door': {...}, 'window': {...}},
    layer='author'
)
offers = template_prov.get_dependency_offers(requirement, ctx=ctx)
# Yields CREATE offers if requirement has template
```

### UpdatingProvisioner
Finds existing nodes and modifies them.

```python
updating_prov = UpdatingProvisioner(node_registry=graph, layer='author')
offers = updating_prov.get_dependency_offers(requirement, ctx=ctx)
# Yields UPDATE offers if requirement has template
```

### CloningProvisioner
Clones existing nodes and evolves them.

```python
cloning_prov = CloningProvisioner(node_registry=graph, layer='author')
offers = cloning_prov.get_dependency_offers(requirement, ctx=ctx)
# Yields CLONE offers if requirement has template
```

### Custom Affordance Provisioners
Offer actions based on world state.

```python
class CompanionProvisioner(Provisioner):
    def get_affordance_offers(self, node, *, ctx):
        yield AffordanceOffer(
            label='sing',
            accept_func=lambda dest: create_sing_affordance(dest),
            target_tags={'musical'}  # Only offer in musical scenes
        )
```

## Integration with Planning Phase

(This is the part we're NOT implementing yet, but here's how it fits together)

### Phase Flow

```python
# 1. COLLECT OFFERS (provisioners generate proposals)
all_offers = []
for provisioner in discovered_provisioners:
    if requirement:
        all_offers.extend(provisioner.get_dependency_offers(requirement, ctx=ctx))
    else:
        all_offers.extend(provisioner.get_affordance_offers(node, ctx=ctx))

# 2. SELECT OFFERS (apply policy and priority)
selected_offers = select_best_offers(all_offers)

# 3. ACCEPT OFFERS (execute callbacks)
for offer in selected_offers:
    provider = offer.accept(ctx=ctx)
    requirement.provider = provider

# 4. COMPOSE RECEIPT (aggregate results)
return PlanningReceipt(
    satisfied=len(selected_offers),
    unresolved=[r.uid for r in hard_requirements if not r.satisfied]
)
```

### Provisioner Discovery

Provisioners are discovered through `scoped_dispatch`:
```python
def do_get_provisioners(anchor: Node, *, ctx: Context) -> list[Provisioner]:
    """
    Walk behavior registry layers and gather provisioners.
    
    Discovery order:
    1. LOCAL: anchor.provisioners (if hasattr)
    2. AUTHOR: graph.provisioners or author-level registries
    3. APPLICATION: app-level provisioners
    4. GLOBAL: vm_dispatch registered provisioners
    """
    receipts = scoped_dispatch(
        caller=anchor,
        ctx=ctx,
        task="get_provisioners",
    )
    return CallReceipt.merge_results(*receipts)
```

## Example Scenarios

### Scenario 1: Hallway with Three Doors

```python
hallway = graph.add_node(label="hallway")

# Three dependencies for doors
for i in range(3):
    req = Requirement(
        graph=graph,
        identifier=f'door_{i}',
        template={'label': f'door_{i}', 'obj_cls': Node},
        policy=ProvisioningPolicy.ANY
    )
    Dependency(graph=graph, source=hallway, requirement=req, label=f'door_{i}')

# Provisioners offer solutions:
# - GraphProvisioner: "I found door_0 already exists" (EXISTING, cost=10)
# - TemplateProvisioner: "I can create door_1 from template" (CREATE, cost=200)
# - TemplateProvisioner: "I can create door_2 from template" (CREATE, cost=200)

# Selection picks EXISTING for door_0, CREATE for door_1 and door_2
```

### Scenario 2: Companion with Conditional Affordances

```python
companion = graph.add_node(label="friend", tags={'happy', 'musical'})
scene = graph.add_node(label="scene", tags={'peaceful'})

companion_prov = CompanionProvisioner(companion_node=companion)

# Proactive offers:
offers = list(companion_prov.get_affordance_offers(scene, ctx=ctx))
# -> ['talk', 'sing']  (sing only offered because companion is happy)

# Accept "sing" offer
sing_offer = next(o for o in offers if o.label == 'sing')
affordance = sing_offer.accept(ctx=ctx, destination=scene)

# Now ns['sing'] = companion
```

### Scenario 3: Villain Fallback

```python
scene = graph.add_node(label="scene")

# Prefer Darth Vader, but accept any villain
req1 = Requirement(
    graph=graph,
    identifier='darth_vader',
    policy=ProvisioningPolicy.EXISTING
)
Dependency(graph=graph, source=scene, requirement=req1, label='villain')

req2 = Requirement(
    graph=graph,
    identifier='starkiller',
    policy=ProvisioningPolicy.EXISTING
)
Dependency(graph=graph, source=scene, requirement=req2, label='villain')

# If darth_vader exists:
#   GraphProvisioner offers EXISTING (cost=10)
#   req1 is satisfied, req2 is ignored (same label)
# If darth_vader missing but starkiller exists:
#   req1 unresolved, req2 satisfied with EXISTING
```

## Testing Strategy

### Unit Tests (Provisioner in Isolation)

```python
def test_graph_provisioner_finds_existing_node():
    graph = Graph()
    node = graph.add_node(label="door")
    prov = GraphProvisioner(node_registry=graph)
    
    req = Requirement(identifier="door", policy=ProvisioningPolicy.EXISTING)
    ctx = Context(graph=graph, cursor_id=node.uid)
    
    offers = list(prov.get_dependency_offers(req, ctx=ctx))
    
    assert len(offers) == 1
    assert offers[0].operation == 'EXISTING'
    assert offers[0].cost == ProvisionCost.DIRECT
    
    provider = offers[0].accept(ctx=ctx)
    assert provider is node
```

### Integration Tests (Multiple Provisioners)

```python
def test_cheapest_offer_wins():
    graph = Graph()
    existing_door = graph.add_node(label="door")
    
    req = Requirement(
        identifier="door",
        template={'label': 'door'},
        policy=ProvisioningPolicy.ANY
    )
    ctx = Context(graph=graph, cursor_id=existing_door.uid)
    
    graph_prov = GraphProvisioner(node_registry=graph)
    template_prov = TemplateProvisioner(template_registry={'door': {...}})
    
    offers = []
    offers.extend(graph_prov.get_dependency_offers(req, ctx=ctx))
    offers.extend(template_prov.get_dependency_offers(req, ctx=ctx))
    
    offers.sort(key=lambda o: o.cost)
    
    best = offers[0]
    assert best.operation == 'EXISTING'  # Cheaper than CREATE
    assert best.accept(ctx=ctx) is existing_door
```

## Migration Path

From current code to this design:

1. **Keep existing Requirement/Dependency/Affordance** - they're solid
2. **Replace Provisioner class** - new design focused on offer generation
3. **Introduce Offer types** - DependencyOffer, AffordanceOffer with callbacks
4. **Update tests** - focus on offer generation, not direct resolution
5. **(Later) Wire into planning phase** - integrate with dispatch system

## Open Questions

1. **Where do provisioners live?**
   - Graph attribute? Node attribute? Registry?
   - How does inheritance work (graph → subgraph → node)?

2. **How are provisioners discovered?**
   - Walk graph ancestry like namespace resolution?
   - Query behavior registries via `task="get_provisioners"`?

3. **Should offers be cached?**
   - Generate once and reuse?
   - Or regenerate for each planning phase?

4. **How to handle offer deduplication?**
   - Multiple provisioners might offer the same node
   - Use (provider_id, operation) as key?

5. **Should provisioners be typed by what they provision?**
   - NodeProvisioner, EdgeProvisioner, MediaProvisioner?
   - Or keep generic and rely on offer types?

## Summary

This design focuses the provisioner on **offer generation** rather than direct resolution. Benefits:

- ✅ Clear separation of concerns (generate vs select vs execute)
- ✅ Lazy execution (offers are proposals until accepted)
- ✅ Cost-based prioritization (direct < indirect)
- ✅ Extensible (easy to add new provisioner types)
- ✅ Testable (provisioners isolated from planning phase)
- ✅ Flexible (supports both dependency and affordance modes)

Next steps:
1. Validate this design with a few concrete examples
2. Update existing tests to match new API
3. Implement concrete provisioner classes
4. **(Later)** Integrate with planning/dispatch system
