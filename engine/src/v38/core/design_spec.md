# Core Subpackage Design Principles

Core defines shared vocabulary and generic data structures and algorithms

## 1. Three Verbs

All operations reduce to compositions of:

| Verb         | Semantics                                           | Returns             |
|--------------|-----------------------------------------------------|---------------------|
| **Select**   | Filter + rank candidates using pure query           | `Iterable[T]`       |
| **Dispatch** | Execute selected behaviors, produce trace           | `Iterable[Receipt]` |
| **Resolve**  | Materialize instance from references/recipes/offers | `T`                 |

Higher layers (VM, Story, Service) express logic as compositions of these primitives, not parallel verbs.

**Notes:**
- "Dispatch" is a mechanism in Core; "which behavior registries are active" is context selection (VM)
- "Resolve" unifies: provisioning, templates, snapshots, singleton references, media

## 2. Separation of Concerns

Core types keep these concerns independent:

| Concern       | Trait           | Contract                                                   |
|---------------|-----------------|------------------------------------------------------------|
| Identity      | `HasIdentity`   | Stable identifiers; never derived from ordering or content |
| Content       | `HasContent`    | Content equality/hash meaningful only for frozen content   |
| Ordering      | `HasOrder`      | Deterministic ordering; never participates in identity     |
| State         | `HasState`      | Mutable locals; not used for content hashing               |
| Structuring   | `Untructurable` | Internal constructor form                                  |

**Key rule:** Un/structuring is _not_ serialization. Unstructured data may carry Python-native objects (including live Type references); data is flattened to be JSON/YAML-safe in a separate service.

## 3. Reference by ID, Resolve at Access

Registry-aware entities never hold direct pointers to other members of their registry. They store indirect references to other members via UUIDs.  These are usually resolved lazily on property access.

**Exception:** Owning boundaries may embed nested unstructurable children (e.g., Registry containing members), but embedding must be explicit, type-checked, and round-trip guaranteed.

## 4. Layer Independence

Each layer has clear responsibilities and dependency direction:

```
Service  → Lifecycle management, persistence, API
Story    → Domain semantics, narrative concepts
VM       → Temporal evolution, context-dependent evaluation
Core     → Timeless primitives and mechanisms (no context selection)
```

Lower layers MUST NOT import from higher layers. Higher layers compose lower-layer primitives.

## 5. Portability

Core types should be implementable in any language with:
- Algebraic data types or class inheritance
- First-class functions
- Associative collections (dict/map)
- Ordered collections (list/array)

Avoid Python-specific magic where possible. Document where unavoidable.

---

# Layer Responsibilities

The key insight: **anything requiring a shaped context for evaluation belongs in the layer where that context is defined.**

### Litmus Test

| Question                                        | If Yes →   |
|-------------------------------------------------|------------|
| Can I evaluate this with just the data?         | Core       |
| Is this a pure transform of inputs to outputs?  | Core       |
| Do I need to know "where we are" / "what step"? | VM         |
| Does the answer change if the cursor moves?     | VM         |
| Does it require narrative domain knowledge?     | Story      |
| Does it manage persistence or access control?   | Service    |

## Core — What IS (Contextless/Timeless)

```
tangl.core
├── Lifecycle      → existence, frozen vs mutable, identity, uniqueness
├── Shape          → structure/unstructure, Registry, Graph topology, Singleton
├── State          → HasState, locals dict, attribute access
├── Behavior       → dispatch, receipts, aggregation
└── Selection      → Selector (query), Requirement (satisfaction)
```

Core provides shapes and context-free behaviors for Graph, but traversal semantics are deferred to VM.

## VM — What HAPPENS (Contextual/Temporal)

```
tangl.vm
├── Evolution      → cursor movement, phase bus, step counter, traversal
├── Observation    → visibility, availability, frontier discovery
├── Provisioning   → find-or-create against requirements + scope
├── Journaling     → emit fragments to stream
└── Snapshotting   → capture graph state and deltas for replay/rollback
```

**VM interprets Core shapes:**
- Scope visibility rules
- Predicate evaluation against runtime state

## Story — What It MEANS (Domain Semantics)

```
tangl.story
├── Narrative concepts  → Fabula, Episode, Concept, Block
├── Domain behaviors    → registered handlers for story phases
├── Thematic projection → how archetypes render to prose
└── Author schemas      → what a "world" looks like
```

## Service — Who OWNS It (Lifecycle Management)

```
tangl.service
├── Persistence    → load/save via encode/decode
├── Endpoints      → controller API surface
├── Orchestration  → hydrate dependencies, write-back
└── Sessions       → user identity, access control
```

## Layer Dependency Rules

