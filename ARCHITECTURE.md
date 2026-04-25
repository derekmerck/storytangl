# StoryTangl Architecture

> Read this before writing any code. This document describes what the system
> *is* — the concepts, the types, and how they relate. Everything in the
> engine is built from these pieces. If you need something and it's described
> here, use the one that exists. If it's not described here, you're probably
> inventing something that shouldn't exist — stop and ask.

> Status: current v38.3 architecture. Some story-layer authority and
> materialization seams are transitional; where that matters, this document
> describes both the current contract and the intended direction.


## The Four Layers

```
┌─────────────────────────────────────────────────────────┐
│  Service    Lifecycle, persistence, transport, auth      │
├─────────────────────────────────────────────────────────┤
│  Story      Narrative vocabulary, compilation,           │
│             materialization, journal rendering            │
├─────────────────────────────────────────────────────────┤
│  VM         Phase pipeline, provisioning, traversal,     │
│             replay                                       │
├─────────────────────────────────────────────────────────┤
│  Core       Entity, Registry, Graph, Selector,           │
│             Behavior, Record, Template, Factory          │
└─────────────────────────────────────────────────────────┘
```

Imports go down only. VM imports Core. Story imports VM and Core.
Service imports all three. **Nothing imports upward.** If you need
upward knowledge, pass it as a callback or protocol parameter.

Each layer has a `_DESIGN.md` file in its source directory that describes
the intended shape in detail. Read the relevant one before adding or
modifying modules in that layer.


---

## Core — The Vocabulary

Core defines the types that every other layer builds on. These types are
deliberately language-portable: no Python magic that couldn't be expressed
in Rust, TypeScript, or any language with algebraic types, first-class
functions, and associative collections.

### Entity (`core/entity.py`)

```{storytangl-topic}
:topics: entity
:facets: overview
:relation: documents
```

The universal base type. Everything managed by the graph is an Entity.

- Has a UUID (`uid`), an optional string `label`, and an optional `tags` set.
- Two comparison modes: by-identity (same UUID) and by-value (same
  serialized form). MRO determines which `__eq__` wins.
- Polymorphic serialization: `unstructure()` produces a constructor-form dict,
  `structure(data)` restores a live object.

### Selector (`core/selector.py`)

A composable predicate that matches entities.

- `Selector(label="x", has_tags={"foo"})` — keyword criteria.
- Criteria check fields first, then invoke callable attributes when present.
- `selector.with_criteria(**kw)` narrows (never widens) the predicate.
- This is the ONE blessed way to query entities. Do not write bespoke filter
  loops around registries.

### Registry (`core/registry.py`)

An indexed collection that owns entities. `UUID → Entity`.

- `find_one(selector)`, `find_all(selector)` for querying.
- `chain_find_all(*registries, selector)` for layered lookup across
  multiple registries.
- `RegistryAware` mixin: entity back-pointer to its owning registry.
- `EntityGroup` / `HierarchicalGroup`: reference-only membership groups
  over a registry's members.

### Graph (`core/graph.py`)

A `Registry` specialized for topology.

- **Node** — a graph member that can have edges.
- **Edge** — a directed relationship with `predecessor` and `successor`.
- **Subgraph** — a group of graph members within a graph.
- **HierarchicalNode** — a Node that is also a Subgraph (contains children).
  Hierarchical membership defines `parent`, `children`, `path`, `source`,
  and `sink`.
- Typed queries: `find_nodes(selector)`, `find_edges(selector)`,
  `find_subgraphs(selector)`.

**Factory back-pointer.** `graph.factory` references the singleton
`GraphFactory` that created the graph, when one exists. This is the same
pattern as `GraphItem.graph` and `RegistryAware.registry`: a back-pointer to
the thing that provides context the item cannot provide itself.

The default `get_authorities()` delegates to the factory:

```python
def get_authorities(self):
    return self.factory.get_authorities() if self.factory else []
```

That means a bare core graph inherits its authority chain from its bound
factory without needing graph-subclass-specific hook discovery.

### GraphFactory (`core/factory.py`)

A singleton graph authority and deterministic eager materializer.

`GraphFactory` is the new core abstraction that turns an already-resolved
template bundle into a live graph and then stays attached to that graph as
its behavior authority.

What it owns:

- a `BehaviorRegistry` (`dispatch`)
- a `TemplateRegistry` (`templates`)
- zero or more token singleton types (`token_types`)
- the graph class to instantiate (`graph_type`)

What it does:

- materialize template groups before nodes
- attach materialized entities into the graph hierarchy
- wire edges from canonical predecessor/successor references
- bind `graph.factory = self`
- expose graph-level authorities through `get_authorities()`
- preserve factory identity across graph structuring because it is a
  `Singleton`

