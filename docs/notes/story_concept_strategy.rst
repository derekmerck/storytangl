Story Graph Concepts and VM Strategy
====================================

This note distills the useful ideas from the existing ``tangl.story`` modules and the
legacy implementations under ``scratch/legacy_src/story`` to clarify how episodic
narrative structures should be represented on top of the modern ``core`` runtime and
story virtual machine (VM) traversal loop.

Current Story Building Blocks
-----------------------------

* **Story graph and nodes** – ``Story`` already combines the traversal runtime with
  world/user context and journaling, so the graph itself can expose traversal state,
  story-level context, and a mutability flag for downstream systems.【F:engine/src/tangl/story/story_graph.py†L1-L23】
  ``StoryNode`` inherits context gathering from ``core`` nodes, giving every story
  element access to the graph, world, and shared locals namespace.【F:engine/src/tangl/story/story_node.py†L1-L25】
* **Structural traversal nodes** – Blocks and Scenes inherit ``TraversableNode`` to plug
  directly into the VM: blocks render content/effects and expose choices, while scenes
  coordinate blocks, roles, and settings through the same handler interfaces.【F:engine/src/tangl/story/structure/block.py†L1-L47】【F:engine/src/tangl/story/structure/scene.py†L1-L87】
  ``Action`` edges model interactive links via ``DynamicEdge`` so they can resolve
  successors lazily and participate in availability/effect checks.【F:engine/src/tangl/story/structure/action.py†L1-L50】
* **Resource concepts** – Actors, Locations, and their Role/Setting placeholders are
  implemented as associating nodes backed by ``DynamicEdge`` lookups. Roles cast actors
  on demand, and settings scout locations, establishing a clear pattern for other
  affordance/resource relationships (items, concepts, achievements, etc.).【F:engine/src/tangl/story/concept/actor/actor.py†L1-L35】【F:engine/src/tangl/story/concept/actor/role.py†L1-L80】【F:engine/src/tangl/story/concept/location/location.py†L1-L39】【F:engine/src/tangl/story/concept/location/setting.py†L1-L58】
* **Journal integration** – ``HasJournal`` wraps a bookmarked list of ``ContentFragment``
  objects, giving the story graph a first-class way to capture and replay rendered
  content as the VM advances.【F:engine/src/tangl/story/journal/has_journal.py†L1-L25】

Legacy Insights Worth Preserving
--------------------------------

* **Namespace affordances** – The legacy ``Scene`` assembled actors and blocks into a
  single lookup map and surfaced them via ``on_gather_context`` and ``__getattr__``
  overrides. This pattern keeps traversal-local resources addressable by logic and
  presentation code.【F:scratch/legacy_src/story/scene.py†L1-L58】
* **Actor demographic context** – ``NamespaceHandler`` strategies injected actor names
  (and potentially other demographic fields) into the scoped namespace, hinting at how
  resource nodes can publish facts to the VM without bespoke plumbing.【F:scratch/legacy_src/story/actor.py†L1-L37】
* **Casting and replication flows** – The legacy ``CastingHandler`` explored cloning and
  evolving actors when a role needed a fresh body, suggesting that dynamic edges should
  support template overrides, registry searches, and post-processing hooks inside the
  casting pipeline.【F:scratch/legacy_src/story/casting_handler.py†L1-L108】

Strategy for the Core/VM Runtime
--------------------------------

1. **Lean on ``TraversableGraph`` for the VM loop.** The existing traversal pipeline already
   sequences availability checks, effect application, rendering, and automatic continues.
   Scenes and blocks only need to register the right handlers to benefit from the shared
   cursor management and recursion into follow-up edges.【F:engine/src/tangl/core/graph_handlers/traversable.py†L1-L145】
2. **Treat structural nodes as VM entry points.** ``Story.enter`` should resolve an entry
   block/scene and rely on ``TraversableGraph.follow_edge`` to drive progression while
   journal entries accumulate via the shared journal interface.【F:engine/src/tangl/core/graph_handlers/traversable.py†L103-L145】【F:engine/src/tangl/story/journal/has_journal.py†L9-L25】
3. **Model resources as dynamic dependencies.** Continue the Role/Setting pattern for
   characters, locations, items, concepts, and relationships: placeholder nodes inherit
   ``DynamicEdge`` to resolve a successor via ref, template, or criteria, while the
   concrete resource nodes mix in ``Associating`` so they can enforce uniqueness and push
   context into the VM namespace.【F:engine/src/tangl/story/concept/actor/role.py†L37-L78】【F:engine/src/tangl/story/concept/location/setting.py†L12-L57】【F:engine/src/tangl/story/concept/actor/actor.py†L10-L35】
4. **Publish namespaces through ``on_gather_context``.** Scenes, blocks, and resources
   should register context providers that expose their affordances (actors, locations,
   items, relationship handles) to descendant nodes and rendering code, echoing the
   legacy scene child-map approach.【F:engine/src/tangl/story/structure/scene.py†L30-L63】【F:scratch/legacy_src/story/scene.py†L28-L43】
5. **Embed casting/scouting hooks in handler pipelines.** Roles and settings can expose
   explicit ``cast``/``scout`` tasks that are invoked during availability checks, letting
   the VM ensure prerequisites are resolved before traversal continues. Plugging the
   legacy cloning/template ideas into these handlers keeps the logic encapsulated while
   remaining compatible with ``TraversableEdge`` availability inheritance.【F:engine/src/tangl/story/structure/scene.py†L71-L87】【F:scratch/legacy_src/story/casting_handler.py†L23-L108】【F:engine/src/tangl/story/structure/action.py†L10-L35】

Next Steps
----------

* Formalize additional resource placeholders (items, relationships, concepts) by mirroring
  the Role/Setting mixin structure and registering them with the casting/scouting hooks.
* Expand namespace strategies so Actors, Locations, and future resource nodes publish the
  right facts (names, traits, states) automatically when attached to a scene or block.
* Define VM-facing controller services that translate traversal events (entry, choice
  selection, journal updates) into UI/view-model updates without bypassing the ``core``
  handler pipelines.
