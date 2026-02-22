# tangl.core38 — Design Notes

> Architectural intent, design decisions, and rationale for the core38 subpackage
> of the StoryTangl narrative engine (v3.8 framework).

---

## Position in the Architecture

Core is the timeless, context-free foundation of StoryTangl. It provides the vocabulary
and mechanisms that all higher layers compose, but it has **no awareness of narrative
semantics, temporal evolution, or persistence concerns**. The dependency direction is
strictly upward:

```
Service  → Lifecycle management, persistence, API
Story    → Domain semantics, narrative concepts
VM       → Temporal evolution, context-dependent evaluation
Core     → Timeless primitives and mechanisms
```

Lower layers MUST NOT import from higher layers. The key architectural insight is that
**anything requiring a shaped context for evaluation belongs in the layer where that
context is defined.**

### Litmus Test

| Question                                        | Layer      |
|-------------------------------------------------|------------|
| Can I evaluate this with just the data?         | Core       |
| Is this a pure transform of inputs to outputs?  | Core       |
| Do I need to know "where we are" / "what step"? | VM         |
| Does the answer change if the cursor moves?     | VM         |
| Does it require narrative domain knowledge?     | Story      |
| Does it manage persistence or access control?   | Service    |

### The Three Primitive Verbs

All operations in the system reduce to compositions of three primitives:

| Verb         | Semantics                                           | Returns             |
|--------------|-----------------------------------------------------|---------------------|
| **Select**   | Filter + rank candidates using pure query           | `Iterable[T]`       |
| **Dispatch** | Execute selected behaviors, produce trace           | `Iterable[Receipt]` |
| **Resolve**  | Materialize instance from references/recipes/offers | `T`                 |

Core defines the mechanisms for Select and Dispatch. Resolve is expressed as compositions
of these primitives at higher layers (VM provisioning, template materialization).
Higher layers express logic as compositions of these primitives, not parallel verbs.


## Core Module Map

```
tangl.core38
├── Lifecycle      → bases.py      (existence, frozen vs mutable, identity, uniqueness)
├── Shape          → entity.py     (Entity: canonical concrete composition)
│                  → registry.py   (Registry, RegistryAware, EntityGroup, HierarchicalGroup)
│                  → graph.py      (Graph, Node, Edge, Subgraph, HierarchicalNode)
│                  → singleton.py  (Singleton, InstanceInheritance)
│                  → token.py      (Token[X] — wrapper class factory)
│                  → record.py     (Record, OrderedRegistry)
│                  → template.py   (EntityTemplate, Snapshot, TemplateGroup, TemplateRegistry)
├── Behavior       → behavior.py   (Behavior, CallReceipt, BehaviorRegistry, AggregationMode)
│                  → dispatch.py   (on_*/do_* hook pairs, global dispatch registry)
├── Selection      → selector.py   (Selector: pure query predicate)
├── Runtime Ops    → runtime_op.py (RuntimeOp, Query, Predicate, Effect)
└── Context        → ctx.py        (resolve_ctx, using_ctx, ambient ContextVar)
```

### What Core Explicitly Does NOT Define

Core provides vocabulary to implement the following concerns in higher layers, but does
not itself define:

- Requirements, satisfaction, provisioning, scope visibility (VM)
- Traversal, cursor, steps, epochs, ledgers (VM)
- Availability predicates and phased effects on traversable nodes (VM — see
  `vm38.traversable.HasAvailability`, `HasEffects`, `TraversableEffect`)
- Token provisioning and singleton catalog discovery (VM — see
  `vm38.provision.TokenProvisioner`)
- Narrative semantics or syntax (Story)
- Persistence policies, transactions, access control (Service)

---

## Component Design

### Trait Axes (`bases.py`)

The foundation of the entire system. Five orthogonal trait mixins that compose via
standard Python MRO to produce the identity, comparison, serialization, ordering, and
state behavior of every object in the graph:

| Trait            | Concern         | `__eq__`         | Hashable? |
|------------------|-----------------|------------------|-----------|
| `HasIdentity`    | Who am I?       | `eq_by_id` (uid) | No*       |
| `Unstructurable` | What am I?      | `eq_by_value`    | No        |
| `HasContent`     | What do I hold? | `eq_by_content`  | No        |
| `HasOrder`       | When was I?     | (none)           | No        |
| `HasState`       | Runtime scratch | (none)           | No        |