The public materialization API is:

```python
factory.materialize_graph(graph=None, **graph_kwargs) -> Graph
```

This is intentionally narrower than the old story eager-init path. Core
`GraphFactory` is a deterministic topology expander for already-resolved
template topology. It is **not** a story compiler, resolver, or narrative
validator.

### Record (`core/record.py`)

A frozen Entity with content-based equality and a monotonic sequence number.
Used for immutable facts: journal fragments, events, patches.

- **OrderedRegistry** — append-only registry of records with range-slice
  queries over the sequence space.

### BaseFragment (`core/base_fragment.py`)

A `Record` subclass that serves as the base for all journal output.
Has `fragment_type`, `content`, and `origin_id`.

**All concrete reusable fragment types live in `journal/fragments.py`.**
There is no second fragment hierarchy.

### Singleton (`core/singleton.py`)

A frozen Entity where identity is `(class, label)`. One instance per label
per class. Hashable. Class-level registry.

**Singleton is a serialization strategy, not just a uniqueness constraint.**
Singletons serialize as `{"kind": Class, "label": "x"}` and deserialize by
looking up the live instance via `Class.get_instance("x")`. If you need a
reference-like entity that survives structuring without being deep-copied,
make it a `Singleton`.

### Token (`core/token.py`)

A mutable `Node` wrapping an immutable `Singleton`.

- `token_from` identifies the singleton referent.
- `label` names the token node in the runtime graph.
- Reads delegate to the singleton; mutable instance-var fields live on the
  token itself.

This is the "short sword" (type definition) vs. "Glamdring" (graph instance)
pattern.

### EntityTemplate (`core/template.py`)

A `Record` wrapping a prototype Entity payload.

- `compile(data)` — dict → template
- `decompile()` — template → dict
- `materialize()` — template → live entity
- `TemplateGroup` / `TemplateRegistry` provide hierarchy and lookup

**This is the ONE path from authored data to runtime entities.**

### Behavior & Dispatch (`core/behavior.py`, `core/dispatch.py`)

```{storytangl-topic}
:topics: dispatch
:facets: overview
:relation: documents
```

- **Behavior** — a callable wrapper with priority, dispatch layer, and
  optional caller-kind filtering. Returns a `CallReceipt`.
- **BehaviorRegistry** — a registry of behaviors. `chain_execute_all`
  assembles behaviors from explicit registries + context registries +
  inline callables, deduplicates, sorts, and yields receipts.
- **Dispatch hooks** — `on_*/do_*` pairs for common lifecycle events:
  init, create, add_item, get_item, remove_item, link, unlink.

This is the ONE dispatch/plugin mechanism. Do not invent others.

### Namespace (`core/namespace.py`)

- `HasNamespace` mixin: entities publish local key-value maps via
  `@contribute_ns`-decorated methods or fields.
- `get_ns()` collects only this entity's local contributions.
- Scoped namespace assembly is a VM concern.

### RuntimeOp (`core/runtime_op.py`)

Safe expression evaluation primitives:

- `Predicate` — boolean query
- `Effect` — state mutation

Core defines the shape. VM defines when and how they run.


---

## VM — The Execution Mechanics

VM defines how the graph evolves over time. It knows about traversal,
phases, provisioning, and replay. It does **not** define narrative
semantics such as scenes, actors, or story structure.

### TraversableGraph / TraversableGraphFactory (`vm/factory.py`)

VM adds one thin factory layer over core graph materialization.

- **TraversableGraph** — a `Graph` carrying `initial_cursor_id`, the default
  traversal entry chosen from graph shape.
- **TraversableGraphFactory** — a `GraphFactory` subclass that materializes a
  `TraversableGraph`, resolves the shallowest entry-like node, stamps
  `initial_cursor_id`, and validates traversal contracts. It also exposes
  `materialize_seed_graph(...)` for lazy seed-graph creation from a template
  subset.

This is intentionally narrow. VM does not define a second "runtime factory"
for planning or replay. Those remain runtime behavior over a traversable graph,
not separate graph-authority classes.

### ResolutionPhase (`vm/resolution_phase.py`)

An `IntEnum` defining the causal phase ordering:
`INIT → VALIDATE → PLANNING → PREREQS → UPDATE → JOURNAL → FINALIZE → POSTREQS`

### TraversableNode / TraversableEdge (`vm/traversable.py`)

Core provides topology. VM adds the traversal contract.

- **TraversableNode** — hierarchical node + availability predicates +
  runtime effects + mutable locals + container semantics.
- **TraversableEdge** — edge + availability + trigger phase + entry phase +
  optional payload.

These types define what cursor movement and phase execution mean.

