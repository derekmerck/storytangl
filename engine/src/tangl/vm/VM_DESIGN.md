# tangl.vm — Design Notes

> Architectural intent, design decisions, and rationale for the canonical vm package
> of the StoryTangl narrative engine (v3.8 framework).
> This document describes the current v3.8 framework. The source packages are
> `tangl.core`, `tangl.vm`, and `tangl.story` (no version suffix).

---

## Position in the Architecture

VM is the execution layer. It adds temporal structure, context-dependent evaluation,
and traversal semantics on top of the timeless primitives core provides. The dependency
direction is strictly upward: vm imports from core, story imports from vm.

```
Service  → Lifecycle management, persistence, API
Story    → Domain semantics, narrative concepts
VM       → Temporal evolution, context-dependent evaluation   ← this document
Core     → Timeless primitives and mechanisms
```

**VM's defining characteristic is the phase pipeline.** Where core provides static
graph topology, vm provides the machinery that moves a cursor through that topology,
fires behavior at each step, and produces a deterministic, replayable output stream.
VM knows about time in the sense of *causal ordering* — phases have a defined sequence,
steps accumulate, the cursor has a history — but it knows nothing about wall-clock time
or narrative meaning.

### What VM Explicitly Does NOT Define

- Narrative concepts: scenes, characters, inventory, dialogue (Story)
- Domain-specific singleton types: weapons, clothing, animals (Story/World)
- Persistence backends, access control, session management (Service)
- Content rendering: text generation, image selection, audio synthesis (Story/Service)

VM provides the *contract* for how these things plug in, not their implementation.

### VM Module Map

```
tangl.vm
├── Resolution     → resolution_phase.py  (ResolutionPhase enum, causal ordering)
├── Factory        → factory.py           (TraversableGraph, TraversableGraphFactory)
├── Traversal      → traversable.py       (TraversableNode, TraversableEdge, AnonymousEdge)
│                  → traversal.py         (history queries: visit_count, call_depth, etc.)
├── Runtime        → runtime/frame.py     (Frame: one resolve_choice driver)
│                  → runtime/ledger.py    (Ledger: state across player actions)
│                  → runtime/causality.py (CausalityMode: clean/soft_dirty/hard_dirty)
│                  → ctx.py              (VmPhaseCtx protocol)
├── Provisioning   → provision/           (Requirement, Dependency, Resolver, Provisioners)
├── Dispatch       → dispatch.py          (on_*/do_* hook pairs for the phase pipeline)
│                  → system_handlers.py   (SYSTEM-layer behavior registrations)
└── Replay         → replay/              (Event, Patch, StepRecord, DiffReplayEngine)
```

---

## Component Design

### TraversableGraph / TraversableGraphFactory (`factory.py`)

VM adds one narrow factory layer above core eager topology expansion.

**`TraversableGraph`** is a `core.Graph` subtype carrying one extra field:
`initial_cursor_id`. This is traversal metadata derived from graph shape, not
session state. `Ledger` still owns the live cursor and cursor history.

**`TraversableGraphFactory`** subclasses `core.GraphFactory` and adds only two
behaviors after core materialization:

- resolve the default traversal entry via `get_entry_cursor()`
- validate traversal contracts with `assert_traversal_contracts()`

It also exposes `materialize_seed_graph(...)`, the VM-level public seam for
lazy seed-graph creation from an already-resolved template subset. This keeps
selected-path seeding in VM without introducing a second runtime factory type.

This keeps VM's authority surface small. Planning, replay, and causality stay
runtime behavior over a traversable graph; they are not separate factory
classes.

### ResolutionPhase (`resolution_phase.py`)

The canonical enumeration of pipeline stages, in causal order:

```
INIT → VALIDATE → PLANNING → PREREQS → UPDATE → JOURNAL → FINALIZE → POSTREQS
```

**Phase ordering is causal, not arbitrary.** Each phase has a defined semantic role and
fires in a fixed sequence with no skipping (except when an early phase produces a
redirect, in which case `follow_edge` loops from the top on the new target):

