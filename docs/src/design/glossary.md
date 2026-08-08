# Canonical Vocabulary

> The terms StoryTangl uses, what they mean, and where they live in the code.

This glossary maps between **narratological concepts**, **engineering metaphors**,
and **implementation names**.  When design docs, docstrings, or commit messages
use these terms, they mean *exactly* what's defined here.

---

## Core Graph Primitives

```{storytangl-topic}
:topics: entity, registry, graph
:relation: documents
:facets: overview
```

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Entity** | managed object | Base data structure with identity, labels, tags, and comparison semantics | `core.entity.Entity` |
| **Registry** | collection | Indexed collection of entities with criteria-based search | `core.registry.Registry` |
| **Node** | vertex | Graph member; may carry state, children, and handler registrations | `core.graph.Node` |
| **Edge** | constraint | Directed link between nodes; carries predicate and effect semantics | `core.graph.Edge` |
| **Subgraph** | scope boundary | Named partition of related nodes with source/sink entry points | `core.graph.Subgraph` |
| **Graph** | program | Registry of nodes, edges, and subgraphs with membership and ancestry | `core.graph.Graph` |

## Narrative Architecture

```{storytangl-topic}
:topics: traversal, journal
:relation: documents
:facets: overview
```

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Fabula** | possibility space | The complete graph of events, characters, and relationships — all possible stories | `StoryGraph` after compilation |
| **Episodic process** | execution | Cursor-driven traversal that collapses fabula into a specific story | `Frame.follow_edge()` pipeline |
| **Syuzhet** | output trace | The linear journal of content fragments as experienced by the reader | `Journal` / `OrderedRegistry` |
| **Block** | instruction | Traversable structural node that generates content when visited | `story.episode.Block` |
| **Scene** | function | Structural subgraph containing blocks, with local roles and settings | `story.episode.Scene` |
| **Action** | branch | Traversable edge representing a player choice between blocks | `story.episode.Action` |
| **Actor** | resource | Non-traversable concept node representing a character | `story.concepts.Actor` |
| **Location** | resource | Non-traversable concept node representing a place | `story.concepts.Location` |
| **Role** | dependency slot | Named placeholder linking a structural node to a required actor | `story.concepts.Role` (dependency edge) |
| **Setting** | dependency slot | Named placeholder linking a structural node to a required location | `story.concepts.Setting` (dependency edge) |

## Execution Model

```{storytangl-topic}
:topics: frame, phase_ctx, ledger, resolution_phase, replay
:relation: documents
:facets: overview
```

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Frame** | stack frame | Runtime context for a single traversal step: cursor, namespace, phase state | `vm.Frame` |
| **Phase** | compiler pass | One stage of the resolution pipeline; pure contract on inputs/outputs | `ResolutionPhase` enum |
| **Cursor** | program counter | Current position in the structural graph | `Frame.cursor_id` |
| **Frontier** | enabled set | Available outgoing edges from the current cursor position | Computed by `do_validate` |
| **Namespace** | symbol table | Scoped mapping of identifiers, layered local → ancestor → domain → global | `PhaseCtx.get_ns(node)` / `do_gather_ns()` → `ChainMap` |
| **Ledger** | event log | Append-only record of patches (state changes) per story instance | `vm.Ledger` |
| **Patch** | diff hunk | Single atomic state change: `(step, target, op, before, after)` | Ledger entries |
| **Snapshot** | checkpoint | Serialized graph state at a point in time; replayable with patch log | `persistence.Snapshot` |

## Provisioning

```{storytangl-topic}
:topics: provisioning
:relation: documents
:facets: overview
```

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Requirement** | package.json line | Declarative specification of what a dependency edge needs | `ProvisionRequirement` |
| **Offer** | candidate package | A proposed binding that could satisfy a requirement | `ProvisionOffer` |
| **Resolver** | package manager | Walks open dependencies, gathers offers, selects bindings by policy | `vm.provision.Resolver` |
| **Provisioner** | provider strategy | Concrete strategy for generating offers (find, create, template, clone) | `FindProvisioner`, `TemplateProvisioner`, etc. |
| **Scope group** | search radius | Set of registries to search for offer candidates, ordered by proximity | Resolver constructor args |
| **Binding** | lock-file entry | Committed assignment of a specific resource to a dependency edge | Resolved edge with destination |
| **Narrative debt** | technical debt | Provisioned concept not yet introduced to the reader via journal | Bound dependency with no journal coverage |
| **Narrative credit** | foreshadowing | Concept introduced in journal before any structural need requires it | Namespace-published, no dependency yet |

## Open Links and Projection

