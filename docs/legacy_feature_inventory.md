# Legacy Story, Mechanics, and Media Feature Inventory

## Purpose

This document surveys the historical `tangl.story`, `tangl.mechanics`, and `tangl.media` modules (plus the related `scratch/` experiments) and identifies concepts that remain valuable for the current engine. Each subsection highlights what is salvageable, why it matters, and how it can align with the modern `tangl.core` and `tangl.vm` architecture.

## Story Graph Concepts

### Structural flow (fabula / episodic process / syuzhet)
- The legacy notes distinguish *fabula* (latent possibility space), *episodic process* (cursor-driven traversal), and *syuzhet* (journal output).【F:engine/src/tangl/story/notes.md†L1-L31】 These still map cleanly onto core graph + VM resolution: the graph encodes fabula, `vm.Frame` drives episodic resolution, and `core.fragment` + journal registries store the syuzhet.
- Chronological tooling such as “story time vs discourse time,” temporal edges, and consequence propagation give us vocabulary for domain handlers that manage non-linear traversal within the phase pipeline.【F:engine/src/tangl/story/notes.md†L19-L53】

### Structural nodes
- Scenes aggregate blocks, roles, and settings, expose local context, and gate traversal on casting/scouting hooks.【F:engine/src/tangl/story/episodic_process/scene.py†L1-L87】 In the modern engine these behaviors belong in structural domain handlers layered on top of `core.graph.Node` subclasses that participate in VM phases (validation, planning, journal, finalize).
- Scratch prototypes show companion patterns: scenes exposing child maps, automatic continuation to entry blocks, and dot-access of sub-elements for scripting.【F:scratch/legacy/story/story-32/scene.py†L1-L58】 These patterns can be reintroduced via scope helpers or `vm.Context` accessors rather than bespoke magic methods.

### Resource nodes and affordances
- Actors remain resource nodes that provide context, while `Role` edges act as dependency placeholders that can search, instantiate, or clone actors before traversal.【F:engine/src/tangl/story/fabula/actor/actor.py†L13-L40】【F:engine/src/tangl/story/fabula/actor/role.py†L1-L80】
- This aligns with the current dependency handling in `vm.planning`: roles become specialized `DependencyEdge` derivatives whose planning handlers resolve `successor` references, while actors themselves can just extend `core.entity.Entity` or `core.graph.Node` with tags.

### Narrative lifecycle hooks
- The notes outline lifecycle hooks (new, init, gather context, render, availability checks, effects) for every story node class.【F:engine/src/tangl/story/notes.md†L81-L108】 These correspond to VM resolution phases (`ResolutionPhase.VALIDATE` for availability, `PLANNING` for dependency realization, `UPDATE` for effects, `JOURNAL` for render). Many helpers already exist in `vm.simple_handlers`; we should refactor remaining legacy hooks into those phase-aware registries.

### Salvageable pieces
- Keep the taxonomy (books/acts/scenes, events, roles/settings/props, narrative contracts, tension/emotional beats) as domain-specific registries layered onto the generic graph. They become data schemas + handler bundles rather than bespoke base classes.
- Legacy world and controller APIs hint at service endpoints for listing worlds, creating stories, and retrieving media.【F:engine/src/tangl/story/story_controller.py†L1-L88】【F:engine/src/tangl/story/story_domain/world_controller.py†L1-L117】 These remain relevant for `service` integration once story orchestration stabilizes on the VM contracts.

## Mechanics Layer Concepts

### Package overview
- The mechanics notes call out subsystems that extend concept/structure nodes: sandbox traversal, stat progression, minigames, credential checks, demographic generation, look/wardrobe management, and crafting.【F:engine/src/tangl/mechanics/notes.md†L1-L23】 Each is a thin veneer atop story resources and should become optional capability modules (domains) added to the scope when relevant nodes are active.

### Actor presentation (Look)
- The look subsystem separates body traits, outfits, and ornaments, while also acknowledging transient pose/attitude and exposing two key interfaces: `describe()` for narrative output and `media_spec()` for art generation.【F:engine/src/tangl/mechanics/look/notes.md†L1-L22】 This maps naturally to journal vs media fragments: the describe handler feeds `JOURNAL`, while media specs feed media dependencies during planning.
- Outfit and ornament managers already depend on a `BodyRegion` ontology for coverage logic.【F:engine/src/tangl/mechanics/look/notes.md†L20-L22】 We can represent this as tagged entities and handler policies executed in `vm.planning` and `vm.update` phases.

### Progression, games, credentials
- Credential gameplay prototypes detail rule-driven inspections, limited interaction verbs, and day-by-day rule changes reminiscent of a constraint puzzle.【F:scratch/mechanics/credentials/notes.md†L1-L83】 These align with `vm.planning` (rule evaluation) and `vm.update` (state mutations), while journal/media output capture the player's decisions.
- Other mechanics (progression, crafting, sandbox) can be reimagined as domain registries that attach extra affordances (new choice edges, stat checks, resource synthesis) by registering handlers for specific node or resource types.

## Media Layer Concepts

### Provisioning vocabulary
- Media notes already frame dependencies as `DependencyEdge` derivatives resolved by provisioners that either discover existing media resource tags or invoke forges.【F:engine/src/tangl/media/notes.md†L4-L55】 The mermaid diagram explicitly situates these pieces inside `.core` and `.vm`, confirming that the architecture expected today’s separation of concerns.【F:engine/src/tangl/media/notes.md†L31-L91】
- Scratch protocols codify the same flow in interface form (media dependency script items yielding realized specs, forges returning new tags).【F:scratch/media/protocols.py†L1-L76】 This is directly compatible with `vm.planning` resolution receipts and `core.registry.Registry` for resource lookup.