### Frame (`vm/runtime/frame.py`)

Drives one runtime resolution call — a sequence of `follow_edge` steps that
run the phase pipeline until no redirect is produced.

The pipeline at each cursor position is:

1. **VALIDATE** — is this movement legal?
2. **PLANNING** — provision frontier dependencies
3. **PREREQS** — auto-redirect or container descent
4. **UPDATE** — apply effects and mark visited
5. **JOURNAL** — emit content fragments
6. **FINALIZE** — commit step record
7. **POSTREQS** — continuation redirect, if any

### PhaseCtx (`vm/runtime/frame.py`)

```{storytangl-topic}
:topics: phase_ctx
:facets: overview
:relation: documents
```

The ONE concrete context type for phase execution.

- `ctx.graph`, `ctx.cursor`, `ctx.step` — direct access
- `ctx.get_ns(node)` — cached scoped namespace
- `ctx.derive(...)` — create a child context for a different cursor or graph

Core and story may define protocols over this surface, but they should not
create competing runtime context objects.

### Ledger (`vm/runtime/ledger.py`)

Persistent state across choices. Carries:

- graph
- cursor id
- step
- output stream
- call stack

Creates `Frame` instances to execute one resolution cycle.

### Provisioning (`vm/provision/`)

The system that resolves "what does this node need?" into concrete graph
entities.

- **Requirement** — a `Selector` with provision policy and authored-path
  metadata
- **Dependency** — an edge carrying a requirement
- **Affordance** — optional resource attachment
- **Fanout** — an edge that dynamically generates child edges
- **Provisioners** — strategies that generate `ProvisionOffer`s:
  Find, Template, Token, InlineTemplate, Stub, UpdateClone
- **Resolver** — gather offers → filter → rank → bind

### VM Dispatch (`vm/dispatch.py`)

Phase hooks such as:

- `on_validate` / `do_validate`
- `on_provision` / `do_provision`
- `on_gather_ns` / `do_gather_ns`

These are the VM's execution surfaces.

There are also still a few story-flavored helper hooks in the current VM
surface, such as template-scope collection. Treat those as **transitional
seams**, not patterns to extend. The long-term direction is that graph
authorities participate through the normal behavior registry chain rather than
through specialized resource-discovery hook vocabulary.

### Traversal Queries (`vm/traversal.py`)

Pure functions over graph state:

- `get_visit_count`
- `is_first_visit`
- `steps_since_last_visit`
- `get_call_depth`
- `in_subroutine`


---

## Story — The Narrative Domain

Story defines the vocabulary that authored content writes against. It
translates between that vocabulary and the engine's runtime machinery.

### StoryGraph (`story/story_graph.py`)

A graph specialization carrying story-layer runtime state.

Today it adds:

- one or more initial cursor ids
- story locals
- a compatibility `world` property over the bound `factory`
- delegated access to the world's script manager and story materialization hooks
- template lineage maps from runtime entities back to templates
- runtime wiring markers

`StoryGraph` is currently a **transitional** graph subtype: it still carries
story-specific back-pointers and it currently overrides `get_authorities()` to
prepend `story_dispatch` and then cascade to the attached world.

### Episode Types (`story/episode/`)

- **Scene** — a `TraversableNode` container
- **Block** — a `TraversableNode` leaf; primary interactive cursor position
- **MenuBlock** — a block whose choices come from dynamic fanout
- **Action** — a `TraversableEdge` representing a player choice

### Concept Types (`story/concepts/`)

- **Actor** — a named character node
- **Location** — a named place node
- **Role** — a dependency edge binding an actor into structural scope
- **Setting** — a dependency edge binding a location into structural scope
- **EntityKnowledge** — epistemic state

### Compiler (`story/fabula/compiler.py`)

Takes authored script data, validates and normalizes it, and produces a
compiled `StoryTemplateBundle`:

- template registry
- metadata
- authored locals
- entry information

Compilation runs once. The resulting bundle can materialize many runtime
stories.

### Materializer (`story/fabula/materializer.py`)

`StoryMaterializer` is now a story-policy helper and compatibility wrapper,
not the primary owner of graph creation.

It still owns story-layer helper logic such as:

- preserves template lineage for runtime scope recovery
- wires structural/runtime story topology
- optionally pre-resolves dependencies in eager mode
- validates traversal contracts for the resulting graph

Generic graph creation now belongs to `World.create_story(...)` layered over
`vm.TraversableGraphFactory`, while `StoryMaterializer.create_story(...)`
delegates for compatibility.

### World (`story/fabula/world.py`)

The primary story authority and story-init entry point.

**Current shape:**