| Phase | Role | Aggregation |
|-------|------|-------------|
| VALIDATE | Is this movement legal? Gate on all-true. | all_true |
| PLANNING | Provision this node's frontier dependencies. | gather |
| PREREQS | Auto-redirect? Container descent? | first_result → edge |
| UPDATE | Mutate state for arrival. | gather |
| JOURNAL | Emit content fragments. | merge (all contributions) |
| FINALIZE | Commit step record, emit patch. | last_result → patch |
| POSTREQS | Continuation redirect? | first_result → edge |

**`trigger_phase` on effects and edges encodes causal intent.** `TraversableEffect`
carries a `trigger_phase` field (default `UPDATE`) so a single `effects` list covers both
arrival effects and departure effects without needing separate `entry_effects` /
`final_effects` fields. The system handler for UPDATE fires effects tagged UPDATE; the
system handler for FINALIZE fires effects tagged FINALIZE. Same mechanism, declared
intent at the data level.

**Phase is VM vocabulary; core knows nothing about it.** `ResolutionPhase` must not be
imported into `core`. This is why `HasAvailability`, `HasEffects`, and
`TraversableEffect` live in `vm.traversable` rather than `core.bases`, even though
they wrap core primitives (`Predicate`, `Effect`). See *Traversal Traits* below.

**Atomic pipeline, no split around input.** FINALIZE and POSTREQS run immediately after
JOURNAL — the player's next choice is recorded at the start of the *next*
`resolve_choice` call, not at the end of the current pipeline. This keeps the pipeline
atomic and simplifies replay: every step is a complete VALIDATE→POSTREQS sequence.


### Traversal Contracts (`traversable.py`)

Adds the traversal contract to core's topology: which nodes the cursor can visit, how
movement works, and what container structure means for the pipeline.

#### TraversableNode

`TraversableNode` composes three vm-layer traits — `HasAvailability`, `HasEffects`,
`HasState` — plus core's `HierarchicalNode`:

**Leaf / container duality.** One class covers both cases. Container behavior activates
when `source_id` is set — no separate `TraversableLeaf` / `TraversableContainer`. When
the cursor arrives at a container, the system-level PREREQS handler detects `is_container`
and returns an `AnonymousEdge` to the source. The frame follows that edge normally, which
may itself trigger further descent. Nested containers descend recursively through normal
pipeline execution with no special mechanism.

**UUID-referenced source/sink.** Stored as `source_id` / `sink_id`, dereferenced through
the graph. Unlike the legacy `TraversableSubgraph` which created hidden `__SOURCE` /
`__SINK` nodes, v38 designates existing members as source and sink. Edges into the
container target the container itself; edges out of the container originate from the sink.

**LCA-based movement.** Every cursor movement is `goto(target)` whose context
implications are determined by the lowest common ancestor (LCA) of source and target in
the hierarchy. The ancestor chain at any cursor position defines the complete resource
scope. `decompose_move(source, target)` yields `(exit_path, enter_path, pivot)` for
teardown/setup hooks. The namespace is always recomputed from `cursor.ancestors` rather
than maintained as a mutable stack — correctness over cleverness for MVP.

#### TraversableEdge

Wraps core's `Edge` with phase-control fields:

- `entry_phase` — which pipeline phase to start at when arriving via this edge. Return
  edges set `entry_phase=UPDATE` to skip VALIDATE/PLANNING on already-processed nodes.
- `return_phase` — marks this edge as a *call*. The frame pushes it onto the return
  stack before following. When the callee pipeline reaches a terminal, the frame pops
  the stack and follows `get_return_edge()` back to the predecessor at `return_phase`.

**Call/return semantics are edge properties, not graph structure.** One edge UUID in the
graph serves as the call bookmark — there is no separate return-edge data structure.
`get_return_edge()` constructs an `AnonymousEdge` pointing back to the predecessor.

#### AnonymousEdge

Lightweight dataclass for transient traversal operations (prereq redirects, container
descent, return edges). No graph membership, no UUID, GC-friendly. `entry_phase` is
supported; `return_phase` is not — only persistent `TraversableEdge` instances with
stable UUIDs serve as call bookmarks.