```{storytangl-topic}
:topics: open_link
:relation: documents
:facets: overview
```

> Canonical model: [Open Links: Requirement-Bearing Edges and the Planning
> Matrix](planning/AFFORDANCE_MODEL.md). The entries below are the shared
> vocabulary; the model doc owns the definitions, the planning matrix, and the
> filled audit table.

The canonical pipeline ordering, used consistently across design docs:
**binding/admission → projection → live availability → submission → backend
validation → mutation → journal output**. Binding answers "can this
relationship be formed?"; projection turns a bound link into the `Action` that
carries its predicates; live availability — a use-time filter applied *after*
binding and projection — answers "can this bound relationship be used now?" The
model doc's "Availability is after binding" section is the source of truth for
that distinction.

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Open link** | binding site | The planning primitive: a relationship represented before both endpoints are known — fixed endpoint + `Requirement` (open endpoint) + policy. Not a broken edge; the basic unit of work in the provisioner | `Edge + HasRequirement` (`vm.provision.requirement`) |
| **Dependency** | addressed pull | Open link with the requester fixed and the provider endpoint open. A hard dependency is consumer-side pressure: if it cannot bind, the frontier blocks and provisioning is driven to make a provider exist | `vm.provision.Dependency` |
| **Affordance** | broadcast offer | The same open-link object with the provider fixed and the context endpoint open. Provider-side availability: if no taker, nothing is offered and nothing fails | `vm.provision.Affordance` |
| **Fanout** | edge generator | A cardinality/rule-generation mode that produces many open links — not a third peer of dependency/affordance | `vm.provision.Fanout` + `Resolver.resolve_fanout` |
| **Scoped contribution** | open mic | Cross-domain pattern: a concept visible in the current scope contributes a phase-appropriate artifact (action, info affordance, journal fragment, modifier, redirect) | Pattern, not a class; sandbox's `SandboxInteraction` is its sandbox authoring form |
| **Dynamic action projection** | JIT menu build | Phase-local creation of ordinary `Action` edges from a scoped source coordinate, with explicit admission, payload, availability, projection, and cleanup. A named pattern, deliberately not one shared implementation | `project_menu_affordances`, `_project_sandbox_interaction`, game move provisioning, … |
| **Self-fanout** | REPL loop | A re-entrant game block re-projecting its currently available moves as self-loop actions until a terminal state routes outward. Conceptual coordinate; implemented as a local projector by design | `HasGame` move provisioning (`mechanics/games/handlers.py`) |
| **Cleanup ownership** | tag-scoped GC | Which projector may delete a generated action: a compound key of source-node scoping (the owner's `edges_out`) plus a discriminator tag set. The tag contract is **mutual non-subsumption** — a subset antichain — not set disjointness, since families intentionally share tags like `dynamic` | Audit table in the model doc; invariant tests in `engine/tests/mechanics/test_sandbox_architecture.py` |
| **Interaction request** | form submission | Conceptual name for the client-to-backend submission of a backend-issued interaction id plus collected payload. The wire field remains `edge_id`; renaming it is deferred pending a concrete client/compat need | `DirectEdgeRequest(edge_id, payload)` via `resolve_choice` |
| **Projection provenance** | audit stamp | Additive, non-authoritative lifecycle metadata recording which projector emitted a generated edge and why. Diagnostic only — never legality authority | Discriminator tags; sandbox source fields currently ride in `ui_hints` (normalization tracked in issue #268) |

## Dispatch and Behavior

```{storytangl-topic}
:topics: dispatch
:relation: documents
:facets: overview
```

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Behavior** | plugin | Callable registered for a specific task at a specific priority | `core.behavior.Behavior` |
| **Task** | hook point | Named extension point in the pipeline (e.g., `validate_edge`, `render_journal`) | Task name string |
| **Priority** | ordering | Execution order within a task, applied *after* layer: FIRST → EARLY → NORMAL → LATE → LAST | `Priority` enum (`core.behavior`) |
| **Layer** | ordering band | Execution order only — the first key of `Behavior.sort_key`. Confers no visibility. Ladder: GLOBAL < SYSTEM < APPLICATION < AUTHOR < USER < LOCAL | `DispatchLayer` enum (`core.behavior`) |
| **Authority chain** | visibility scope | Which registries are in play for a call — assembled by `chain_execute_all` from explicit args, `ctx.get_authorities()` (graph → world), then inline. **This** is what scopes a handler | `BehaviorRegistry.chain_execute_all`, `World.get_authorities()` |
| **Fold** (aggregation) | reduction strategy | How the receipts of a task reduce to one result. Chosen **per task at the `do_*` site**, not by the handlers. Decides *who wins* — see below | `CallReceipt.first_result` / `last_result` / `all_true` / `gather_results` / `merge_results`; `AggregationMode` enum names them |
| **Receipt** | audit record | Record of what a handler did: blame_id, result, timing | `JobReceipt` |
| **on_* / do_*** | event / handler | Hook pair: `on_*` fires registered behaviors; `do_*` is the task implementation | `dispatch.py` in each layer |

### Layers order; registries scope; folds decide

Three **independent** axes. The first two are commonly conflated because the layer
*names* suggest scopes — they are not scopes. The third is missed entirely: order alone
never determines who wins.

**1 · Registry membership determines visibility.** A behaviour is reachable when the
registry holding it is in the assembled chain. `BehaviorRegistry.chain_execute_all`
assembles registries from explicit arguments, then `ctx.get_authorities()` (which
cascades graph → world, with `World.get_authorities()` returning the world's own
`dispatch` registry plus any extra authorities), then inline behaviours — deduplicated by
identity. Handlers from *all* assembled registries are then pooled together.

**2 · `DispatchLayer` determines order only.** It is simply the first element of
`Behavior.sort_key` — `(dispatch_layer, priority, wants_exact_kind, seq)` — applied across
that pooled set. It confers no visibility of any kind. `LOCAL` sorts last so it can
observe and aggregate what earlier layers produced.

| Where it is registered | Visible | Layer's role there |
|---|---|---|
| shared module registry (e.g. `story_dispatch`) | everywhere that registry is consulted | ordering only — an `AUTHOR`-layer handler here is still global, just sorted later |
| a world's own `dispatch` registry | only when that world's authorities are in the chain | ordering only — a `SYSTEM`-layer handler here is still world-private, just sorted first |

**The practical trap.** The module-level decorators (`@on_render_text`, `@on_gather_ns`,
…) register into the **shared** story registry. Passing `dispatch_layer=AUTHOR` to one of
them does **not** make a handler world-private — it only makes it sort later. To get
world-privacy, register into the world's own registry. `worlds/composed_beat_demo` is a
live example of the ordering use: its `AUTHOR`-layer namespace override wins because it
sorts after the application default, not because it is scoped.

Compounding this, `BehaviorRegistry.default_dispatch_layer` is `APPLICATION`, so a
registration that omits the layer gets `APPLICATION` **regardless of which registry it
lands in** — which is exactly how the first two axes come to look like one.

**3 · The fold decides who wins.** Sorting fixes the *sequence*; the aggregator chosen at
the `do_*` site fixes what that sequence *means*. "Later wins" is a property of the fold,
not of the ladder. The two single-winner folds encode two different **kinds of decision**,
and they read the ladder in opposite directions on purpose:

- **Refinement** (`last_result`) — every layer contributes and the most specific one
  stands. Later layers *see* what earlier ones produced, so `LOCAL` sorting last is what
  makes an override possible.
- **Interception** (`first_result`) — the first authority to claim the decision takes it,
  and nothing downstream can un-claim it. Here `GLOBAL` sorting first is exactly right:
  the broadest authority gets first refusal.

| Fold | Winner | Effect on the ladder | Live tasks |
|---|---|---|---|
| `last_result` | last non-`None` | `LOCAL` beats `GLOBAL` — the override reading | `do_add_item`, `do_get_item`, `finalize_step`, `do_render_text`, media spec adaptation |
| `first_result` | first non-`None` | **`GLOBAL` beats `LOCAL` — inverted** | `get_prereqs`, `get_postreqs` |
| `all_true` | no winner — gate | order does not affect the outcome | `validate_edge` |
| `gather_results` | no winner — collects | order sets list order | `provision_node`, `apply_update` |
| `merge_results` | no winner — flattens | lists concatenate in order; on dict-key collision **later wins** (`ChainMap` over reversed results) | `do_create`, step dispatch |

So "the `LOCAL` handler overrides the others" is only true for a `last_result` task.

**Why redirects intercept.** `get_prereqs` / `get_postreqs` return an optional redirect
edge, which is a *claim on where the traversal goes next* — not a value to refine. An
application-wide redirect is rare, but when one exists it should trump any story-level
redirect, and interception gives that for free without a precedence table. Meanwhile the
common case is several redirects registered at the **same** layer, where the fold degrades
to `seq` — the monotonic registration counter, last key of `sort_key` — so among peers
**first registered wins**, which is the expected declaration-order reading. The rare
override and the ordinary case are served by one rule.

The practical consequence is that *abstention is the contract*: a redirect handler with
no opinion must return `None`, not a default edge. Returning something unconditionally at
an early layer silently claims every traversal.

One consequence is worth knowing before choosing a layer: the declarative
`trigger_phase` edge scanner is itself a `SYSTEM`-layer handler, so it preempts anything
registered at `APPLICATION`. A redirect meant to trump story-level ones belongs at
`GLOBAL`. See [Redirect precedence](traversal/NAV_DESIGN.md#redirect-precedence-who-claims-the-jump).

**Folds select results; they do not gate execution.** Every matching handler in the
assembled chain runs, whatever the fold. All live sites drain the receipt iterator
through varargs (`CallReceipt.first_result(*receipts)`), so `first_result` is a *selection*
over completed calls, not an early exit — side effects of later handlers still happen.
The way a handler declines is to **return `None`**: its receipt is retained for audit but
takes no part in the reduction.

*Realization note.* `AggregationMode` and `CallReceipt.aggregate()` are exported and unit
tested but have no live production call site — every `do_*` calls the `CallReceipt`
classmethods directly, and the `PhaseSpec` table that would have consumed the enum is
commented out in `vm/resolution_phase.py`. Treat the enum as the vocabulary for these
folds, not as the dispatch path.

**Related invariant:** the engine wires no mechanics. Mechanics register themselves on
import, and worlds choose which to import — see
[CANON_AND_REALIZATION.md](CANON_AND_REALIZATION.md).

## Content and Presentation

```{storytangl-topic}
:topics: journal, widget
:relation: documents
:facets: overview
```

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Fragment** | log record | Atomic unit of journal output: content, type, source reference, metadata | `core.fragment.BaseFragment` |
| **Content fragment** | prose block | Text content rendered from a structural node | `ContentFragment` |
| **Choice fragment** | menu item | Available action with caption, availability status, and blocker diagnostics | `ChoiceFragment` |
| **Media fragment** | asset reference | Pointer to media content (image, audio) with staging hints | `MediaFragment` |
| **Journal** | narrative log | Ordered sequence of fragments constituting the syuzhet so far | `OrderedRegistry` |
| **RIT** | inventory tag | Resource Inventory Tag — content-addressed reference to a media asset | `MediaRIT` |
| **Render profile** | Accept header | Client capability declaration guiding fragment → presentation transformation | Service-layer configuration |
| **Staging hints** | CSS-like metadata | Rendering suggestions (orientation, placement, z-index) for media fragments | `StagingHints` |

## Templates and Compilation

```{storytangl-topic}
:topics: template, factory, codec
:relation: documents
:facets: overview
```

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **World** | source distribution | Singleton factory holding scripts, templates, and handlers for a story domain | `story.World` |
| **Script** | source code | YAML (or other format) defining structural and conceptual content | Authored `.yaml` files |
| **Compiler** | front-end | Transforms scripts into a world bundle (graph template + registries) | `StoryCompiler` |
| **Materializer** | linker | Instantiates a live story graph from a compiled world bundle | `Materializer` |
| **Template** | class definition | Prototype data for creating new node instances during provisioning | Template registries |
| **Vocabulary bank** | word list | Themed word/phrase collections for procedural prose generation | Namespace contributors |

## Cross-Cutting Concerns

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Singleton** | immutable constant | Named, immutable entity serializable by reference | `core.singleton.Singleton` |
| **Token** | wrapped constant | Graph-attachable wrapper adding mutable instance state to a singleton | `core.singleton.Token` |
| **Domain** | library / plugin | Named scope contributing variables, handlers, and templates | `core.domain.Domain` |
| **Scope layer** | stack frame | Local `get_ns()` maps plus gather-time overlays contributed by a domain or subgraph | Namespace assembly during `do_gather_ns` |
| **Source / Sink** | entry / exit | Dominator and post-dominator nodes of a subgraph scope | Subgraph structural properties |

---

## Metaphor Families

The vocabulary above draws on several metaphor families.  When explaining
the system, prefer the metaphor that fits the audience:

**For software engineers:** compiler pipeline, package resolution, event
sourcing, stack frames.  "The resolver is a dependency solver; the ledger
is an event log; phases are compiler passes."

**For narratologists:** fabula/syuzhet, kernels/satellites, focalization,
morphological functions.  "The graph is the fabula; the journal is the
syuzhet; dependency edges are Chatman's kernels."

**For game designers:** possibility space, state collapse, choice
consequences, character casting.  "The story starts wide open and narrows
through play; roles are cast at runtime; choices close off branches."

**For the philosophically inclined:** Platonic forms casting shadows,
Kantian noumenal/phenomenal distinction, quantum superposition collapsing
through observation.  Use sparingly.  These are *analogies*, not
*implementations*.  The engine does not do quantum mechanics.
