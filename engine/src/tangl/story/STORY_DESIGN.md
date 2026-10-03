# tangl.story — Design Notes

> Status: Current contract
> Authority: Journal fragment types are defined in `tangl.journal.fragments`;
> story owns the narrative vocabulary, compilation, and journal policy layered
> over VM/core.

## Position in the Architecture

Story is the narrative domain layer between service and vm.

```
Service  → Lifecycle, persistence, transport
Story    → Narrative vocabulary, compilation, journal policy
VM       → Traversal, provisioning, execution pipeline
Core     → Graph/entity/dispatch primitives
```

Story may import vm/core. It must not import service.

## Canonical Surface

The story package is organized around four things:

- Narrative vocabulary: `Block`, `Scene`, `MenuBlock`, `Action`, `Actor`,
  `Location`, `Player`, `Role`, `Setting`. `Player` is an optional
  non-structural protagonist fixture: a provider `Node` that publishes itself
  into the scoped namespace (`player`) for authored predicate access. It is
  never auto-injected; a world opts in by composing a subclass (a generic
  world-level player-declaration API is intentionally deferred).
- Compilation: `StoryCompiler` turns authored data into a validated template
  registry plus compile metadata.
- Runtime authority: `World` is the singleton story authority and the public
  owner of `create_story(...)`.
- Runtime graph behavior: `StoryGraph` carries story locals, runtime template
  provenance, and story-layer authorities.

`StoryMaterializer` is a story-policy helper, not a second generic graph
factory. Generic topology materialization belongs to `GraphFactory` and
`TraversableGraphFactory`; story keeps only story-specific post-passes and
preview/prelink policy.

## Choice Disclosure

Choice availability and disclosure are separate Story contracts. Availability
continues to decide whether an `Action` can be selected. Disclosure decides
only whether an unavailable action is emitted as a disabled `ChoiceFragment`
with its blockers, or omitted from the reader's menu. Omission never makes a
path selectable; direct submission still follows ordinary VM validation.

At rendering, `unavailable_choice_disclosure` resolves from the current scoped
namespace (`"disclose"` by default, `"hide"` when authored), so world locals
provide a default and nested scene/container/block locals override it. An
`Action.unavailable_choice_disclosure` is an optional typed per-choice override
that inherits the scoped policy when absent. This is server-side Story policy,
not advisory `UIHints` and not a new client vocabulary.

## Runtime Authority Model

World/factory authority is the canonical story runtime model.

- `World` subclasses `TraversableGraphFactory`.
- `World.create_story(...)` calls inherited graph materialization, then runs
  story-only post-passes through `StoryMaterializer`.
- `Graph.get_authorities()` delegates through the bound factory, so runtime
  authority is `graph -> presentation/story base registries -> world/factory
  registries`.
- Template, token, and media lookup should go through world/factory authority
  methods, not through VM-owned story discovery seams.

The old provider-collection layer and domain-view compatibility wrappers are no
longer part of the runtime design.

### Construction-ready domain work

``World.create_story`` runs ``story.dispatch.on_story_ready`` handlers after
materialization, topology/prelink passes, and the namespace-dependent entry
override. The caller is the new ``StoryGraph``; its ``PhaseCtx`` points at the
selected entry. Handlers receive ``init_mode`` and the supplied initialization
``namespace`` and must return ``None``. They may finish construction of ordinary
graph bindings; they do not run the traversal pipeline, arrival effects, clocks,
or JOURNAL. Materialization counts include their additions.

This boundary is before Service primes the initial arrival. It is **not** a
post-arrival or per-playthrough seal. World-specific shape-changing startup work
must finish before bindings that depend on it are established. A later startup
that needs additional recruitment is not proven shape-complete merely because
``story_ready`` ran.

``freeze_shape`` remains an EAGER construction-time promise on an individual
graph, not a mutation ban during construction and not a cached graph on the
World. Prelinking and construction-ready extensions may establish known paths
under that policy; runtime provisioning must not invent new paths. Entry and
player preferences may gate existing paths without changing their existence.
Each new start constructs its own graph and selects its own entry/context. A
future post-setup seal would apply only to that playthrough after its arrival
recruitment, not to another player's start or NG+ run.

