# tangl.story — Design Notes

> Status: Current contract
> Authority: Journal fragment types are defined in `tangl.journal.fragments`; `compose_journal` behavior is defined by `docs/src/design/story/JOURNAL_COMPOSE_CONTRACT.md`.
>
> Architectural intent, design decisions, and rationale for the canonical story
> package of the StoryTangl narrative engine.
> This document describes the current v3.8 framework. The source packages are
> `tangl.core`, `tangl.vm`, and `tangl.story` (no version suffix).
>
> Some story concepts described here are architectural commitments rather than
> fully closed feature surfaces. Where implementation remains partial, this note
> describes intended semantics first and current scope second.

---

## Position in the Architecture

Story is the narrative domain layer. It defines the vocabulary that authored
content writes against and the translation boundary between that vocabulary and
the engine's runtime machinery. It sits between vm (which defines the execution
mechanics) and service (which manages lifecycle and transport):

```
Service  → Lifecycle management, persistence, API
Story    → Domain semantics, narrative concepts                ← this document
VM       → Temporal evolution, context-dependent evaluation
Core     → Timeless primitives and mechanisms
```

Story imports from core and vm. Service and applications import from story.
Story MUST NOT import from service. This boundary was enforced in the Wave 2
simplification and is verified by the layering import guard tests.

### Litmus Test

| Question                                               | Layer      |
|--------------------------------------------------------|------------|
| Does it define a narrative entity type (actor, scene)? | Story      |
| Does it compile authored scripts into templates?       | Story      |
| Does it emit journal fragments from cursor nodes?      | Story      |
| Does it define traversal or provisioning mechanics?    | VM         |
| Does it manage persistence or access control?          | Service    |

### Story's Defining Characteristic

Story defines the narrative vocabulary and translation boundary between authored
content and runtime execution. It turns authored structural and conceptual
declarations into templates and graph entities that VM can execute without
understanding narrative-specific vocabulary. Compilation (author → templates) and
materialization (templates → runtime graph) are deliberately separate so one
authored world can produce many independent story instances without reparsing.

### Current Story Semantics

Five statements that orient readers quickly:

- The cursor moves among **structural nodes** (Block, Scene) via **Action edges**.
- **Concept nodes** (Actor, Location) are bound into structural scope through
  Role and Setting edges, not traversed directly.
- **Scripts declare** potential structure; the compiler normalizes; the materializer
  instantiates concrete graph entities. Authored declarations become historical
  metadata once materialization completes.
- The **journal** is the observable narrative product of cursor movement, the
  discourse trace exposed upward for service-layer rendering.
- **World facets** extend story policy without inverting layer boundaries.

### What Story Explicitly Does NOT Define

Story provides the *policy* that configures these mechanisms for narrative use,
not the mechanisms themselves:

- Traversal algorithms, cursor movement, availability evaluation (VM)
- Dependency resolution mechanics, offer selection, provisioning policy (VM)
- Phase pipeline ordering and execution (VM)
- Graph topology primitives, registries, entity base classes (Core)
- Persistence, serialization, transport, access control (Service)
- NLP transforms, pronoun systems, language banks (Lang)
- Media generation, resource indexing, asset storage (Media)

---

## Story Module Map

