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
  `Location`, `Role`, `Setting`.
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

## Runtime Authority Model

World/factory authority is the canonical story runtime model.

- `World` subclasses `TraversableGraphFactory`.
- `World.create_story(...)` calls inherited graph materialization, then runs
  story-only post-passes through `StoryMaterializer`.
- `Graph.get_authorities()` delegates through the bound factory, so runtime
  authority is `graph -> world/factory -> dispatch registries`.
- Template, token, and media lookup should go through world/factory authority
  methods, not through VM-owned story discovery seams.

The old provider-collection layer and domain-view compatibility wrappers are no
longer part of the runtime design.

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

## Compilation and World Assembly

`StoryCompiler` validates authored script data and produces:

- a `TemplateRegistry`
- world/story metadata
- entry-template references
- compile issues and source/codec metadata

That compiled bundle is a build-time artifact. `WorldBuilder` copies the
surviving fields onto `World` and wires in adjunct resources such as:

- dispatch authorities
- class registry / imported domain modules
- media/resources/assets
- optional extra template registries
- story info projector

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

## What Story Does Not Define

Story does not define:

- traversal algorithms or phase ordering
- provisioning mechanics or offer ranking
- persistence, auth, or transport contracts
- graph/entity base abstractions
- media backend implementations

Story configures the engine for narrative use; vm/core provide the machinery.