**Same interface as TraversableEdge for Frame.** `frame.follow_edge` accepts
`AnyTraversableEdge = Union[AnonymousEdge, TraversableEdge]` so the pipeline machinery
never branches on edge type.

#### Traversal Traits (`HasAvailability`, `HasEffects`, `TraversableEffect`)

These live in `vm.traversable` rather than `core.bases` because they depend on
`ResolutionPhase`, which is VM vocabulary. The migration from core is deliberate:

**`HasAvailability`** — list of `core.Predicate` instances evaluated against a
namespace. `available(ns, ctx, rand)` tests own conditions. `available_for(other, ctx)`
tests against another entity's namespace, used by resolvers evaluating whether a
candidate satisfies a requirement and by `on_link` / `on_unlink` hooks on dependency
edges.

**`HasEffects`** — list of `TraversableEffect` instances partitioned and applied by
phase. `apply_effects(phase, ctx)` applies matching effects to own namespace.
`apply_effects_to(other, phase, ctx)` applies to another entity's namespace for
dependency link/unlink hooks. `_sync_locals(ns)` writes changed namespace values back
to `self.locals` — this is a node concern, not a `RuntimeOp` concern: `RuntimeOp`
knows only about the namespace dict.

**`TraversableEffect`** — wraps `core.Effect` with a `trigger_phase` field (default
`UPDATE`). The wrapper pattern follows the established ladder:
`Effect → TraversableEffect → StoryEffect` at successive layers. A single `effects`
list with phase annotation replaces v37's separate `entry_effects` / `final_effects`
fields.

**Duck-typed system handlers, not required inheritance.** System handlers check
`hasattr(caller, "apply_effects")` rather than `isinstance(caller, HasEffects)`. This
keeps `TraversableNode` free to compose traits without being forced into a specific MRO,
and makes traits accessible to story-layer node types that may have their own base
classes.


### Dispatch Hook Pairs (`dispatch.py`)

The phase pipeline exposed as `on_*` / `do_*` decorator and invocation pairs. Each pair
covers one pipeline stage plus the two cross-cutting helpers for namespace assembly and
requirement resolution.

**Pipeline hooks:**

| Decorator | Invocation | Phase |
|-----------|------------|-------|
| `on_validate` | `do_validate` | VALIDATE |
| `on_provision` | `do_provision` | PLANNING |
| `on_prereqs` | `do_prereqs` | PREREQS |
| `on_update` | `do_update` | UPDATE |
| `on_journal` | `do_journal` | JOURNAL |
| `on_finalize` | `do_finalize` | FINALIZE |
| `on_postreqs` | `do_postreqs` | POSTREQS |

**Cross-cutting helpers:**

| Decorator | Invocation | Purpose |
|-----------|------------|---------|
| `on_gather_ns` | `do_gather_ns` | Namespace assembly from caller/ancestor `get_ns()` + immediate dispatch |
| `on_resolve` | `do_resolve` | Offer override/filter during provisioning |

**`do_resolve` is a filter hook, not an addition hook.** Handlers return `None` to leave
existing offers unchanged, or `Iterable[ProvisionOffer]` to replace them. Provisioners
(Find, Template, Token) contribute offers *before* `do_resolve` fires in
`Resolver.gather_offers`. `do_resolve` is for late filtering, scoring adjustments, and
story-layer offer manipulation — not for generating new offer sources.

**Search-space discovery is authority-based, not dispatch-based.** `PhaseCtx`
delegates template, token, and media lookup directly to `graph.factory` /
world authority methods. The VM no longer exposes dedicated discovery hook
families for those search spaces, which keeps story/media vocabulary out of
the VM dispatch surface.

**Aggregation modes match phase semantics.** PREREQS and POSTREQS use `first_result`
(first redirect wins, subsequent handlers skipped). VALIDATE uses `all_true` (all
handlers must pass). JOURNAL uses merge (all handler contributions combined). UPDATE and
PLANNING use gather (all results collected). These are not arbitrary choices — they
follow from what each phase does.