### Runtime materialization domain work

``StoryMaterializer.story_post_materialize`` invokes
``story.dispatch.on_story_materialized`` after a newly attached traversable
node has provenance and story topology. The caller is that node; its derived
``PhaseCtx`` preserves the materialization context and points at the new node.
Handlers run through the existing authority chain, return ``None``, and may
establish ordinary domain bindings. This is not an arrival, journal, or a new
VM phase. Already-wired nodes do not rerun the hook; restored graphs retain
their persisted bindings rather than rebuilding them during structuring.

Authored children do not by themselves make a runtime node an episodic
container. Automatic entry creation/finalization applies to ``Scene``;
hierarchical sponsors such as sandbox scopes remain grouping nodes.

An Action whose target is not realized can carry the ordinary ``destination``
Dependency, just like an authored lazy choice. Preview is non-mutating, and
selection recruits its target through the normal resolver. Triggered actions
use the VM's existing destination provisioning at PLANNING. Domain handlers do
not implement their own target materialization path.

## StoryGraph

`StoryGraph` is the runtime graph specialization for story execution.

- `locals` holds authored story globals exposed to runtime namespace assembly.
- `initial_cursor_ids` carries one or more story entry points.
- `wired_node_ids` records which runtime-created traversable nodes have already
  had story topology passes applied.
- `template_by_entity_id` and `template_lineage_by_entity_id` are rebuildable
  runtime provenance maps derived from `templ_hash` plus the authoritative
  template registry.

`StoryGraph.world` is a convenience property over the bound factory when the
factory is a `World`. The factory is the authority; the graph is the per-story
instance state.

## Continuity State Placement

Recurring story nouns should be durable graph concepts rather than reconstructed
from passage-local flags. Their current state and identity survive across scenes,
while scoped namespace gathering and journal composition derive the description
and opportunities appropriate to the current cursor.

Keep the following facts distinct:

- intrinsic and component state belongs to the concept or its owned managers;
- holdings, assignments, familiarity, and social posture belong to explicit
  relationships or relationship-like story state;
- committed encounters belong to ledger/receipt history and may deliberately
  mutate the participating concepts or relationships;
- recoverable questions about prior narration should remain derived queries over
  attributed journal fragments and their stable concept references;
- narrator identification and disclosure belong to concept-local
  `EntityKnowledge`;
- template lineage and planning bindings belong to `StoryGraph` provenance;
- generated actions and journal fragments are projections, not additional
  authoritative copies of the facts they render.

In particular, planning a concept into a scene does not imply a diegetic
encounter. Disclosing it may update narrator knowledge; traversing and committing
an interaction may update relationship state. Handlers must not infer one of
those facts merely from another surface's bookkeeping.

Symbolic prose references resolve from current graph state when a fragment is
generated. Changing one concept field therefore changes every later projection
that reads it. An emitted journal fragment is normally a historical snapshot of
what was disclosed at that step and must not silently rewrite when current state
changes. A deliberate retcon operation may instead replay the realized path,
regenerate affected attributed fragments, and preserve the revision through
replacement/tombstone records. That is an explicit rewrite of the syuzhet, not a
side effect of ordinary concept mutation.

## Compilation and World Assembly

### World Global Seeds

Each call to `World.create_story()` copies a finite graph of native mutable
containers from the world's global namespace into the new graph. Nested
dictionaries, lists, and sets belong to that graph, and repeated references in
the source remain repeated references in its copy; reference-like values remain
references rather than becoming a second persistence or ownership mechanism.

### Authored Node Effect Timing

Blocks may name `pre_effects` for UPDATE and `post_effects` for FINALIZE. The
older Block `effects` spelling is an UPDATE alias for `pre_effects`; an author
may not provide both spellings on the same block. Compilation lowers both names
into the VM's one `effects` list as `TraversableEffect` values with explicit
trigger phases, and decompilation restores the author-facing pair. Actions
remain edges and retain their ordinary UPDATE `effects` behavior.