```
tangl.story
├── Dispatch       → dispatch.py             (story_dispatch registry, on_journal, on_gather_ns, etc.)
├── Graph          → story_graph.py          (StoryGraph: runtime graph with story locals and authorities)
├── Context        → ctx.py                  (StoryRuntimeCtx protocol)
├── Fragments      → fragments.py            (compatibility re-exports from `tangl.journal.fragments`)
├── Providers      → provider_collection.py  (collect_template_registries, collect_token_catalogs, etc.)
├── Handlers       → system_handlers.py      (APPLICATION-layer namespace, provisioning, and journal handlers)
├── Concepts       → concepts/
│                  → concepts/actor.py       (Actor: named character provider)
│                  → concepts/location.py    (Location: named place provider)
│                  → concepts/role.py        (Role: dependency edge binding actors into scope)
│                  → concepts/setting.py     (Setting: dependency edge binding locations into scope)
│                  → concepts/narrator_knowledge.py  (EntityKnowledge, HasNarratorKnowledge)
├── Episodes       → episode/
│                  → episode/block.py        (Block: primary interactive cursor node)
│                  → episode/scene.py        (Scene: container grouping blocks)
│                  → episode/action.py       (Action: choice/redirect edge between blocks)
│                  → episode/menu_block.py   (MenuBlock: dynamic choice hub)
└── Fabula         → fabula/
                   → fabula/compiler.py      (StoryCompiler → StoryTemplateBundle)
                   → fabula/materializer.py  (StoryMaterializer → StoryGraph)
                   → fabula/world.py         (World: entry point packaging bundle + facets)
                   → fabula/script_manager.py (ScriptManager: runtime template scope facade)
                   → fabula/types.py         (InitMode, InitReport, StoryInitResult, facet protocols)
```

---

## Component Design

### Dispatch (`dispatch.py`)

The story-layer behavior registry and hook decorators. `story_dispatch` is an
APPLICATION-layer `BehaviorRegistry` that `StoryGraph.get_authorities()` exposes
to the VM's dispatch chain.

**Story hooks registered on `story_dispatch`:**

| Decorator            | VM task            | Purpose                                     |
|----------------------|--------------------|---------------------------------------------|
| `on_journal`         | `render_journal`   | Emit raw journal fragments for cursor node  |
| `on_compose_journal` | `compose_journal`  | Post-merge fragment transformation          |
| `on_gather_ns`       | `gather_ns`        | Contribute symbols to assembled namespaces  |

`on_journal` and `on_compose_journal` are the two stages of journal production.
`on_journal` handlers emit raw fragments (content, media, choices) at different
priorities. `on_compose_journal` handlers receive the merged fragment list and can
replace it. The first concrete consumer and reference transform is dialog
micro-block rewriting.

`on_gather_ns` is the most widely used story hook. Role and setting modules each
register namespace contributors that expose resolved providers under their labels.
System handlers contribute story and world locals. The assembled namespace is what
`format_map` renders against in block content.

**Legacy keyword normalization.** `_normalize_legacy_register_kwargs` translates
v37 registration patterns (`caller=`, `is_instance=`, `handler_layer=`) to
current vocabulary (`wants_caller_kind=`, `dispatch_layer=`). This enables
gradual migration of handler registrations without a flag day.

**Legacy sub-hook seam.** `on_gather_content` is a surviving sub-hook from the v37
three-stage journal pipeline (gather-content / post-process-content / get-choices).
The current pipeline uses prioritized `on_journal` handlers instead.
`on_gather_content` has one active consumer (`mechanics.games.handlers`); the
other two sub-hooks were removed (zero consumers). See `scratch/legacy` for the
v37 pipeline if the full collect/enrich/compose decomposition is needed later.


### StoryGraph (`story_graph.py`)

Runtime graph specialization carrying story-level state that `Graph` alone
doesn't provide.

**Story locals.** `StoryGraph.locals` holds authored namespace values that
story-level `on_gather_ns` handlers inject into every assembled namespace. These
are set from the compiled bundle's `locals` field during materialization.

**Authority hookup.** `StoryGraph.get_authorities()` returns `[story_dispatch]`
plus any registries from the attached world's `get_authorities()`. This is the
mechanism by which story and world handlers participate in VM dispatch without any
import coupling between VM and story.

