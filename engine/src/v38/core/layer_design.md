# Package Layer Design

Intent
------

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


Layer Responsibilities
----------------------

Each layer has clear responsibilities and dependency direction:

```
Service  → Lifecycle management, persistence, API
Story    → Domain semantics, narrative concepts
VM       → Temporal evolution, context-dependent evaluation
Core     → Timeless primitives and mechanisms (no context selection)
```

Lower layers MUST NOT import from higher layers. Higher layers compose lower-layer primitives.

The key insight: **anything requiring a shaped context for evaluation belongs in the layer 
where that context is defined.**

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

### Litmus Test

| Question                                        | If Yes →   |
|-------------------------------------------------|------------|
| Can I evaluate this with just the data?         | Core       |
| Is this a pure transform of inputs to outputs?  | Core       |
| Do I need to know "where we are" / "what step"? | VM         |
| Does the answer change if the cursor moves?     | VM         |
| Does it require narrative domain knowledge?     | Story      |
| Does it manage persistence or access control?   | Service    |

### Core Layer

```
tangl.core
├── Lifecycle      → existence, frozen vs mutable, identity, uniqueness
├── Shape          → structure/unstructure, Registry, Graph topology, Singleton
├── State          → HasState, locals dict, attribute access
├── Behavior       → dispatch, receipts, aggregation
└── Selection      → Selector (query), Requirement (satisfaction)
```

**Non-Goals** (Explicitly Out of Core)

Core does NOT define:
- Requirements, satisfaction, provisioning, scope visibility (VM)
- Traversal, cursor, steps, epochs, ledgers (VM)
- Narrative semantics or syntax (Story)
- Persistence policies, transactions, access control (Service)

Core provides vocabulary to implement these in higher layers.

### Systems Layers — What HAPPENS (Contextual/Temporal)

VM -> graph traversal and provisioning rules, cursor controller, rollback/audit
Service -> persistence, user/account management, and lifecycle endpoints

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

```
tangl.service
├── Persistence    → load/save via encode/decode
├── Endpoints      → controller API surface
├── Orchestration  → hydrate dependencies, write-back
└── Sessions       → user identity, access control
```

**Service manages who _owns_ shapes and behaviors.**

### Application Layers  — What It MEANS (Domain Semantics)

Story -> layers fabula concepts, episodic process, syuzhet on top of VM
Discourse -> extensions for adapting story concepts to text-narrative engine
Media -> extensions for adapting story concepts to media engine
Mechanics -> extensions for modeling specialized story concepts

```
tangl.story
├── Narrative concepts  → Fabula, Episode, Concept, Block
├── Domain behaviors    → registered handlers for story phases
└── Thematic projection → how archetypes render to prose
```

### Author Layers

Story.World -> content and rules for a particular story

```
tangl.story.world
└── Author schemas      → what a "world" looks like
```