**`AggregationMode` will drive a hook factory.** Each `do_*` function currently
hardcodes its own fold call. The intent is to replace this copy-paste with a table of
`(task_name, agg_mode)` pairs driving a single `_make_do_hook(task, agg_mode)` factory.
`CallReceipt.aggregate(mode, *receipts)` is the bridge; `AggregationMode` in
`core.behavior` is the vocabulary. This refactor reduces ~15 near-identical function
bodies to a declaration table. It is deferred past MVP but the vocabulary is already in
place.


### Phase Context (`runtime/frame.py` — `PhaseCtx`)

The dispatch context for one `follow_edge` invocation. Created fresh at each cursor hop;
discarded when the hop completes.

**Registry assembly stays explicit at call time.** The `do_*` helpers dispatch through
`vm_dispatch`; `PhaseCtx.get_authorities()` contributes only *additional* registries.
If the graph exposes `get_authorities()`, those registries are appended in declaration
order. Frame and Ledger may also inject populated local registries explicitly for one
call path via `PhaseCtx.local_authorities`. This keeps story/world registries automatic
while preserving narrow local override seams without ambient per-instance discovery.

**Template scope discovery is factory-authority-first.** `PhaseCtx.get_template_scope_groups()`
delegates to the bound graph factory when it exposes `get_template_scope_groups(...)`
and otherwise falls back to the factory's template registry. Token catalogs and media
inventories use the same authority pattern through `get_token_catalogs(...)` and
`get_media_inventories(...)`.

**Namespace is cached per-node per-context.** `get_ns(node)` delegates to
`do_gather_ns` on cache miss, caches the result by node UID. `do_gather_ns` uses a
two-phase model: (1) caller + ancestors contribute via `get_ns()`, (2) immediate-caller
dispatch contributors add runtime/context layers. Different nodes during the same
pipeline pass (cursor, frontier nodes during PLANNING, ancestors during condition
evaluation) each get their own cached namespace. The cache dies with the PhaseCtx, so
UPDATE mutations are visible in the *next* pipeline pass via a fresh PhaseCtx — they do
not retroactively affect cached namespaces within the current pass.

**Child runtime contexts come from `PhaseCtx.derive()`.** Provisioning and
post-materialization validation sometimes need a `PhaseCtx` scoped to a different cursor
without losing tracing, RNG, dirty callbacks, or local authorities. The supported path is
`ctx.derive(cursor_id=..., graph=..., meta_overrides=...)`, which carries forward shared
runtime identity/config state while intentionally resetting per-pass caches and nested
dispatch result buffers. Manual field-plucking is not part of the contract.

**Namespace handlers must not call `get_ns` for the node they're building.** That
would cause infinite recursion. Use handler priority ordering instead — a handler that
needs a partial namespace can register at a later priority and rely on earlier handlers
having already contributed their portions.

**Seeded randomness for deterministic replay.** The Frame seeds its `_random` from
`hashing_func(graph.value_hash(), cursor.uid, step_base)` in `__post_init__`. The seed
is deterministic from graph state + position + step, so replaying the same sequence of
choices produces the same random outcomes. `ctx.get_random()` exposes the shared RNG;
`rand` is threaded through `RuntimeOp.eval/exec` and `HasAvailability.available` as
`rand: Random | None`. Passing `rand=None` preserves backward-compatible behavior
(expression has no `rand` available).


### Frame (`runtime/frame.py`)

Drives one `resolve_choice` call: a sequence of `follow_edge` steps through the graph
until the pipeline produces no redirect or the return stack is exhausted.

**Frames are ephemeral.** Created by Ledger for each player action, consume edges,
produce output into `output_stream`, then discarded. Their output is deterministically
reproducible from graph state and the chosen edge.

**`follow_edge` is the unit of work.** Each call: (1) prepares the hop and validates
the incoming edge, (2) advances cursor and builds a fresh PhaseCtx, (3) runs the full
phase pipeline VALIDATE→POSTREQS, and (4) returns any redirect edge or `None`.
`resolve_choice` remains an explicit loop over returned edges and return-stack unwind;
the VM keeps this bus concrete rather than hiding it behind a generic phase-spec table
because redirect capture, tracing, and return-edge resumption are part of the runtime
contract.