### Salvageable pieces
- Reuse the vocabulary and spec interfaces: `MediaDependency` stays a dependency edge with optional template/path/data inputs; `MediaSpec` instances become the forge contracts; provisioners remain dispatch registries hooking into planning.
- Media controllers in story/world API wrappers can survive as service endpoints once the runtime surface area is finalized.【F:engine/src/tangl/story/story_controller.py†L41-L84】【F:engine/src/tangl/story/story_domain/world_controller.py†L87-L111】

## Protocol and Overview Blueprints

### Service protocols as architecture contracts
- The protocol dumps from late prototypes defined clean DTO expectations for worlds, stories, traversal nodes, and runtime hooks (locks, predicates, effects).【F:scratch/protocols/protocols-26.py†L10-L200】 They make clear that every structure resource exposes cascading namespaces and serialization helpers—a pattern that maps directly to `core.entity.Entity` + `core.registry.Registry` backed graphs.【F:engine/src/tangl/core/entity.py†L24-L147】【F:engine/src/tangl/core/graph/node.py†L11-L62】
- Traversable mixins, challenge blocks, and media handler slots in the protocols demonstrate how availability, update, and render behaviors were previously bundled per node.【F:scratch/protocols/protocols-26.py†L117-L160】 Under the current phase bus, those responsibilities should be broken into domain handlers registered for the appropriate VM phase (`VALIDATE`, `PLANNING`, `UPDATE`, `JOURNAL`).【F:engine/src/tangl/vm/frame.py†L23-L140】
- World/user/story protocols emphasized singleton registries, serialized responses, and templated instantiation.【F:scratch/protocols/protocols-26.py†L23-L200】 Those expectations align with `StreamRegistry` journaling and `vm.Context` namespaces, letting us preserve API ergonomics while modernizing execution.【F:engine/src/tangl/core/record.py†L31-L168】【F:engine/src/tangl/vm/context.py†L1-L114】

### Overview diagrams and technical notes
- The `notes_v34` overview captured the hierarchical relationships between entities, handler registries, and graph solver loops, and it remains a useful blueprint when aligning old terminology with the modern packages.【F:scratch/overviews/notes_v34.md†L1-L196】 The accompanying text enumerates structure/resource/trace node roles plus dependency/choice/blame edge semantics, which remain intact in today’s graph types.【F:scratch/overviews/notes_v34.md†L145-L167】【F:engine/src/tangl/core/graph/node.py†L11-L62】
- We ported the master mermaid diagram to a new “Core/VM Architecture Map” in `legacy_core_inventory.md` so the current layering is documented alongside the historical commentary. That updated diagram now references `Scope`, `Context`, the phase bus, and planning receipts to reflect how capabilities are dispatched in the modern runtime.【F:scratch/overviews/notes_v34.md†L5-L97】【F:docs/legacy_core_inventory.md†L12-L96】

## Mapping Strategy for the Modern Core + VM

1. **Treat legacy data classes as schemas.** Convert story/mechanics/media script models into Pydantic models that populate `core.graph.Graph` nodes and edges. Handlers become domain registrations rather than methods on bespoke subclasses.
2. **Leverage `vm.Frame` phases.** Map lifecycle hooks to the eight phases (`VALIDATE` for availability gates, `PLANNING` for dependency resolution like casting roles or provisioning media, `UPDATE` for stateful mechanics such as crafting outcomes, `JOURNAL`/`FINALIZE` for content fragments and replay patches).【F:engine/src/tangl/vm/frame.py†L1-L121】
3. **Namespace capabilities with domains.** Mechanics like look, progression, or credentials become `AffiliateDomain` implementations registered on relevant nodes/resources so that `vm.Context` activates them only when the cursor is within their scope.【F:engine/src/tangl/vm/frame.py†L1-L121】
4. **Represent resources as registries of entities.** Actors, locations, items, credentials, and media tags extend `core.entity.Entity` and live in `core.registry.Registry` instances. Dependency edges (roles, media deps, crafting recipes) remain `vm`-aware edges that resolve to concrete entities during planning.
5. **Expose services via thin controllers.** The story/world controller patterns can wrap the orchestrator and media registries, delegating to `core`/`vm` functionality while enforcing access levels. This keeps the API surface similar to the legacy service layer without reintroducing tight coupling.

## What to carry forward

- **Taxonomy and naming.** Retain the fabula/episodic/syuzhet terminology, scene/block/role organization, and mechanic glossaries as documentation and schema tags to keep continuity for authors.【F:engine/src/tangl/story/notes.md†L1-L108】【F:engine/src/tangl/mechanics/notes.md†L1-L23】
- **Handler contracts.** The legacy hook lists and media provisioning diagrams already anticipate the current phase bus; formalize them as handler registration guides rather than duplicated method stacks.【F:engine/src/tangl/story/notes.md†L81-L108】【F:engine/src/tangl/media/notes.md†L4-L55】
- **Interaction blueprints.** Mechanics like credentials screening or look rendering provide reusable gameplay/state machine templates that can become reference implementations for new domains.【F:scratch/mechanics/credentials/notes.md†L1-L83】【F:engine/src/tangl/mechanics/look/notes.md†L1-L22】

By reframing these ideas as data schemas and domain-specific handler bundles layered on top of `tangl.core` primitives and executed by `tangl.vm` phases, we can preserve the creative affordances of the legacy system without reintroducing the monolithic, highly coupled architecture that made earlier iterations brittle.