*HasIdentity overrides `__eq__`, so Pydantic sets `__hash__ = None`. Singletons and
Records restore `__hash__` explicitly.

**Availability predicates and executable effects are NOT in this table.** They require
`ResolutionPhase` vocabulary from the VM layer. `HasAvailability`, `HasEffects`, and
`TraversableEffect` live in `vm38.traversable` as VM-layer traits that happen to wrap
core `Predicate` and `Effect` primitives. See `VM_DESIGN.md — Traversal Traits`.

**Key design decisions:**

**MRO determines equality semantics.** The leftmost trait providing `__eq__` wins.
`Entity(Unstructurable, HasIdentity)` compares by value. `class X(HasIdentity, Unstructurable)`
would compare by identity. This is intentional — composition order declares intent.
The `TestTraitComposition` suite pins these MRO contracts explicitly.

**Schema introspection powers identity discovery.** `BaseModelPlus` provides
`_match_fields()` and `_match_methods()` that discover fields and methods annotated
with arbitrary metadata (e.g., `json_schema_extra={"is_identifier": True}`) and the
`@is_identifier` decorator. `get_identifiers()` collects values from both sources into
a unified set. This mechanism avoids hardcoding field names and makes the identity
system extensible without modifying base classes.

**No label sanitization.** v37 silently transformed `"my test node"` into
`"my_test_node"`, making labels ungettable by their original name. v38 stores labels
as-given. Sanitized forms for path-based access (e.g., `scene1.block_1` delegating
to the member with label `"block 1"`) are injected via getters at higher layers.

**`value_hash()` is not an identifier.** It's mutable (recomputed each call), so
including it in `get_identifiers()` would conflate state comparison with identity
comparison. It remains a plain method used by `eq_by_value()` but does not appear in
the identifier set.

**`HasState.locals` is invisible to identity.** The `locals` dict is a mutable
scratchpad for runtime working memory. It is not used for identity, content hashing,
or equality by any trait — it exists purely for runtime state that higher layers
manage. The VM's `HasEffects._sync_locals()` is responsible for writing effect
mutations back to `locals` after they run — this is the node's concern, not
`RuntimeOp`'s.

**Seq ordering is monotonic across runs.** `HasOrder._seq` is seeded from
`time.time_ns()` and auto-increments. This ensures monotonicity within and across
process lifetimes. Not thread-safe for strict uniqueness, but collisions are harmless
since seq is a tie-breaker, not a primary key.

**`evolve()` uses deepcopy.** This is mainly for dict-typed fields (`locals`) and
BaseModel-typed fields. If it becomes a performance bottleneck, field-level cloning
can be substituted, but for the MVP the safety of deepcopy outweighs the cost.


### Entity (`entity.py`)

Entity is intentionally minimal. Its entire purpose is to (a) fix the MRO for `__eq__`
as `eq_by_value` via `Entity(Unstructurable, HasIdentity)`, and (b) inject dispatch
hooks into the construction path via `_ctx`.

**The `_ctx` pattern.** Entity's `__init__` and `structure()` accept an optional `_ctx`
parameter. When provided (or when an ambient ctx exists via `using_ctx`), construction
fires `do_init` / `do_create` dispatch hooks. The underscore prefix prevents collision
with domain fields that might be named `ctx` (e.g., a `CallReceipt` legitimately has
both `ctx=` and `_ctx=` in the same call).

**Ctx is duck-typed.** The `_ctx` parameter accepts `Any`. The dispatch contract is
progressive by layer: core expects `get_registries()` and `get_inline_behaviors()`;
VM extends with graph access, template data, and `get_receipts()`; Story extends further
with actor registries and world-level asset managers. Each layer should define a Protocol
for what it minimally expects. The legacy `core.ctx.Ctx` frozen dataclass is a
placeholder/stub.

**Deferred imports are intentional.** Entity's dispatch/ctx imports are deferred to
break circular dependencies. Entity is a low-level concept; dispatch and ctx are
higher-order mechanisms. Entity just provides launching points for hooks.


### Selector (`selector.py`)

The pure query predicate that decouples matching logic from entity logic. This is the
v38 replacement for legacy `Entity.matches(**criteria)`.

**Direction swap.** v37: `entity.matches(**criteria)` — the entity decides if it matches.
v38: `selector.matches(entity)` — the selector decides. This makes selectors first-class
objects that can be stored, composed, and passed around independently of the entities
they query.