**`output_stream` is an `OrderedRegistry`.** Fragments (JOURNAL) and patches (FINALIZE)
are appended to a shared `OrderedRegistry`. The registry's append-only, seq-ordered
semantics ensure the output is total-ordered and reproducible.

**Step counter is absolute.** `step_base` carries the ledger's `cursor_steps` at frame
creation. `ctx.step = step_base + frame.cursor_steps` gives the absolute step number
at any point, which appears in records and is used for replay slicing.

**`cursor_trace` and `redirect_trace` for diagnostics.** The trace lists accumulate
during `resolve_choice` for debugging infinite redirects and softlock analysis. They are
not persisted — diagnostic instrumentation only.


### Ledger (`runtime/ledger.py`)

Persistent state across player actions. Where Frame is ephemeral, Ledger is durable.

**Ledger owns the cursor, return stack, and step count.** Frame borrows these for the
duration of a `resolve_choice` call and returns them (mutated) when done. Ledger is the
authoritative source of "where are we."

**Ledger creates Frames, not the other way around.** `ledger.resolve_choice(edge)` builds
a Frame from current ledger state, runs it, validates the resulting return stack, and
writes back cursor, trace, and step counters through small sync helpers. Callers never
construct Frames directly.

**Event sourcing via OrderedRegistry.** Ledger's output accumulates in a single
`OrderedRegistry` across all frames. Replay slices this registry by step range and
re-executes fragments to reconstruct any point-in-time state.


### Provisioning (`provision/`)

The frontier constraint satisfaction system. Provisioning answers: "what entities does
the cursor need in its scope, and how do we find or create them?"

#### Requirement and Dependency

`Requirement` is a `Selector` with provision metadata. Because it inherits Selector, a
Requirement IS a query — `requirement.satisfied_by(entity)` is `selector.matches(entity)`.
This means the same callable-attribute convention that powers `Selector.matches` also
powers requirement satisfaction checking, and `requirement.filter(entities)` returns all
entities satisfying the requirement out of an iterable pool.

`Dependency` is a graph edge that records the resolved provider. Before resolution,
`dependency.provider_id` is `None`. After resolution, it points to the winning entity's
UID. Dependency edges participate in the graph topology — they are real `Edge` subclasses
stored in the graph, not ephemeral data structures.

#### Provisioners

Provisioners are stateless or lightly-stateful objects that generate `ProvisionOffer`
instances for a given requirement. Three symmetrical provisioner types cover the three
fundamental resolution strategies:

| Provisioner | Source | Policy | Distance |
|-------------|--------|--------|----------|
| `FindProvisioner` | entity_groups from graph | EXISTING | location distance |
| `TemplateProvisioner` | `ctx.get_template_scope_groups()` | CREATE | scope distance |
| `TokenProvisioner` | `ctx.get_token_catalogs(requirement=...)` | CREATE | 0 |

**Provisioners are not registered — they are called.** `Resolver.gather_offers` calls
each provisioner directly before `do_resolve` fires. This is intentional: provisioners
are offer *sources*, not offer *filters*. The hook (`do_resolve`) is for late
manipulation of the already-assembled offer list, not for contributing new sources.

**Distance encodes scope proximity.** `FindProvisioner(values=entity_group, distance=i)`
encodes how far from the cursor this group of entities lives. Distance 0 is the cursor
itself; distance 1 is the immediate parent scope; higher distances are further ancestors
or global scope. `ProvisionOffer.priority` is adjusted by distance so closer providers
naturally rank higher in offer selection.

#### TokenProvisioner

`TokenProvisioner` integrates singleton catalog discovery into the standard offer
pipeline. It is a thin source/filter/offer loop:

```python
# Resolver-side discovery
catalogs = ctx.get_token_catalogs(requirement=requirement)
offers = TokenProvisioner(catalogs=catalogs).get_dependency_offers(requirement)
```

Each catalog wraps one singleton type (`TokenCatalog.wst`) and delegates matching to the
singleton `_instances` registry (`catalog.find_all(selector=...)`). For each match,
TokenProvisioner yields a `CREATE | TOKEN` offer whose callback mints
`Token[wst](token_from=instance.label, ...)`.