`StoryCompiler` validates authored script data and produces:

- a `TemplateRegistry`
- world/story metadata
- entry-template references
- compile issues and source/codec metadata

World bundles select their source codec in `world.yaml`. Before decode, the
compiler imports the bundle's trusted domain module once; that module may expose
`get_story_codecs()` to contribute codecs for that bundle only. The local
contributions overlay the application's built-in registry without changing it,
then lower their private source representation directly to cardinal story data.
The same loaded domain adjuncts are reused for `WorldBuilder` assembly.

**A bundle contribution wins, and that is the intended rule.**
`_resolve_story_codec()` consults the bundle's contributions before the
application registry. Resolution is ordered by specificity, not by who
registered it: a contribution from a world's own domain module is inherently
scoped to that world, so it outranks a generic registration for the codec type.
If an application ships a weak `passages` codec, a world that ships its own gets
its own.

There is no parameterization seam, and none is planned. `get_story_codecs()`
returns constructed instances, so a contribution carries exactly one
configuration.

That is a smaller constraint than it first appears, because most of what tempts
an author to parameterize a codec does not belong to a codec at all. Graph
initialization depth is already a runtime per-story toggle — `InitMode.LAZY` /
`InitMode.EAGER` on `World.create_story()`, surfaced per request by the service
manager — and governs the initial shape of a new graph. Which media a template
prefers when it emits an instance onto a graph is a property of the template. A
codec reads source into cardinal data and nothing more. Policy about what a
graph looks like at birth belongs to the runtime toggle; policy about what a
template emits belongs to the template. Before reaching for a construction
parameter, check the option is really about *reading the source*; the first
candidate to be examined this way, CarWars' flavor-media mode, turned out to be
template-emission policy wearing a codec argument.

A finer binding — an application registration scoped to one world's singleton
label, outranking even that world's own contribution — is a natural extension if
a real conflict ever calls for it. Nothing needs it today, and it is not built.

Domain modules contribute through a small set of parallel hooks:
`get_authorities()`, `get_story_codecs()`, and `get_media_index_handlers()`, plus
the `class_registry` collected automatically from the module's `Entity`
subclasses.

The module itself is imported once and cached, but the hooks are called on every
domain-adjunct load, which is once per world-facet build: once per `compile()`,
once per `compile_anthology()` and shared across all its stories, and again for
`encode()`. Hooks should therefore be cheap and free of side effects — they
declare contributions, they do not perform setup.

That domain module also contributes a `class_registry` of its `Entity`
subclasses, and bare authored `kind` names resolve through it after the cardinal
vocabulary. Cardinal bare names win, so a bundle cannot quietly redefine
`Block` or `Scene`; everything the core does not already name is the world's to
supply. Explicit Entity class objects and dotted import paths instead identify
their class exactly, even when its bare `__name__` matches a cardinal. This is
the same registry the asset compiler uses for `asset_kind`, so a bundle
contributes block kinds and asset kinds through one pathway rather than by
subclassing `StoryCompiler`. An authored kind that resolves to nothing records
a `compile:unresolved_kind` issue instead of silently compiling as the fallback,
because a world losing its own block kinds should not look like a world that
never declared any.

`StoryCompiler.decompile()` is the inverse semantic projection: it recovers a
portable, deterministic cardinal mapping from a compiled template bundle for a
later codec to encode. It canonicalizes hierarchy and payload kinds rather than
recreating original file placement, section sugar, or diagnostic provenance.
`WorldCompiler.encode(bundle, story_bundle, story_key=None)` resolves the
bundle's matching codec, including its local domain contribution, and returns
an ``EncodeResult`` containing safe manifest-declared source artifacts and
structured diagnostics, without writing or materializing a graph. Near-native
encoding and the strict Twee 3 exporter both reject
multi-file stories rather than inventing a source repartitioning or
manifest-rewrite policy. The Twee exporter supports one ordinary ``world``
scene of non-anonymous blocks with text and simple actions, preserving passage
names, order, tags, header metadata, and format hints from codec state. Its
output is normalized rather than byte-identical; artifacts with import loss or
unrepresentable controls fail explicitly.

