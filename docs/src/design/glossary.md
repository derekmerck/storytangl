# Canonical Vocabulary

> The terms StoryTangl uses, what they mean, and where they live in the code.

This glossary maps between **narratological concepts**, **engineering metaphors**,
and **implementation names**.  When design docs, docstrings, or commit messages
use these terms, they mean *exactly* what's defined here.

---

## Core Graph Primitives

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Entity** | managed object | Base data structure with identity, labels, tags, and comparison semantics | `core.entity.Entity` |
| **Registry** | collection | Indexed collection of entities with criteria-based search | `core.registry.Registry` |
| **Node** | vertex | Graph member; may carry state, children, and handler registrations | `core.graph.Node` |
| **Edge** | constraint | Directed link between nodes; carries predicate and effect semantics | `core.graph.Edge` |
| **Subgraph** | scope boundary | Named partition of related nodes with source/sink entry points | `core.graph.Subgraph` |
| **Graph** | program | Registry of nodes, edges, and subgraphs with membership and ancestry | `core.graph.Graph` |

## Narrative Architecture

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Fabula** | possibility space | The complete graph of events, characters, and relationships — all possible stories | `StoryGraph` after compilation |
| **Episodic process** | execution | Cursor-driven traversal that collapses fabula into a specific story | `Frame.follow_edge()` pipeline |
| **Syuzhet** | output trace | The linear journal of content fragments as experienced by the reader | `Journal` / `StreamRegistry` |
| **Block** | instruction | Traversable structural node that generates content when visited | `story.episode.Block` |
| **Scene** | function | Structural subgraph containing blocks, with local roles and settings | `story.episode.Scene` |
| **Action** | branch | Traversable edge representing a player choice between blocks | `story.episode.Action` |
| **Actor** | resource | Non-traversable concept node representing a character | `story.concepts.Actor` |
| **Location** | resource | Non-traversable concept node representing a place | `story.concepts.Location` |
| **Role** | dependency slot | Named placeholder linking a structural node to a required actor | `story.concepts.Role` (dependency edge) |
| **Setting** | dependency slot | Named placeholder linking a structural node to a required location | `story.concepts.Setting` (dependency edge) |

## Execution Model

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Frame** | stack frame | Runtime context for a single traversal step: cursor, namespace, phase state | `vm.Frame` |
| **Phase** | compiler pass | One stage of the resolution pipeline; pure contract on inputs/outputs | `ResolutionPhase` enum |
| **Cursor** | program counter | Current position in the structural graph | `Frame.cursor_id` |
| **Frontier** | enabled set | Available outgoing edges from the current cursor position | Computed by `do_validate` |
| **Namespace** | symbol table | Scoped mapping of identifiers, layered local → ancestor → domain → global | `Frame.gather_ns()` → `ChainMap` |
| **Ledger** | event log | Append-only record of patches (state changes) per story instance | `vm.Ledger` |
| **Patch** | diff hunk | Single atomic state change: `(step, target, op, before, after)` | Ledger entries |
| **Snapshot** | checkpoint | Serialized graph state at a point in time; replayable with patch log | `persistence.Snapshot` |

## Provisioning

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

## Dispatch and Behavior

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Behavior** | plugin | Callable registered for a specific task at a specific priority | `core.behavior.Behavior` |
| **Task** | hook point | Named extension point in the pipeline (e.g., `validate_edge`, `render_journal`) | Task name string |
| **Priority** | ordering | Execution order within a task: EARLY → NORMAL → LATE | `HandlerPriority` enum |
| **Layer** | override scope | Dispatch tier: SYSTEM < APPLICATION < DOMAIN < INSTANCE | `DispatchLayer` enum |
| **Aggregation mode** | fold strategy | How multiple handler results combine: `all_true`, `gather`, `merge`, `first`, `last` | `AggregationMode` enum |
| **Receipt** | audit record | Record of what a handler did: blame_id, result, timing | `JobReceipt` |
| **on_* / do_*** | event / handler | Hook pair: `on_*` fires registered behaviors; `do_*` is the task implementation | `dispatch.py` in each layer |

## Content and Presentation

| Term | Metaphor | Definition | Implementation |
|------|----------|------------|----------------|
| **Fragment** | log record | Atomic unit of journal output: content, type, source reference, metadata | `core.fragment.BaseFragment` |
| **Content fragment** | prose block | Text content rendered from a structural node | `ContentFragment` |
| **Choice fragment** | menu item | Available action with caption, availability status, and blocker diagnostics | `ChoiceFragment` |
| **Media fragment** | asset reference | Pointer to media content (image, audio) with staging hints | `MediaFragment` |
| **Journal** | narrative log | Ordered sequence of fragments constituting the syuzhet so far | `StreamRegistry` |
| **RIT** | inventory tag | Resource Inventory Tag — content-addressed reference to a media asset | `MediaRIT` |
| **Render profile** | Accept header | Client capability declaration guiding fragment → presentation transformation | Service-layer configuration |
| **Staging hints** | CSS-like metadata | Rendering suggestions (orientation, placement, z-index) for media fragments | `StagingHints` |

## Templates and Compilation

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
| **Scope layer** | stack frame | `(locals, behaviors, templates)` tuple contributed by a domain or subgraph | Namespace assembly during `gather_ns` |
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
