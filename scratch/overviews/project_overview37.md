# StoryTangl — Project Mission (v3.7)

## Purpose
Build a **narrative virtual machine** that represents story‐spaces (fabula), discovers a **self-consistent episodic process** through them, and **projects** that process into a linear discourse (syuzhet). The system works **forward** (generate fabula → episodes → syuzhet) and **in reverse** (infer a partial fabula from an existing syuzhet).

## What We’re Building
A **Python-first reference implementation** of a **self-evolving story graph** with scoped state and pluggable behaviors. Choices advance a **resolution frontier**, triggering rule-driven updates to both **data** (state) and **shape** (topology). Every step emits:
- a **Patch** (event-sourced, replayable mutations), and
- a **Journal entry** (human-readable fragments for rendering).

The Python implementation prioritizes clarity and ergonomics now, while the **core data and process model** remains portable to other runtimes later.

## Core Abstractions (minimal, clean)
- **StoryIR (graph)**: immutable history + transient workspace per step  
  - **Nodes**: `STRUCTURAL` (episodes/beats), `RESOURCE` (actors, props, locations), `META` (optional)  
  - **Edges**: `transition` (flow), `dependency/affordance/provenance` (semantics)
- **Facts**: monotone, queryable assertions derived from graph state; the unit predicates/guards read.
- **Frontier**: the “program counter”—cursor, enabled choices, and small call stack for redirects/returns.
- **Templates & Guards**: python callables that (a) test applicability and (b) bind/create nodes/roles (“provisioning”), enabling **affordances** when conditions are met.
- **Projections**:  
  - **Patch stream** (machines/audit/replay),  
  - **Journal stream** (clients/renderers).

## Resolution Lifecycle (per choice/tick)
1. **Validate** selected transition/guard.  
2. **Redirect/Return** (optional call stack).  
3. **Enter** scope; assemble layered **namespace** (local → ancestor subgraphs → domains → global).  
4. **Provision** via templates (bind existing resources, optionally create new) and attach **affordances**.  
4. **Update** (apply episode specific rules to update state).  
5. **Journal** (gather fragments; IO allowed but logged).  
6. **Post** bookkeeping (emit **intents**; no direct mutation).  
7. **Commit** a **single canonical Patch**; advance frontier.  
8. **Auto-follow** transitions if rules demand; otherwise block for the next choice.

## Scopes & Domains
- **Structural scopes** arise implicitly from nested subgraphs (book → act → scene → passage).  
- **Domain scopes** are **opt-in** (e.g., “blackjack”, “dialogue”), registered via tags or Python MRO.  
- Both contribute **locals, handlers, templates, and predicates**, merged into the call site’s namespace.

## Extensibility Model
A tiny **phase bus** dispatches **handlers** by `(phase, priority)`: `validate`, `enter`, `provision`, `journal`, `post`, `auto`.  
“Mechanics” (minigames, dialogue, combat) are **intent producers**: they compute and **emit effects**; the engine applies those effects during **commit** (event-sourced). Authors can ship Python subpackages that register handlers/templates for their domain.

## Determinism & Observability
- **One patch per tick**; canonical op ordering.  
- **Seeded RNG** per tick `(story_id, epoch, choice, payload_hash)`.  
- **External IO** (LLMs/media) goes through a deterministic IO port and is recorded in the Patch.  
- **Provenance** (origin edges) on nodes, edges, patches, and journal entries.

## Why This Matters
- **Validate** story spaces as solvable/coherent; detect unreachable beats and unsatisfied roles.  
- **Interpolate** existing narratives by locating them in fabula-space and exploring nearby paths.  
- **Author ergonomics**: rules/affordances attach themselves when facts become true; no nested if/else jungles.

## Design Goals
Transparent (scoped lookups), Observable (receipt/patch for every change), Repeatable (snapshot + patch log), Extensible (plugin behaviors, domains), and Portable (spec-first IR + clean contracts).

## Python Reference: pragmatic first pass
- Guards/templates/handlers are **Python callables** (DSL optional later).  
- Use **intents/effects** to centralize mutation; keep direct writes out of handlers.  
- Serialize with `orjson`/pickle now; annotate patches with `{plugin, version, code_sha}` for replay integrity.  
- Keep **Facts** simple (indexed dicts); add a small Rete-lite later if needed.

## MVP Milestones
1. **Frontier & choices** over a fixed graph (deterministic replay).  
2. **Facts & guards** (Python callables), enable/disable transitions.  
3. **Templates (bind first)** + **affordances**; then **creation**.  
4. **Journal + Patch** projections (one patch per tick).  
5. **Domains/scopes** with a minimal phase bus.  
6. **Verifiers**: reachability & role satisfaction with provenance.

**Mission:** Deliver a small, deterministic kernel and data spec that make complex narrative systems **auditable, extensible, and fun to author**—and prove it with a Python reference that writers can use today.
# StoryTangl — Project Overview (Integrated, 2025‑09‑05)

## Purpose
Build a **narrative virtual machine** that represents story‑space (fabula), discovers a **self‑consistent episodic process** through it, and **projects** that process into a linear discourse (syuzhet). The kernel must be **deterministic, auditable, and extensible**, with a Python reference that favors clarity now and a data/process model portable to other runtimes later.