### Codec and Interchange Status

The minimum viable interchange spine is landed. Bundle-local codecs can lower
their own structured source directly to cardinal story data; deterministic
decompilation returns compiled templates to that same cardinal boundary; and
near-native YAML plus the strict simple-world Twee subset prove normalized
semantic fixed points through ``DecodeResult`` and ``EncodeResult``. Codec
losses also persist into the authoring-diagnostics path and prevent strict
Twee export.

The remaining work is tracked by issue #382 and should be driven by real source
formats rather than a speculative universal codec framework. The immediate
target is to retrofit the CarWars passages loader, or an equivalently
nontrivial demo-world side-loader, as a proper world-local codec. That proof
should precede broader work on per-operation fidelity vocabulary, explicit
lossy-export policy, opaque foreign-syntax residue, richer directory or archive
source roots, deterministic multi-file repartitioning, and source-span or
concrete-syntax support for same-file rewriting.

Strict export remains the default. A codec must not silently emit artifacts
after discarding information, and foreign source syntax must not leak into the
cardinal story vocabulary merely to make a particular format round-trip.

That compiled bundle is a build-time artifact. `WorldBuilder` copies the
surviving fields onto `World` and wires in adjunct resources such as:

- dispatch authorities
- class registry / imported domain modules
- media/resources/assets
- optional extra template registries
- world-owned presentation contributors through ordinary dispatch authorities

The compiled bundle may still exist as an internal helper during loading, but it
is not the canonical runtime contract for story execution.

## StoryMaterializer

`StoryMaterializer` keeps only story-specific runtime work:

- finalize scene/container contracts
- wire role/setting dependencies
- wire menu fanouts
- wire block actions
- wire media dependencies
- run eager prelink/preview policy

It does not duplicate generic graph topology expansion.

For runtime lookups it should prefer:

- `PhaseCtx` as the only VM execution context
- `PhaseCtx.derive(...)` for nested validation/preview child contexts
- `templ_hash` plus template selectors for template→entity recovery

It should not maintain parallel runtime context types or broad compatibility
maps when graph/template lookup can answer the question directly.

## Dispatch and Journal

`story_dispatch` is the shared story behavior registry.

- `on_gather_ns` contributes story/world symbols to assembled namespaces.
- `on_journal` emits raw journal fragments.
- `on_compose_journal` performs post-merge fragment rewriting.

The journal is the only narrative output surface. Story owns what fragments
mean; service/transports decide how to present them.

## Graph Analysis And Projection

Story also owns the graph-analysis helpers that sit *beside* runtime execution
rather than inside the VM pipeline.

- `ProjectedGraph` is the canonical analysis/view model for graph inspection.
- `project_story_graph(...)` is the live-graph adapter.
- `project_world_graph(...)` is defined by creating an eager frozen inspection
  story, then projecting that `StoryGraph`.
- Selection is expressed with core `Selector`; there is no parallel graph-query
  DSL.
- Processors are ordered pure transforms over `ProjectedGraph`.
- Structural rewrites such as chain collapse happen **after** projection, not
  on the source `StoryGraph`.
- Renderers such as DOT are dumb sinks over the projected view. They do not
  inspect runtime graph internals directly.

The canonical runtime inspection pipeline is:

`project_story_graph(...) -> annotate_runtime(...) -> focus_runtime_window(...) -> cluster_by_scene() -> collapse_linear_chains(...) -> mark_runtime_styles() -> to_dot(...)`

## What Story Does Not Define

Story does not define:

- traversal algorithms or phase ordering
- provisioning mechanics or offer ranking
- persistence, auth, or transport contracts
- graph/entity base abstractions
- media backend implementations

Story configures the engine for narrative use; vm/core provide the machinery.