```
┌─────────────────────────────────────────────────────────────┐
│  Service  └── imports: vm, story, core                      │
├─────────────────────────────────────────────────────────────┤
│  Story    └── imports: vm, core                             │
├─────────────────────────────────────────────────────────────┤
│  VM       └── imports: core                                 │
├─────────────────────────────────────────────────────────────┤
│  Core     └── imports: (nothing from tangl)                 │
└─────────────────────────────────────────────────────────────┘
```

## Dispatch Layer Mapping Parallels

| Layer       | Code      | Registry            | Typical Tasks                   |
|-------------|-----------|---------------------|---------------------------------|
| GLOBAL      | core      | `core.dispatch`     | Auditing, logging               |
| SYSTEM      | vm        | `vm.dispatch`       | Phase handlers, provisioning    |
| SYSTEM      | service   | `service.dispatch`  | Api, persistence                |
| APPLICATION | story     | `story.dispatch`    | Content rendering, domain rules |
| APPLICATION | mechanics | `story.dispatch`    | Extend story concepts           |
| APPLICATION | discourse | `story.dispatch`    | Extend story narrative          |
| APPLICATION | media     | `story.dispatch`    | Extend story media              |
| AUTHOR      | world     | `world.dispatch`    | World-specific mechanics        |
| LOCAL       | vm.frame  | `vm.frame.dispatch` | One-off handlers                |

---

## Canonical Composition Patterns

### Layered Dispatch

```python
# Select → Dispatch → Aggregate
behaviors = Registry.chain_find_all(*registries, selector=Selector(attributes={'task': task}))
receipts = [b(*args, ctx=ctx, **kwargs) for b in sorted(behaviors, key=lambda b: b.sort_key())]
result = Receipt.first_non_null(*receipts)
```

### Find-or-Create (Provisioning)

```python
# Select existing → Resolve if none
existing = registry.find_one(req.selector)
if existing is not None:
    return existing
return resolve(req, satisfiers, ctx=ctx)
```

### Snapshot/Template Materialization

```python
# Templates are Satisfiers that return Offers
class TemplateSatisfier(Satisfier[T]):
    def get_offers(self, req, ctx=None):
        if self.template_matches(req):
            yield TemplateOffer(template=self.template, cost=self.cost)

class TemplateOffer(Offer[T]):
    def accept(self, ctx=None):
        kind, kwargs = self.template.reduce()
        return Entity.unreduce(kind, {**kwargs, "uid": uuid4()})  # Fresh instance
```

---

## Non-Goals (Explicitly Out of Core)

Core does NOT define:
- Cursor, steps, epochs, ledgers (VM)
- Phase lists or story semantics (VM/Story)
- Scope visibility and pattern interpretation (VM)
- Persistence policies, transactions, access control (Service)
- Global registries chosen implicitly (all layers explicit)

Core only provides vocabulary to implement these elsewhere.

---

## File Organization

```
tangl/core/
├── __init__.py           # Public API exports
├── identity.py           # HasIdentity, uid, labels, tags
│
│   # Discovery
├── selector.py           # Selector, match()
├── registry.py           # Registry, RegistryAware, EntityGroup, chain_find_all()
│
│   # Lifecycle
├── record.py             # Record, HasContent, HasOrder, OrderedRegistry, sort_key()
├── singleton.py          # Singleton, InstanceInheritance
│
│   # Relationships
├── graph/
│   ├── __init__.py
│   ├── graph.py          # GraphItem, Graph (Registry[GraphItem])
│   ├── subgraph.py       # Subgraph (EntityGroup[GraphItem])
│   ├── node.py           # Node
│   └── edge.py           # Edge
│
│   # Doing things
├── runtime_op.py         # RuntimeOp, Query, Predicate, Effect
├── behavior/
│   ├── __init__.py
│   ├── behavior.py       # Behavior, Priority, DispatchLayer
│   ├── receipt.py        # Audit receipt, aggregators
│   └── behavior_registry.py  # BehaviorRegistry (Registry[Behavior])
├── dispatch              # Hooks for create(), new(), add(), get(), remove()
│
│   # Creation
├── unstructurable.py     # Unstructurable, un/structure()
├── token.py              # Delegate to singleton
└── template.py           # Semi-structured data, TemplateRegistry
```

---

## Exit Criteria (Semantic Tests)

| Criterion                      | What It Validates                                    |
|--------------------------------|------------------------------------------------------|
| Identity invariants            | `uid` always in identifiers; identifiers stable      |
| Reduce round-trip              | `structure(unstructure(x))` yields equivalent object |
| Selector purity                | Deterministic; no side effects                       |
| Registry chain selection       | Stable, predictable ordering                         |
| Dispatch trace + aggregation   | Stable ordering + clear aggregation semantics        |
| Resolve protocol               | Can choose between offers; deterministic selection   |
| Singleton reference semantics  | Unstructured as reference; structures via lookup     |
| Singleton instance inheritance | Reference chain correctly resolves                   |
| Graph topology purity          | `successors/predecessors` need no runtime context    |