Token creation is always treated as synthetic provisioning. Existing token entities on
the graph are still discovered by `FindProvisioner` like any other entity. Update/clone
composition excludes TOKEN offers by policy.

#### Offer Selection

`Resolver.gather_offers` assembles all offers from all provisioners plus `do_resolve`
filtering, then applies `_allowed(offer)` filtering against `requirement.provision_policy`.
The first (highest-priority) allowed offer wins and its `callback()` is invoked to
materialize the provider.

`ProvisionPolicy` flags encode the selection contract: `EXISTING` (find an existing
entity), `CREATE` (clone/mint a new one), `STUB` (debug/preview fallback, only when
stubs are allowed), `TOKEN` (specifically a singleton token). Requirements can restrict
which policies are acceptable.

**Selected-path runtime materialization.** When a CREATE or CLONE offer is
accepted for a traversable requirement, resolver may need to build missing
structural prefix segments before binding the final provider. The supported
contract is selected-path-safe rather than a general recursive planning system:

- missing intermediate segments are materialized, attached, post-materialized,
  and validated one by one before the final provider is bound
- newly created providers are post-materialized and validated before dependency
  binding completes
- preview checks the same selected-path contract through story-provided preview
  hooks, but remains pure and must not mutate graph state

Story owns the domain-specific postconditions for authored topology and
container-entry behavior; VM owns the offer-selection, chain execution, and
validation order that makes those postconditions hold at commit time.

#### Causality Modes (Debug/Preview Traversal)

Runtime context carries a monotonic causality mode:

- `CLEAN` — normal authored traversal assumptions hold.
- `SOFT_DIRTY` — debug inspection/mutation occurred, but authored availability still runs.
- `HARD_DIRTY` — causal chain is broken; availability becomes permissive and STUB linking
  is allowed automatically.

`SOFT_DIRTY` is set by explicit debug actions (`jump`, `inspect`, `check`, `apply`).
`HARD_DIRTY` is set on first accepted `STUB` dependency link. Transitions are append-only
audit records in the ledger output stream via `CausalityTransitionRecord`.


### Authority Chain and Back-Pointer Aliasing

The authority chain is the mechanism by which world-specific registries participate in
vm-level dispatch without any direct dependency between vm and world.

**The full pointer chain:**
```
item.registry          ← RegistryAware back-pointer (core)
item.registry.factory  ← registry's owning factory/world
item.graph             ← GraphItem alias for item.registry
item.graph.factory     ← same as registry.factory, via graph
item.story             ← StoryItem alias for item.registry
item.story.world       ← StoryGraph.world (= story.factory)
```

All of these are the same underlying pointer walking through aliases defined at each
layer. Higher-layer code uses the ergonomic alias; lower-layer code uses the canonical
name. Nothing new at the vm layer — vm just consumes `ctx.graph` and
`graph.get_authorities()`.

**`PhaseCtx.get_authorities()` is the authority aggregation point.** It calls
`graph.get_authorities()` for environment-level registries and appends any explicit
local registries supplied by the current Frame or Ledger. Authority dispatch is
therefore automatic for graph-owned registries, while local experimental or audit
registries remain opt-in per call path.

**Four world manager types, one authority pattern.** A complete world provides:

| Manager | Authority hook | VM consumer |
|---------|---------------|-------------|
| `DomainManager` | registers handlers directly | fires through normal dispatch |
| World/factory template providers | `World.get_template_scope_groups(...)` | Template search-space discovery |
| World asset/domain providers | `World.get_token_catalogs(...)` | Token catalog discovery |
| World/media providers | `World.get_media_inventories(...)` | Media inventory discovery |

Template scope groups, token catalogs, and media inventories now come from the
graph/factory authority chain, so the VM stays ignorant of world/facet plumbing
details without carrying story/media-specific dispatch tasks.


### System Handlers (`system_handlers.py`)

SYSTEM-layer behaviors registered at module import time on `vm_dispatch`. These are the
built-in VM behaviors that run for every node regardless of story content.