**Template lineage tracking.** `template_by_entity_id` and
`template_lineage_by_entity_id` record which template produced each materialized
entity and its scope-chain ancestry. This powers runtime scope matching: when the
resolver needs templates for a frontier node, `get_template_scope_groups(caller)`
returns templates from closest scope (the node's own template group) outward to
the broadest scope (the full template registry).

**World and factory back-pointers.** `world`, `factory`, and `script_manager` are
non-serialized back-pointers set during materialization. They give runtime handlers
access to world facets and the template registry without serializing compile-time
structures into the runtime graph.


### Context Protocol (`ctx.py`)

`StoryRuntimeCtx` is a structural `Protocol` extending `VmResolverCtx` with
story-specific accessors. It documents the minimal contract story helpers and
handlers need from a runtime context without coupling to one concrete context
implementation.

**Progressive protocol layering.** Core expects `get_authorities()` and
`get_inline_behaviors()`. VM extends with graph access, namespace caching, and
seeded randomness. Story extends further with `get_story_locals()`,
`get_location_entity_groups()`, and `get_template_scope_groups()`. Each layer
defines what it minimally expects. The runtime `PhaseCtx` satisfies all layers.


### Fragments (`fragments.py`)

Compatibility imports for journal output types emitted by story JOURNAL handlers.

**`ContentFragment`** carries rendered prose (`content: str`) plus `source_id`
tracing it back to the block that produced it.

**`ChoiceFragment`** carries one available or unavailable choice: the edge UUID,
display text, availability flag, blocker reasons, and optional UI hints.

**`MediaFragment`** is re-exported from `tangl.journal.fragments` through the
story compatibility surface. Story owns composition policy, not fragment model
definitions.

**Fragments are the observable discourse surface.** In narratological terms, the
runtime graph and ledger are the fabula, everything that happened. The journal
stream is the syuzhet, the particular discourse trace exposed upward. Story
defines what *kinds* of discourse artifacts exist (content, choices, media);
service decides how to present them. Fragment types carry semantic roles, not
rendering instructions. The same fragment list can be rendered as CLI text, a rich
web page, or a PDF.


### Provider Collection (`provider_collection.py`)

Shared helpers that story system handlers use to collect templates, token catalogs,
and media inventories from heterogeneous world facets.

All three collectors (`collect_template_registries`, `collect_token_catalogs`,
`collect_media_inventories`) follow the same pattern: iterate providers, call the
appropriate accessor, coerce the result into a normalized type, deduplicate by
`id()`, return a flat list. They exist because world facets come in many shapes
(protocols, bare registries, singleton types), and the VM's dispatch hooks expect
normalized results.


### System Handlers (`system_handlers.py`)

The APPLICATION-layer behaviors that make story-specific policy run during the VM
phase pipeline. This is the largest file in the story package and the primary
integration surface between story semantics and VM mechanics.

Story's runtime policy is expressed almost entirely through handler registration.
The handlers divide into three domains:

**Namespace contribution.** `on_gather_ns` handlers inject story-graph locals,
world locals, resolved roles, and resolved settings into the assembled scoped
namespaces that block content renders against.

**Provisioning discovery.** `on_get_template_scope_groups`,
`on_get_token_catalogs`, and `on_get_media_inventories` handlers delegate to
`provider_collection` helpers, collecting templates, token catalogs, and media
inventories from graph, world, and domain facets. The `on_provision` handler
invokes the resolver for each frontier node's dependencies.

**Journal emission.** `on_journal` handlers at EARLY, NORMAL, and LATE priorities
produce content, media, and choice fragments respectively. The `on_compose_journal`
handler rewrites explicit dialog micro-block syntax into attributed discourse
fragments when present.

The exact handler decomposition is contingent and may evolve. The three-domain
pattern is the stable commitment.


### Concepts (`concepts/`)

Story-domain entity types that give authors a vocabulary for characters, places,
and the dependency edges that bind them into narrative scope.

#### Actor and Location

Concept-layer provider nodes. `Actor` and `Location` both carry a human-friendly
`name`, publish metadata into local namespaces via `provide_*_symbols()`, and
mix in `HasNarratorKnowledge` for epistemic bookkeeping. They are referenced by
structural nodes through Role and Setting bindings rather than serving as the
primary traversal fabric themselves.

**Actor** is a pure concept provider. It extends `Node`, not `TraversableNode`,
because actors are entities referenced by structural scope, not cursor destinations.

**Location** is also a pure concept provider. It extends `Node`, not
`TraversableNode`, because locations describe where episodes happen rather than
forming part of the episodic traversal fabric themselves. If sandbox-oriented
place traversal arrives later, it should be introduced through a dedicated
runtime node type or a targeted wrapper rather than by making all locations
cursor destinations by default.

#### Role and Setting

Dependency edges that bind providers into scope. `Role(Dependency[Actor])` resolves
an actor and publishes it into the namespace under the role label.
`Setting(Dependency)` does the same for locations.

**Roles and settings are edges, not nodes.** This is a deliberate design choice:
they represent *relationships* between structural nodes and concept nodes, not
standalone entities. The resolved actor or location is the node; the role or
setting is the binding. This preserves the directionality rule (structural →
concept, never backward).

Both types register `on_gather_ns` handlers that walk the cursor's ancestor chain,
collect resolved roles/settings at each scope level, and contribute a merged
namespace with entries like `{label}` (the provider), `{label}_name`,
`{label}_role` (the edge itself), and aggregate `roles`/`settings` dicts.

**Provider namespace delegation.** Both `Role` and `Setting` call
`provider.get_ns()` to incorporate the provider's own namespace contributions.
This means an actor's `provide_actor_symbols()` output automatically appears
under the role label prefix in the assembled scope.

#### EntityKnowledge and HasNarratorKnowledge

Narrator-facing epistemic bookkeeping stored directly on story concepts.

**`EntityKnowledge`** tracks one narrator's knowledge state about one concept:
a string state (`UNKNOWN`, `ANONYMOUS`, `IDENTIFIED`), an optional nominal handle,
a first-description capture, and an identification source marker.

**`HasNarratorKnowledge`** is a mixin that adds `narrator_knowledge: dict[str,
EntityKnowledge]` keyed by narrator key. Multiple narrators can have independent
knowledge states about the same concept. The narrator key comes from
`ctx.get_meta()["narrator_key"]` at render time.


### Episodes (`episode/`)

Story-facing cursor vocabulary that wraps VM traversal contracts. These are the
structural units that authors write and that cursors visit, the primary traversal
fabric of a story graph.

#### Block

The primary interactive cursor node. Blocks carry authored prose (`content`), and
are the unit that JOURNAL handlers render into fragments. They are also the
declaration carrier for local actions, roles, settings, and media.

**Blocks store declarations, not resolved state.** The `roles`, `settings`,
`actions`, `continues`, `redirects`, and `media` fields are authored declarations
from the compiled script. The materializer turns these into actual graph edges
(Role, Setting, Action) during materialization. By the time the cursor visits a
block, the edges exist in the graph and the declarations are historical metadata.
This is a package-wide invariant. See *Declarations Become Metadata After
Materialization* below.

#### Scene

Container node grouping blocks into a traversable narrative segment and serving as
the primary scope boundary for role and setting declarations. Scenes own
source/sink cursor pointers (VM's `TraversableNode.source_id/sink_id`) so container
traversal is deterministic once children are materialized.
`finalize_container_contract` derives missing source/sink ids from child order
during materialization.

#### Action

The author-facing choice edge connecting blocks. Actions encode both navigation
and presented agency: `text` is what the player sees, `successor_ref` enables lazy
destination resolution, and `activation` shorthands map to VM `trigger_phase`
values (`"first"` → PREREQS, `"last"` → POSTREQS). Optional `accepts` and
`ui_hints` metadata travel through to `ChoiceFragment` for presentation.

#### MenuBlock

Dynamic choice hub extending Block. MenuBlocks declare `menu_items` selectors that
the materializer uses to gather compatible providers and project them into outgoing
actions. This is the first concrete consumer of the hub fanout pattern. Full
refresh policy, call/return menu semantics, and sandbox scheduling remain deferred.
See `docs/src/design/story/HUB_FANOUT.md` for the broader design direction.


### Fabula (`fabula/`)

The compilation and materialization pipeline that turns authored scripts into
runtime story graphs.

#### StoryCompiler → StoryTemplateBundle

The compiler accepts raw dicts or validated IR models and produces a
`StoryTemplateBundle` containing a validated `TemplateRegistry` tree, metadata,
locals, entry points, and provenance.

**Compilation is intentionally separate from materialization.** One compiled bundle
can produce many independent story graphs. This separation enables resetting a
story without recompiling, running parallel instances from one world, and testing
structural properties against the compiled fabula before any traversal.

**Action reference canonicalization.** The compiler normalizes authored shorthand
references (`"next_scene"`, `"scene2.block1"`) into a stable canonical form that
the materializer's lazy destination resolver can match against.

**Kind resolution.** The compiler attempts to resolve authored `kind` references
(e.g., `"Actor"` → the `Actor` class) during compilation, tolerating legacy
`obj_cls` input when an override cannot be imported.

#### StoryMaterializer → StoryGraph

The materializer walks a compiled template registry and instantiates concrete
runtime entities inside a `StoryGraph`. After the Wave 4 decomposition, it
operates in five explicit passes:

1. **Initialization** — create graph, set up story locals and factory back-pointers
2. **Materialization** — walk template tree, create nodes and edges via shared
   `materialize_template_entity` helpers
3. **Topology** — wire scene contracts, role/setting dependencies, menu fanout,
   actions, and media dependencies
4. **Prelink** — resolve dependencies eagerly (in EAGER mode), verify traversal
   contracts, promote hard errors
5. **Result assembly** — package graph, entry IDs, and diagnostics into
   `StoryInitResult`

**InitMode controls materialization breadth.** `EAGER` materializes the full
template registry, prelinks dependencies, and raises `GraphInitializationError`
on unsatisfied hard requirements. `LAZY` materializes only entry templates and
defers deeper graph expansion and dependency resolution to runtime planning.
EAGER is the default.

**Runtime materialization contract (`InitMode.LAZY`, phase 1).** The supported
LAZY behavior is now explicit and is defined in applicability, postconditions,
and observational-parity terms rather than "did a node get created."

Applicability

- A lazy realization step is applicable only when resolver has a concrete
  selected path (`target_ctx` plus any structural `build_plan`) and the hard
  blockers required for that selected path are satisfiable.
- Preview evaluates the same selected-path contract non-mutatingly. It may
  report blockers for missing containers or leaves, but it must not add nodes,
  edges, provenance, or wiring markers.

Postconditions: place graph

- A lazily created entity is attached at the same parent/path location that an
  eager realization would imply for that selected frontier.
- Template provenance is stamped immediately onto `StoryGraph` via
  `template_by_entity_id` and `template_lineage_by_entity_id` so later scoped
  provisioning uses the same nearest-first lineage groups as eager mode.
- Lazy-created containers satisfy entry behavior immediately. Phase 1 uses an
  entry-only rule: materialize the designated entry child, attach it, and set
  `source_id = sink_id = entry.uid`.
- Additional authored descendants of a lazy-created container may remain
  unresolved until later traversal reaches them. LAZY is not required to match
  EAGER's total graph breadth at creation time.
- The resulting placement must preserve immediate descent behavior and LCA-based
  scoping coherence for the realized frontier.

Postconditions: link graph

- Once a lazy-created node is attached, authored topology needed immediately for
  normal execution is wired before the frame follows into it: actions,
  role/setting dependencies, menu fanout, media deps, and other authored
  crosslinks represented by those edges.
- For selected-path container creation, immediate ancestor-visible hard deps
  needed for eager-equivalent arrival, traversal, or journaling must be
  resolved before arrival when traversal skips directly to a descendant leaf.
- Wiring is idempotent. Revisit, re-choice, and restore flows must not duplicate
  authored topology. Runtime wiring state is graph-adjacent (`wired_node_ids`)
  and reconstructible from existing graph evidence.

Observational parity with EAGER

- Parity is defined at the realized frontier, not by whole-graph identity.
- For the selected destination and any selected-path containers, LAZY and EAGER
  should expose the same offered actions, arrival namespace or rendered content
  where relevant, reachable entry behavior, hard blockers, and authored topology
  multiplicity.
- LAZY is allowed to differ from EAGER by leaving non-frontier siblings or
  deeper descendants unmaterialized until later traversal demands them.

**Focused contract tests.** The supported phase-1 contract is pinned by
`engine/tests/story/test_lazy_runtime_materialization.py`, with surrounding
path, availability, and traversal coverage in the existing story/vm tests.

#### World

The primary external entry point. `World` packages a compiled bundle with optional
facets (domain, templates, assets, resources) and exposes `create_story()`.

**World facets are protocol-typed.** `WorldDomainFacet`, `WorldTemplatesFacet`,
`WorldAssetsFacet`, `WorldResourcesFacet` are `Protocol` types that world
implementations can satisfy without inheriting from a specific base class. This
keeps world plumbing decoupled from the engine.

**Process-local instance registry.** `World._instances` provides a lightweight
`get_instance(label)` lookup so service controllers can find loaded worlds by
label without a separate world-management service.

#### ScriptManager

Runtime template lookup facade. `ScriptManager` wraps a `TemplateRegistry` with
`find_template` (single lookup by selector/uid/label/identifier) and
`get_template_scope_groups` (lineage-ordered scope groups for provisioning).

---

## Cross-Cutting Design Decisions

### Structural and Concept Vocabularies

Story maintains two distinct vocabularies within one graph, and the relationship
between them is the organizing principle of the package:

**Structural vocabulary** — scenes, blocks, and actions form the traversal fabric.
These are the nodes the cursor visits and the edges it follows. They are
authored as the "skeleton" of a story: what happens, in what order, with what
choices.

**Concept vocabulary** — actors and locations are the named entities that inhabit
the story world. They carry identity, knowledge state, and namespace payload, but
they are not themselves waypoints the cursor visits.

**Binding vocabulary** — roles and settings are the edges that connect structural
nodes to concept nodes. They are the mechanism by which "this scene needs a
villain" becomes "this scene's villain is Marta." Flow is always structural →
concept: a block declares a role slot, the provisioner resolves it to an actor.
Never the reverse.

This three-part vocabulary is the story-layer expression of the structural/concept
distinction described in `VM_DESIGN.md`. Keeping the vocabularies separate is what
makes provisioning tractable (the resolver only needs to satisfy edges from
structural nodes), namespace assembly clean (roles and settings contribute
providers under stable labels), and graph reasoning sound (no cycles between
structural and concept layers).


### The Wrapper Inheritance Ladder

Story types wrap VM types, which wrap core types:

```
core.Node               → topology
  story.Actor           → + name, narrator knowledge
  story.Location        → + name, narrator knowledge
  vm.TraversableNode    → + source_id, sink_id, availability, effects
    story.Block         → + content, authored declarations (roles, media, etc.)
    story.Scene         → + title, scene-level declarations

core.Edge               → topology endpoints
  vm.TraversableEdge    → + entry_phase, return_phase
    story.Action        → + text, successor_ref, activation, accepts

  vm.Dependency         → + requirement, provider binding
    story.Role          → + actor namespace publication, narrator knowledge
    story.Setting       → + location namespace publication, narrator knowledge
```

Each layer adds local fields without modifying the parent. VM machinery sees
`TraversableNode`/`TraversableEdge` via `isinstance` or duck-type and works
correctly regardless of which story subclass is in play.


### Declarations Become Metadata After Materialization

Scripts declare potential structure. The compiler normalizes those declarations
into templates. The materializer instantiates concrete runtime graph entities from
those templates. After materialization, the graph is the source of truth.

This means authored fields on blocks, scenes, and other materialized nodes, the
`actions`, `roles`, `settings`, `continues`, `redirects`, and `media` lists, are
not the active runtime state. They are historical provenance recording what the
author declared. The live action list comes from querying edges out of a block.
The live role bindings come from dependency edges. The live media dependencies
come from MediaDep edges.

This is one of the easiest places for future confusion. Code that reads
`block.actions` at runtime thinking it's the live action list is reading
compile-time provenance, not graph truth. Always query the graph.


### Compilation / Materialization Separation

This is the fabula/episodic boundary made concrete. The compiled bundle is the
fabula: everything that *could* happen. The materialized graph is one possible
starting state: the structural topology with dependency edges ready for runtime
resolution.

The separation enables:

- Resetting a story without recompiling
- Running multiple independent instances from one world
- Testing structural properties against the fabula before any traversal
- Swapping materialization strategies (EAGER vs. LAZY) without touching scripts


### Namespace Assembly as the Integration Surface

The assembled namespace is how story concepts become available to rendering. The
full chain is:

1. `on_gather_ns` handlers contribute symbols from story locals, world locals,
   roles, settings, and any other story-level providers
2. `do_gather_ns` (VM) merges these with core entity-local `get_ns()` and
   ancestor contributions
3. `ctx.get_ns(node)` caches the result per-node per-pipeline-pass
4. `render_block_content` renders block text via `format_map` against this
   namespace

This means adding new concept types to the namespace is purely a matter of
registering an `on_gather_ns` handler. No changes to the rendering pipeline are
required.


### Knowledge on Concepts, Not on Ledger

Narrator knowledge is stored as `narrator_knowledge: dict[str, EntityKnowledge]`
directly on story concept nodes (Actor, Location, Role, Setting), not in a
centralized ledger table. This means:

- Rollback is correct by default (knowledge rolls back with the graph)
- Multiple narrators get independent knowledge via narrator-keyed entries
- No schema change to Ledger for epistemic features
- Knowledge is co-located with the entity it describes

The trade-off is that knowledge is per-graph-instance, not cross-session. If
cross-session narrator memory is needed later, it belongs in the service layer.


### Concept Provisioning: Named vs. Generic

Story distinguishes named individuals (unique actors with identity, declared as
affordances) from generic templates (fungible role-fillers, stored as script records
in registries). Named individuals persist and are discoverable by identifier.
Generic templates are materialized on demand and can be replaced by any entity
matching the requirement criteria. See `docs/src/design/story/CONCEPT_PROV_DESIGN.md`
for the full treatment.

---

## Architectural Principles at the Story Layer

### Policy Over Mechanism

Story never changes *how* dispatch, provisioning, or traversal work. It only
configures *what* happens by registering handlers, extending node/edge types, and
providing templates. If you find story importing from `vm.runtime.frame` or
reaching into resolver internals, something has gone wrong.

### Authored Shape Through Compiled Templates

The compiler is the single validation boundary between authored intent and runtime
structure. Everything downstream of compilation can trust that templates are typed,
scoped, and internally consistent. The materializer doesn't re-validate. It
instantiates.

### Scope as Distance, Not Permission

Template scope and role/setting scope are proximity measures, not access control.
A world-scoped actor is available everywhere because it's distance-0 from the
root scope, not because it has a "world permission." Scene-scoped actors are
available in that scene because they're distance-0 from the scene's scope group.
The resolver ranks offers by distance. Scope is the geometry.

---

## Related Documents

| Document | Location | Status |
|----------|----------|--------|
| Conceptual foundations | `docs/src/design/story/philosophy.md` | Current (conceptual rationale) |
| Compiler history | `docs/src/design/story/compilers.md` | Superseded by this note + `tangl.story.fabula.__init__` |
| Concept provisioning | `docs/src/design/story/CONCEPT_PROV_DESIGN.md` | Current (claims implementation complete) |
| Hub fanout / MenuBlock | `docs/src/design/story/HUB_FANOUT.md` | Active (partial implementation) |
| Mechanics families | `docs/src/design/story/MECHANICS_FAMILIES.md` | Active architecture note |
| Presence/prose contract | `docs/src/design/story/PRESENCE_PROSE_CONTRACT.md` | Active spike |
| Core design | `engine/src/tangl/core/CORE_DESIGN.md` | Current |
| VM design | `engine/src/tangl/vm/VM_DESIGN.md` | Current |

---

*See `CORE_DESIGN.md` for the timeless primitives story builds on. See
`VM_DESIGN.md` for the phase pipeline and provisioning mechanics that story
configures. Companion design notes for `tangl.service` will follow the same
pattern.*