**Callable detection is general.** v37 checked for `has_`/`is_` prefixes explicitly.
v38 checks `callable(attrib_value)` — any callable attribute on the entity is invoked
with the criterion value as sole argument. Convention is still `has_*`/`is_*` but it is
not enforced. This enables patterns like `Selector(caller_kind=Entity).matches(behavior)`
where `Behavior.caller_kind(kind)` is transparently invoked.

**The single-argument callable convention is the system-wide matching contract.**
Methods intended for selector matching — whether on entities, singletons, or tokens —
should accept a single argument that may be a scalar, set, or tuple, handling spreading
internally if needed (see `HasIdentity.has_tags` for the canonical pattern). This
convention applies equally to `Selector.matches()` and to `TokenProvisioner`'s singleton
matching: the same method signature works in both contexts.

**`Any` is a wildcard; `None` is not.** `Selector(label=Any)` skips the label check.
`Selector(label=None)` matches entities where `entity.label == None`. This distinction
matters for optional fields.

**Composition preserves narrowing.** `with_criteria(has_kind=X)` only accepts X if it's
a subclass of the existing `has_kind`. This prevents `find_edges()` from replacing
`Dependency` with `Edge` — only narrowing is allowed. `with_defaults()` never overrides
existing criteria.

**Selectors are not serializable.** Lambda predicates can't be persisted. This is a
known limitation; RuntimeOp integration provides the serializable predicate story.


### Registry (`registry.py`)

The ownership container. Registry owns entities (has them in `members`, manages their
lifecycle); EntityGroup references entities (stores `member_ids`, dereferences through
a registry).

**No duplicate guard.** v38 `add()` silently overwrites on same uid. v37 raised on
duplicate. The guard was removed because the number of add-paths was reduced, making
double-add much less likely. Dispatch hooks provide interception if dedup is needed at
a higher layer.

**`__setitem__` intentionally raises.** `reg[uid] = entity` raises `KeyError`, directing
users to `add()`. This ensures dispatch hooks fire on all additions.

**`bind_registry` is a pointer, not a copy.** Named to emphasize pointer semantics —
Pydantic would occasionally copy during validation, and the name `set_registry` was
misleading. `bind_registry(None)` unbinds (used by `Registry.remove()`).
`bind_registry(registry)` on an already-bound item raises `ValueError` to prevent
accidental dual-ownership.

**`_validate_linkable` uses identity, not equality.** The check is `item.registry is self`,
not `==`. Value equality on registries compares all members recursively, which is
catastrophically expensive and semantically wrong for ownership checks.

**`chain_find_one` was removed.** `chain_find_all` is for filtering into candidate lists.
For single-item lookup, use `next(chain_find_all(...), None)`. The behavioral dispatch
equivalent is the `first_result` aggregator.

**Hierarchical reparenting.** `HierarchicalGroup.add_member()` removes the item from its
old parent first, then adds to the new parent. Cache invalidation via
`_invalidate_parent_attr()` clears the `@cached_property` stored in `__dict__`.

**Back-pointer aliasing is a layering pattern.** `RegistryAware` provides `item.registry`
as the canonical back-pointer to the owning registry. Higher layers alias this to domain-
meaningful names: `GraphItem.graph` aliases `item.registry`; `StoryItem.story` aliases
`item.registry` for story-graph items. This extends upward: `registry.factory` is a
back-pointer from a graph to its owning factory/world, so `item.registry.factory` gives
any item access to its world, aliased as `StoryGraph.world` at the story layer. The
pattern provides ergonomic navigation without special machinery.


### Graph (`graph.py`)

The topology layer. Graph consolidates what v37 split across graph.py, node.py, edge.py,
and subgraph.py into a single file with six classes.

**Core handles shape; VM handles behavior.** Graph provides topology (nodes, edges,
typed queries) and hook injection points. Cursor movement, traversal algorithms,
availability rules, and scope visibility are VM concerns built on top of graph topology.

**predecessor/successor, not source/destination.** The rename from v37 aligns with graph
theory convention and avoids collision with narrative domain concepts where "source" means
something else (e.g., a source text, a source character).

**Dangling edges are intentional.** `predecessor_id` and `successor_id` can be `None`.
Properties return `None` for dangling endpoints. This supports edges as logical constructs
that may not yet have resolved endpoints — critical for provisional graph expansion where
edges are created before their targets exist.