**System handlers are duck-typed, not type-gated.** Each handler checks for the relevant
method via `hasattr(caller, "method_name")` rather than `isinstance(caller, SomeTrait)`.
This means:
- Any node class that exposes `apply_effects` participates in effect dispatch
- No required inheritance from `HasEffects` — composition by convention
- Story-layer node types with their own base classes can opt in by implementing the method

**Two-phase effect dispatch:**

```python
@on_update
def apply_runtime_effects(*, caller, ctx, **kw):
    if hasattr(caller, "apply_effects"):
        caller.apply_effects(phase=ResolutionPhase.UPDATE, ctx=ctx)

@on_finalize
def apply_final_runtime_effects(*, caller, ctx, **kw):
    if hasattr(caller, "apply_effects"):
        caller.apply_effects(phase=ResolutionPhase.FINALIZE, ctx=ctx)
```

UPDATE effects fire on arrival. FINALIZE effects fire on departure/commit. The
`trigger_phase` field on `TraversableEffect` determines which handler fires it.

**Container descent is a PREREQS handler.** When the cursor arrives at a container node
(`is_container=True`), the system PREREQS handler calls `node.enter()` and returns the
resulting `AnonymousEdge`. The frame's PREREQS aggregation is `first_result`, so this
redirect is followed and the pipeline re-runs at the source node. Nested containers
descend recursively through normal pipeline execution.


---

## Cross-Cutting Design Decisions

### Why Dispatch Cannot Bootstrap Itself

The authority chain (`graph.get_authorities()` → `[story_dispatch, world_registries]`)
must be assembled before any dispatch call fires. This means the assembly mechanism
cannot be a dispatch hook. `PhaseCtx.get_authorities()` uses
`getattr(graph, "get_authorities", None)` — a plain duck-type check — for exactly this
reason.

This is a fundamental structural constraint: **you cannot use dispatch to assemble the
dispatch chain.** Any future redesign of the authority pattern must respect this.
`Graph.get_authorities()` is the correct primitive precisely because it is a method
call, not a hook invocation.

### Deterministic Replay as a Core Invariant

Every source of non-determinism in the VM is either eliminated or seeded:

- `random` is seeded from `hashing_func(graph.value_hash(), cursor.uid, step_base)`
- Offer selection is deterministic given a fixed offer list (no tie-breaking by insertion
  order in the current implementation — priority + distance give a total order)
- Namespace assembly is deterministic (ancestor chain is a tree, traversal order is fixed)

Replay works by re-running `resolve_choice` with the same sequence of chosen edges
against the same initial graph state. The seeded RNG ensures random effects produce the
same outcomes. The ordered output stream accumulates replay-stable records.

**`rand=None` is backward-compatible in RuntimeOp.** Expressions that don't use `rand`
are unaffected by whether a seeded `Random` is injected. Expressions that do use `rand`
must be written to expect it — if they call `rand.random()` and `rand` is not injected,
they will get a `NameError`. This is intentional: non-deterministic expressions should
be explicit about their randomness.

### The Wrapper Inheritance Ladder

Every vm-layer concept wraps a core primitive rather than modifying it:

```
core.Edge           topology endpoints
  vm.TraversableEdge    + entry_phase, return_phase
    story.Choice          + narrative metadata, label, availability label

core.Effect         serializable expression
  vm.TraversableEffect  + trigger_phase
    story.StoryEffect     + narrative context helpers (future)

core.Predicate      serializable boolean expression
  (used directly in vm.HasAvailability — no phase annotation needed)
```

This pattern keeps each layer's additions local, prevents upward imports, and gives
authors a consistent inheritance ladder to extend. A story author who wants a custom
edge type with narrative-specific fields subclasses `Choice`, not `TraversableEdge`.
The vm machinery sees `TraversableEdge` (via `isinstance` or duck-type) and behaves
correctly.

### Search-Space Discovery: Authority-Native, Not VM-Wired

Resolver performs search-space discovery by calling the runtime context:

- `ctx.get_template_scope_groups()`
- `ctx.get_token_catalogs(requirement=req)`
- `ctx.get_media_inventories(requirement=req)`

World/factory authorities decide where that data comes from (story lineage maps,
world fields, asset/resource managers, mod systems). The VM contract is only
"typed context in, normalized registries/catalogs/inventories out."