- `World` is a singleton `TraversableGraphFactory` subclass
- it owns a compiled `StoryTemplateBundle`
- it directly owns runtime story metadata, locals, entry ids, and adjunct
  providers
- it uses lower-layer factory materialization for eager and lazy graph creation
- it keeps compatibility aliases such as `domain`, `resource_manager`,
  `asset_manager`, `bundle`, and `script_manager`

What `World` does today:

- `create_story(...)` builds eager or lazy `StoryGraph` instances directly
- `get_authorities()` exposes optional world/domain behavior registries
- `get_template_scope_groups(...)` exposes optional runtime template scopes
- `get_media_inventories(...)` exposes optional runtime media inventories
- `find_template(...)` and `find_templates(...)` delegate through the
  `ScriptManager`

`World.bundle` remains as a compile-artifact compatibility surface for one
phase, but runtime story creation no longer depends on it as the active
authority.

### ScriptManager (`story/fabula/script_manager.py`)

A runtime facade over compiled templates.

It centralizes story-specific template lookup semantics and world-provided
scope-group extensions. `World` uses it as the public template lookup surface
today.

### Story Dispatch & System Handlers

Story-layer dispatch hooks (`story/dispatch.py`) and their default
implementations (`story/system_handlers.py`) handle:

- namespace contribution from story/world state
- journal fragment rendering for blocks and dialog
- menu affordance projection
- other story-level composition and formatting policy

Story participates in VM execution by exposing `story_dispatch` through
`StoryGraph.get_authorities()`.


---

## Service — Lifecycle and Transport

Service manages application lifecycle: persistence, endpoint dispatch,
access control, and response shaping.

### Orchestrator (`service/orchestrator.py`)

Registers controllers and resolves endpoint calls by name. On execute:
hydrate resources such as `User`, `Ledger`, and `Frame` from persistence,
call the method, and persist mutations back.

### ApiEndpoint (`service/api_endpoint.py`)

Metadata annotation on controller methods: access level, method type, and
response type.

### Controllers (`service/controllers/`)

- **RuntimeController** — create_story, resolve_choice, get_journal,
  get_available_choices, get_story_info, jump_to_node
- **WorldController** — list_worlds, compile_world, get_world_info
- **SystemController** — system status
- **UserController** — user management

### Gateway (`service/gateway.py`)

Wraps the orchestrator with inbound/outbound hook pipelines and render-profile
handling.

### Response Contract

Service returns one of two things:

- **Fragment response** — a list or envelope of `BaseFragment` records plus
  runtime metadata
- **Info response** — a typed payload inheriting from `InfoModel`


---

## Journal Fragments — The Complete Surface

All concrete reusable fragment types live in **`journal/fragments.py`**.
They inherit from `BaseFragment` (core). This is the ONE fragment hierarchy.

Representative types include:

- `ContentFragment`
- `ChoiceFragment`
- `MediaFragment`
- `GroupFragment`
- `KvFragment`
- `ControlFragment`
- `UserEventFragment`
- `AttributedFragment`
- `DialogFragment`
- `BlockFragment`


---

## Transitional Seams You Should Treat Carefully

These are real current seams, but they are not invitations to add parallel
infrastructure.

- **Core factory vs. story world authority.** Core now has
  `GraphFactory` as a singleton graph authority plus eager topology
  materializer. Story still uses `World`, `StoryMaterializer`, and
  `StoryGraph` back-pointers for runtime policy and scope recovery.
- **`StoryGraph.factory` is not yet the same thing as `Graph.factory`.**
  In core, `graph.factory` means singleton graph authority. In story,
  `StoryGraph.factory` is still used as a template-registry back-pointer for
  runtime scope recovery. Do not assume those surfaces are unified.
- **World round-tripping is still label-based shim logic.** `StoryGraph`
  currently serializes `world` as a label reference and restores it through
  `World.get_instance(...)`. This exists because world has not yet been moved
  onto the singleton graph-authority pattern.
- **Some VM/provider hooks are still story-colored.** Use existing seams
  carefully, but do not extend them into a parallel discovery framework.


---

## What Does NOT Exist (And Should Not Be Created)

- No parallel fragment hierarchy outside `journal/fragments.py`.
- No alternative runtime context competing with `PhaseCtx`.
- No alternative dispatch or hook mechanism competing with
  `BehaviorRegistry`.
- No alternative template → entity path competing with
  `EntityTemplate.materialize()`.
- No bespoke registry query sugar competing with `Selector`.
- No upward imports (`vm → story`, `core → vm`, etc.).
- No custom reference-tracking serializers for `Singleton`s.
- No second speculative VM factory layer beyond `TraversableGraphFactory`
  without a concrete new use case.
- No wrapper layer that pretends `World` is already a `GraphFactory`
  subclass when it is not.