**Three access patterns for edge endpoints:**
1. `edge.predecessor` — property, dereferences through `graph.get()`
2. `edge.set_predecessor(node, _ctx)` — explicit ctx for dispatch hook firing
3. `edge.predecessor_id` — raw UUID for serialization and identity comparison

**`get_authorities()` is the dispatch bootstrapping extension point.** Application-layer
graph subclasses override this to expose domain-specific behavior registries to the VM's
`Frame.get_registries()`. The no-op default on a bare `Graph` is correct — core has no
policy registries to contribute.

This hook exists because dispatch bootstrapping cannot use dispatch to assemble itself:
the authority chain must be discoverable before any behavior fires. A duck-typed method
on the graph is the right primitive — `Frame.get_registries()` checks
`getattr(graph, "get_authorities", None)` and calls it if present, without type-coupling
to any application graph class. `StoryGraph38` overrides it to return `[story_dispatch,
*world.get_authorities()]`. Future `WorldGraph`, `MechanicsGraph`, etc. follow the same
pattern.


### Singleton (`singleton.py`)

Frozen, content-addressed referents that serve as canonical type definitions for Token
instances.

**Singletons enforce uniqueness by label.** Two `Singleton` instances with the same
`label` are the same object — the constructor raises `ValueError` on a collision.
`get_instance(label)` retrieves the canonical instance; `has_instance(label)` tests
without raising.

**`_instances` is a per-class Registry.** Each Singleton subclass maintains its own
`_instances` class-variable registry. Querying instances uses the same
`registry.find_all(selector=s)` mechanics as any other registry — including the callable
attribute convention from `Selector.matches()`. This is how `TokenProvisioner` discovers
matching singleton candidates without any special matching machinery.

**`json_schema_extra={"instance_var": True}` marks per-token state.** Fields with this
annotation belong to individual token instances rather than the shared type definition.
`Token._instance_vars(singleton_cls)` discovers these fields by inspecting
`model_fields`, and they are materialized as real Pydantic fields on the dynamic wrapper
class. The same annotation drives `TokenProvisioner._partition()`, which splits
requirement parameters into type-level selector criteria (used to filter singletons) and
token locals (passed through to the minted token).

**`load_instances_from_yaml()` is the authoring entry point.** World asset managers
call this during initialization to populate singleton registries from authored YAML
catalogs. The YAML file contains only content fields — the singleton class provides the
schema. Classes typically fire `load_defaults()` at module import time to ensure the
catalog is populated before any provisioning can occur.

**`InstanceInheritance` copies fields at creation time only.** `inherit_from` copies all
non-identity, non-private fields from the referent. Subsequent mutations to the parent do
not propagate. This is creation-order dependent — the referent must exist before the
inheritor is created.


### Token (`token.py`)

The bridge between immutable singleton definitions and mutable graph node instances.
Token sits at the intersection of identity, state, and metaprogramming.

**The problem Token solves.** You need "short sword" as an immutable type definition
(damage, description, base stats) and "Glamdring" as a mutable instance in a graph
(current sharpness, current owner, position). Token wraps the singleton, delegates
immutable attributes, and provides mutable instance-var fields.

**`Token[X]` is a class factory, not standard generics.** `__class_getitem__` creates a
new Pydantic model class at subscription time by discovering `instance_var` fields on the
singleton (`json_schema_extra={"instance_var": True}`) and materializing them as real
Pydantic fields on the dynamic wrapper class. Results are cached by `(Token, X)` so
repeated subscriptions return the same class.