This keeps provisioning extensible without adding VM-specific integration points
for each new story/media search space.

### Availability vs. Existence

The system distinguishes between *existence* (a choice is structurally present in the
graph) and *availability* (the choice can currently be offered to the player). Renderers
receive the complete choice list with availability flags; the decision to hide unavailable
choices entirely vs. showing them grayed-out is a presentation concern, not a VM concern.

This separation prevents anachronistic content problems where future states would appear
before they should be visible. The VM creates all structurally possible choices via
`edges_out`, marks their availability via `HasAvailability.available(ns=ctx.get_ns(node))`,
and passes the annotated list to the renderer. The renderer decides presentation.

---

## v37 → v38 VM Migration Summary

| Aspect | v37 | v38 | Rationale |
|--------|-----|-----|-----------|
| Effect lists | `entry_effects` / `final_effects` (two fields) | `effects: list[TraversableEffect]` + `trigger_phase` | Single list, phase declared on the effect |
| Availability/Effects location | `core.bases.HasAvailability`, `HasEffects` | `vm.traversable.HasAvailability`, `HasEffects` | Phase vocabulary is VM, not core |
| Token provisioning | token helpers in core | `TokenProvisioner` in vm | Provisioning is context-aware; core is timeless |
| Template discovery | Graph/facet call-chain wiring | `ctx.get_template_scope_groups()` via factory authority | VM no longer knows world internals |
| Catalog discovery | Explicit wiring / polling APIs | `ctx.get_token_catalogs()` via factory authority | Unified discovery contract across search spaces |
| System handlers | Self-registering mixins via `@on_update` on class body | Module-level `@on_update` with `hasattr` duck-type | No import side effects on dispatch registry |
| Phase dispatch | Manual aggregation per `do_*` function | `AggregationMode` table driving factory (planned) | Eliminate copy-paste; aggregation mode is data |
| Provisioner registration | Implicit (attached to context) | Explicit call in `gather_offers` | Clear source of truth for what generates offers |
| RNG | `Random()` on each use | `ctx.get_random()`, seeded from graph state | Deterministic replay |
| Namespace | Rebuilt per expression | Cached per node per PhaseCtx | Performance; stable within pipeline pass |
| Container descent | `enter()` / `exit()` methods | `enter()` only; ascent via normal edge/stack | Ascent is not a node operation — it's a pipeline continuation |
| TraversableSubgraph | Synthetic source/sink nodes with auto-wired edges | `source_id` / `sink_id` on existing members | No hidden graph pollution |

---

## Architectural Principles at the VM Layer

### Policy-Free Execution Mechanics

VM defines *how* the pipeline runs, not *what* it does. System handlers provide the
built-in VM behaviors (container descent, effect application, namespace contribution).
Story handlers provide narrative behaviors (content emission, character state). World
handlers provide domain behaviors (token catalog lookup, media provisioning). None of
these require vm to know anything about story concepts.

### Context as the Integration Surface

`PhaseCtx` is the integration surface between vm mechanics and application policy.
Everything vm needs to run is accessible through ctx: registries, namespace, graph,
randomness. Everything application layers need to inject is provided by implementing
the ctx protocol. Neither side knows the other's internals.

### Offers as a Decoupling Mechanism

Provisioners, offers, and selection policies decouple *finding* providers from *choosing*
among them. A provisioner knows how to generate candidates; it knows nothing about
which candidate will win. Selection policy (`provision_policy`, `priority`, `distance`)
is data on the offer, not logic in the provisioner. This means selection strategy can
evolve (scoring, player preference, author hints) without touching provisioner code.

### Correctness Over Cleverness

For MVP, the namespace is always recomputed from `cursor.ancestors` rather than
incrementally maintained. Container descent recurses through normal pipeline execution
rather than being a special mechanism. These are intentional choices: correctness is
established first; optimization (incremental namespace, descent memoization) is
deferred until profiling identifies actual bottlenecks.

---

*See also `CORE_DESIGN.md` for the timeless primitives vm builds on. Companion design
notes for `tangl.story` and `tangl.service` will follow the same pattern.*