---

## What Exists Now (v37 core + vm)
- **Entity & Registry** (core): base identity, labels/tags, criteria‑based search; `Registry` holds typed `Entity` instances.
- **Graph IR** (core): `GraphItem` → `Node`, `Edge`, `Subgraph`; membership and ancestry helpers; `Graph.add_*()` validates linkability; label and path addressing.
- **Dispatch/Handlers** (core): `Handler`, `HandlerPriority`, `HandlerRegistry`, `JobReceipt` (with `blame_id` + `seq`), deterministic ordering.
- **Domains & Scope** (core): `Domain(vars, handlers)` + `global_domain`; `Scope` composes a layered namespace and merges handlers from active domains (anchor → ancestors → globals). `DomainRegistry.find_domains_for()` is a stub to be implemented.
- **Singletons** (core): immutable `Singleton` registry plus `Token[T]` wrapper for graph‑attachable instance variables.
- **Event Sourcing (preview)** (vm): `Event{CREATE,READ,UPDATE,DELETE}`, `ReplayWatcher`, `WatchedEntityProxy`/`WatchedRegistry` that emit events and support `replay_all` to produce a disposable preview graph.
- **Resolution Session** (vm): `ResolutionPhase` and `Session.follow_edge()` control loop; phases currently call handlers via a `Context` that builds the scope and per‑phase namespace. Redirect stacks and auto‑follow are TODO.
- **Provisioning Skeleton** (vm): `Provider`, `ProvisionOffer`, `ProvisionRequirement`, `Provisioner.run()`; generic finder/builder placeholders exist, concrete providers TBD.

---

## Core Abstractions (spec)
- **StoryIR (graph)**: typed nodes (`STRUCTURAL`, `RESOURCE`, eventual `META`) and edges (`transition`, `dependency/affordance/provenance`), plus subgraphs for hierarchical structure (book → act → scene → beat).
- **Frontier**: the “program counter”: current cursor, enabled choices, and (planned) redirect/return stack.
- **Handlers by Phase**: tiny **phase bus** dispatches registered handlers by `(phase, priority)`; handlers return **JobReceipts** (deterministic order).
- **Providers/Templates**: domain plugins propose **offers** (find or create) to satisfy **requirements** or expose **affordances**; the **Provisioner** selects and accepts offers to mutate the working state/shape.
- **Projections**: 
  - **Event stream** exists today (per mutation, via watchers).
  - **Patch per tick** is planned: collapse phase results into one canonical patch during `FINALIZE`.
  - **Journal stream** is planned: human‑readable fragments collected during `JOURNAL`.

---

## Lifecycle (per choice / “tick”)
1. **VALIDATE**: ensure proposed cursor/transition is legal.
2. **PLANNING**: solicit provider **offers** (affordances + reqs); accept per policy.
3. **PREREQS**: optional redirect before entering the target (call‑stack semantics TBD).
4. **UPDATE**: apply rule‑driven state/topology updates.
5. **JOURNAL**: gather fragments for rendering (I/O allowed but must be logged).
6. **FINALIZE**: bookkeeping; (planned) emit a **single patch**.
7. **POSTREQS**: optional redirect after finalize.
8. **Advance Frontier** or **Block** awaiting next choice.

_Status_: VALIDATE/PLANNING/UPDATE/JOURNAL/FINALIZE dispatch through handlers; redirect stack and auto‑follow are TODO; providers are skeletal; journal & patch consolidation not yet implemented.

---

## Scopes & Domains
- **Structural scopes**: emerge from subgraph ancestry (nearest first).
- **Domain scopes**: **opt‑in** via tags/MRO/registration; each domain contributes `vars` and `handlers` merged into the call‑site namespace.
- **Namespace**: a ChainMap layered as `local → ancestor subgraphs → domains → globals`, plus a per‑phase session layer (`phase`, `results`, `step`, `cursor`).

---

## Design Tenets
- **Deterministic**: stable handler ordering; (planned) one patch per tick; seeded RNG per tick.
- **Observable**: event log now; (planned) origin/provenance edges; patch metadata `{plugin, version, code_sha}`.
- **Extensible**: minimal contracts (entities/graph, handlers, providers, domains).
- **Portable**: keep the IR/rules spec‑first; Python impl stays pragmatic and thin.

---

## Roadmap (near‑term)
1. **DomainRegistry rules**: implement tag/MRO‑based domain discovery; add tests.
2. **Providers**: ship concrete `find`/`create` providers; wire PLANNING to accept offers and attach affordances/dependencies.
3. **Patch per tick**: buffer events during a tick and collapse to one **Patch** in `FINALIZE`; include deterministic RNG seed.
4. **Journal**: define fragment model and collection in `JOURNAL`; persist as a linear manifold separate from the working graph.
5. **Redirect stack & auto‑follow**: implement `PREREQS`/`POSTREQS` redirect edges + small call stack; support auto transitions.
6. **Facts/Guards (simple first)**: indexed dict of monotone facts queried by guards; add a “Rete‑lite” later if needed.
7. **Verifiers**: reachability and role satisfaction with provenance; CI tests over sample worlds.
8. **Service/presentation**: keep separate packages (per v3.2 vision); the core remains business‑logic only.