**`token_from` vs `label`.** v37 overloaded `label` to mean both "my name" and "the
singleton I reference." v38 separates these: `token_from` references the singleton,
`label` is the Token's own name as a Node. `Token[SwordType](token_from="short sword",
label="Glamdring")` makes the distinction explicit.

**Delegation rules:**
- Read: check own fields (including instance_vars) first, then delegate to
  `reference_singleton` via `__getattr__`
- Write: instance_var fields are mutable on the Token directly (they're real Pydantic
  fields). Non-instance fields route through the frozen singleton and raise on write.
- Methods: rebound via `MethodType` so `self` in the singleton method refers to the
  Token, not the singleton. This means `def greet(self): return f"I am {self.name}"`
  uses the Token's `name` instance_var, not the singleton's.

**`has_kind` delegates to wrapped type.** `token.has_kind(SwordType)` returns True,
making Tokens transparently findable by their wrapped singleton type via Selector
queries. This is the mechanism that lets `graph.find_nodes(Selector(has_kind=SwordType))`
find tokens.

**`TokenFactory` was removed from core.** The provisioner adapter that wrapped
`Token[X](token_from=label)` for builder-like flows has been replaced by
`vm38.provision.TokenProvisioner`, which integrates singleton catalog discovery into the
standard `gather_offers` pipeline. Token itself has no provisioning responsibility — it
only knows how to create wrapper classes and materialize instances. See
`VM_DESIGN.md — Token Provisioning`.


### RuntimeOp (`runtime_op.py`)

Serializable, sandboxed expression wrappers for authored runtime logic.

**The runtime-op family is intentionally small.** `RuntimeOp` stores an expression
string and provides `eval`/`exec` helpers sandboxed to `safe_builtins`. `Predicate` is
read-only boolean evaluation (guards, availability checks). `Effect` is write-oriented
namespace mutation. `Query` is read-only value computation.

**`rand` is the only injected global at this layer.** `RuntimeOp._eval_expr` and
`_exec_expr` accept `extra_globals: dict | None` as a seam for higher-layer injection.
Public instance methods (`eval`, `exec`, `satisfied_by`, `apply`) expose only
`rand: Random | None`, which is the lowest-layer injectable. Story-layer code passes
additional helpers (e.g., `bind_effect_helpers`) through `extra_globals` without
subclassing.

**RuntimeOp knows nothing about nodes.** It operates purely on namespace dicts. Writing
effect mutations back to a node's `locals` is the responsibility of `HasEffects._sync_locals()`
in the VM layer, not of `Effect.apply()`. This keeps RuntimeOp portable and testable
without any graph context.

**Effects and predicates are not phased.** `ResolutionPhase` is VM vocabulary.
`RuntimeOp` has no trigger timing — it is simply a serializable expression. Phase
annotation (`TraversableEffect.trigger_phase`) lives on the VM-layer wrapper class in
`vm38.traversable`, following the same wrapper-inheritance pattern as `TraversableEdge`
wrapping `Edge`.


### Record & OrderedRegistry (`record.py`)

Immutable, content-addressed, ordered facts and their append-only container.

**Record has three identity layers:** uid (Entity), content (HasContent), seq (HasOrder).
Records are identified primarily by content and ordered by seq.

**OrderedRegistry is append-only.** `add()` is permitted; `remove()` raises. This
enforces the event-sourcing invariant that facts, once recorded, are never retracted
(they may be superseded by later facts, but the history is preserved).

**Slice semantics are sort-key-generic.** `get_slice(after=marker)` works against any
`sort_key` — seq for Records, but potentially domain-specific keys for other
OrderedRegistry users. The registry does not hardcode seq as the ordering mechanism.


### Template (`template.py`)

Prototypes for node creation — authored once, materialized many times.

**Template is a payload wrapper, not a prototype.** The template itself stores creation
metadata and a `payload: Entity` (the prototype). Materialization clones the payload
and applies overrides. This separates "what kind of thing to create" from "how to create it."

**TemplateRegistry is the world's script.** The full ordered set of templates available
during a story session. Provisioners receive it in scoped chunks (closest template scope
first, global scope last) so inner-scope templates shadow outer-scope templates when
multiple match a requirement.

**Snapshot is a degenerate template.** It reuses template machinery for persistence:
"recreate this exact entity" with `preserve_uid=True`. It's not part of the authoring
loop — it exists because the infrastructure for "store a prototype, materialize a copy"
is already there.


### Behavior & Dispatch (`behavior.py`, `dispatch.py`)

The hook system that makes construction, indexing, and graph mutations extensible without
modifying the base classes.

**Dispatch is a mechanism in Core; which registries are active is context selection (VM).**
Core provides the chaining and execution machinery. The VM (and higher layers) determine
which BehaviorRegistries participate in a given dispatch by populating `ctx.get_registries()`
and `ctx.get_inline_behaviors()`.

**Ctx-aware chain assembly.** `chain_execute` pulls registries from three sources:
1. Explicitly passed registries (includes the global `dispatch` singleton)
2. `ctx.get_registries()` — layer-specific registries from the runtime context
3. `ctx.get_inline_behaviors()` — ad-hoc callables normalized into a temporary LOCAL
   registry

Deduplication is by `id()`, preserving insertion order. Behaviors across all registries
are sorted by `sort_key = (dispatch_layer, priority, wants_exact_kind, seq)`.

**Three-tier dispatch layering:**
- GLOBAL — registered at module level via `on_init`, `on_create`, etc.
- APPLICATION — carried by the runtime context's registries
- LOCAL — inline behaviors, per-operation overrides

**Seven hook pairs:**

| Hook | Trigger | Aggregation |
|------|---------|-------------|
| `on_init` / `do_init` | Entity construction | `gather_results` |
| `on_create` / `do_create` | Entity structuring | `merge_results` |
| `on_add_item` / `do_add_item` | Registry addition | `last_result` |
| `on_get_item` / `do_get_item` | Registry retrieval | `last_result` |
| `on_remove_item` / `do_remove_item` | Registry removal | `gather_results` |
| `on_link` / `do_link` | Graph structural link | `gather_results` |
| `on_unlink` / `do_unlink` | Graph structural unlink | `gather_results` |

**`AggregationMode` is serializable dispatch vocabulary.** The enum names the fold
strategies that `do_*` functions apply to receipt lists. It lives in `behavior.py`
alongside `CallReceipt` because the intent is for `_make_do_hook(task, agg_mode)` in
the VM's dispatch factory to read the mode and wire the correct fold — eliminating
the near-identical boilerplate currently copy-pasted across `vm38/dispatch.py`'s
`do_*` function bodies. The `CallReceipt.aggregate(mode, *receipts)` adapter is the
bridge. See `VM_DESIGN.md — Dispatch Hook Factory`.

**`caller_kind` filtering.** Behaviors can declare `wants_caller_kind` to restrict which
entity types trigger them. The Selector invokes `behavior.caller_kind(type(caller))`
transparently — the Selector doesn't know anything about Behavior internals.


---

## Cross-Cutting Design Decisions

### Identity Model

Three distinct identity comparisons serve different purposes:

| Method | Compared By | Use Case |
|--------|------------|----------|
| `eq_by_id()` | uid + class | "Same entity across time" |
| `eq_by_value()` | all serializable fields | "Same content right now" |
| `eq_by_content()` | `get_hashable_content()` | "Same semantic payload" |

Entity's `__eq__` is `eq_by_value` (Unstructurable wins MRO). Singleton's `__eq__` is
effectively `eq_by_id` via `id_hash` (class + label). Record's `__eq__` is `eq_by_content`
(HasContent wins MRO).

### Serialization Strategy

Two serialization loops serve different audiences:

| Operation | Audience | Fidelity | Idempotent? |
|-----------|----------|----------|-------------|
| `unstructure()` / `structure()` | Persistence engine | Complete | Yes |
| `decompile()` / `compile()` | Human authors | Content-only | Yes (after first cycle) |

`unstructure()` preserves everything — uid, seq, caches, internal state. The dict
contains a `kind` key holding the live class object (not a string) for polymorphic
reconstruction.

`decompile()` strips framework noise (uid, seq) and removes redundant defaults
(e.g., `kind=Entity` when Entity is the default). The result is human-readable and
version-control-friendly.

### The `kind` Vocabulary

v37 used `obj_cls`. v38 uses `kind` throughout — in unstructured data dicts, in Selector
criteria (`has_kind`), in creation helpers (`add_node(kind=X)`), and in template matching
(`has_payload_kind`). The rename clarifies that this is a type discriminator, not a
Python class reference (even though at the core level it IS a class reference — higher
layers may use string-based kind resolution through the service layer).

### Wrapper Inheritance as a Layering Pattern

Domain concepts are introduced at the layer where they belong, wrapping core primitives
rather than modifying them. The chain is consistent throughout:

| Layer | Wraps | Adds |
|-------|-------|------|
| `core38.Edge` | — | topology endpoints |
| `vm38.TraversableEdge` | `Edge` | `trigger_phase`, `entry_phase`, `return_phase` |
| `story38.Choice` | `TraversableEdge` | narrative presentation metadata |
| `core38.Effect` | — | serializable expression |
| `vm38.TraversableEffect` | `Effect` | `trigger_phase` for pipeline timing |
| `story38.StoryEffect` | `TraversableEffect` | narrative context helpers |

This pattern keeps each layer's additions local, prevents upward imports, and gives
authors a consistent inheritance ladder to extend.

---

## v37 → v38 Key Migration Summary

| Aspect | v37 | v38 | Rationale |
|--------|-----|-----|-----------|
| Edge endpoints | `source` / `destination` | `predecessor` / `successor` | Graph theory convention; avoid domain collision |
| Matching direction | `entity.matches(**kw)` | `Selector(**kw).matches(entity)` | Selectors are first-class, composable |
| Find API | `find_all(**criteria)` | `find_all(selector=S)` | Typed, storable, composable queries |
| Kind field | `obj_cls` | `kind` | Clearer semantics |
| Graph storage | `graph.data` | `registry.members` | Graph IS a Registry now |
| Registry awareness | Implicit | `RegistryAware` mixin | Explicit binding with rebind protection |
| Template payload | Flattened fields | Separate `payload: Entity` | Clean separation of wrapper and content |
| Ordered slicing | Seq-specific markers | Sort-key-generic `get_slice` | Composable with arbitrary orderings |
| Token reference | `label` (overloaded) | `token_from` (separate) | Distinct identity vs. reference |
| Token provisioner | `TokenFactory` in core | `TokenProvisioner` in vm38 | Provisioning is context-aware; core is timeless |
| Availability/Effects | `HasAvailability`, `HasEffects` in core | `HasAvailability`, `HasEffects`, `TraversableEffect` in vm38 | Phase vocabulary belongs at VM layer |
| Behavior API | `add_behavior` / `dispatch` | `register` / `execute_all` | Clearer verbs; ctx-aware chaining |
| Dispatch layers | `HandlerPriority` / `HandlerLayer` | `Priority` / `DispatchLayer` | Simplified naming |
| Duplicate guard | Registry.add raises | Silent overwrite | Fewer add-paths reduce double-add risk |
| Label sanitization | Silent transformation | Stored as-given | Avoids invisible renaming confusion |
| `Selectable` mixin | Inverse matching | Removed | Selection is Selector's job; templates handle scoping |


---

## Architectural Principles

### Composition Over Inheritance

The trait system (`bases.py`) is the purest expression of this. `HasIdentity`,
`Unstructurable`, `HasContent`, `HasOrder`, and `HasState` are independent axes that
compose via MRO. Entity, Singleton, Record, and Token are specific compositions that fix
the MRO for their domain's equality and identity semantics.

### Mechanism vs. Policy

Core provides mechanisms (dispatch chaining, selector matching, sort-key-generic slicing).
Higher layers provide policy (which registries are active, what scope rules apply, how
bookmarks map to key values). This separation is why OrderedRegistry doesn't have
bookmarks and why Graph doesn't have traversal algorithms.

`Graph.get_authorities()` is the dispatch bootstrapping extension point.  Application-layer
graph subclasses override it to expose their behavior registries (story, world, mechanics)
to the VM's ``PhaseCtx.get_authorities()`` without any type coupling between core and higher
layers.  The no-op default on bare ``Graph`` is correct — core itself has no policy
registries to contribute.  This hook exists precisely *because* you cannot use dispatch
to assemble the dispatch chain: authorities must be discoverable before any behavior fires.

### Hook Points, Not Hook Logic

Every `do_*` function is 4-6 lines. The base classes provide hook injection points
(`_ctx` parameter on constructors, `_do_link`/`_do_unlink` bridge methods) but the actual
hook logic lives in registered behaviors owned by higher layers. Core never decides what
a hook *does* — it only ensures the hook *fires* at the right time.

### Progressive Protocols

Rather than a monolithic context type, `_ctx` is duck-typed with progressive expectations
by layer. Core dispatch expects `get_authorities()` and `get_inline_behaviors()`. VM
extends with graph access, namespace caching, and seeded randomness. Story extends further
with actor registries and world-level asset managers. Each layer defines a Protocol for
what it minimally expects; the runtime context satisfies all layers it passes through.

### Timelessness

Nothing in core depends on time, sequence position, or narrative state. Entities have
`seq` for ordering, but the ordering is structural, not temporal. Temporal semantics
(epochs, steps, phases, cursors) are entirely VM concerns. This is what makes core
testable in isolation — every test can create fresh objects without establishing runtime
context.

---

*Companion design notes for `tangl.vm38`, `tangl.story38`, and `tangl.service` follow
the same pattern of capturing architectural intent, component design rationale, and
cross-cutting decisions. See `VM_DESIGN.md` for the VM layer.*
