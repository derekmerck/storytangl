Story Graph Concepts and VM Strategy
====================================

This note distills the useful ideas from the existing ``tangl.story`` modules and the
legacy implementations under ``scratch/legacy_src/story`` to clarify how episodic
narrative structures should be represented on top of the modern ``core`` runtime and
story virtual machine (VM) traversal loop.

Current Story Building Blocks
-----------------------------

* **World assembly** – ``World`` orchestrates the managers required to build a story
  graph. ``create_story`` materializes actors, locations, scenes, and blocks from the
  ``ScriptManager`` output, wiring ``Frame`` as the graph cursor when the story is ready
  to run.【F:engine/src/tangl/story/fabula/world.py†L1-L173】【F:engine/src/tangl/story/fabula/script_manager.py†L17-L146】
* **Structural traversal nodes** – Blocks and Scenes inherit traversal helpers so they
  can participate directly in the VM pipeline: blocks render content/effects and expose
  choices, while scenes coordinate blocks, roles, and settings through namespace hooks.【F:engine/src/tangl/story/episode/block.py†L1-L109】【F:engine/src/tangl/story/episode/scene.py†L1-L120】
  ``Action`` edges specialize :class:`~tangl.vm.frame.ChoiceEdge` so successors can be
  linked lazily via script references.【F:engine/src/tangl/story/episode/action.py†L1-L44】
* **Resource concepts** – Actors, locations, and Role/Setting placeholders are
  implemented as graph-aware nodes. Roles cast actors on demand and settings scout
  locations, establishing a clear pattern for other affordance/resource relationships
  (items, concepts, achievements, etc.).【F:engine/src/tangl/story/concepts/actor/actor.py†L1-L89】【F:engine/src/tangl/story/concepts/actor/role.py†L1-L120】【F:engine/src/tangl/story/concepts/location/location.py†L1-L63】【F:engine/src/tangl/story/concepts/location/setting.py†L1-L78】
* **Journal integration** – Story output is generated through behavior hooks. Blocks
  register an ``on_journal`` handler that renders inline content, child concepts, and
  interactive choice menus into ``BaseFragment`` records consumed by ledgers.【F:engine/src/tangl/story/episode/block.py†L69-L162】【F:engine/src/tangl/core/__init__.py†L33-L58】

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

1. **Lean on the ledger/frame loop.** ``Ledger`` seeds ``Frame`` instances with behavior
   layers, so blocks/scenes only need to register the right handlers to benefit from the
   shared cursor management, receipts, and journaling pipeline.【F:engine/src/tangl/vm/ledger.py†L1-L118】【F:engine/src/tangl/vm/frame.py†L23-L200】
2. **Treat structural nodes as VM entry points.** Scenes resolve entry blocks and project
   dependencies into namespaces, while blocks assemble choice edges for the frame to
   evaluate. Both surfaces are activated through the shared behavior dispatch instead of
   bespoke traversal stacks.【F:engine/src/tangl/story/episode/scene.py†L17-L120】【F:engine/src/tangl/story/episode/block.py†L1-L162】【F:engine/src/tangl/vm/dispatch/__init__.py†L1-L21】
3. **Model resources as dynamic dependencies.** Continue the Role/Setting pattern for
   characters, locations, items, concepts, and relationships: placeholder nodes inherit
   script-friendly fields (refs, templates, criteria) while concrete resources enforce
   uniqueness and push context into namespaces.【F:engine/src/tangl/story/concepts/actor/role.py†L37-L120】【F:engine/src/tangl/story/concepts/location/setting.py†L12-L78】【F:engine/src/tangl/story/concepts/actor/actor.py†L10-L89】
4. **Publish namespaces through behavior hooks.** Scenes, blocks, and resources register
   ``on_get_ns`` handlers so actors, locations, and other affordances are discoverable by
   downstream renderers without hand-rolled context plumbing.【F:engine/src/tangl/story/episode/scene.py†L63-L105】【F:engine/src/tangl/vm/dispatch/__init__.py†L6-L21】【F:scratch/legacy_src/story/scene.py†L28-L43】
5. **Embed casting/scouting hooks in handler pipelines.** Roles and settings can expose
   explicit behaviors (availability checks, provisioning) invoked during planning, letting
   the VM ensure prerequisites are resolved before traversal continues. Plugging the
   legacy cloning/template ideas into these handlers keeps the logic encapsulated while
   remaining compatible with ``ChoiceEdge`` availability inheritance.【F:engine/src/tangl/story/concepts/actor/role.py†L75-L120】【F:scratch/legacy_src/story/casting_handler.py†L23-L108】【F:engine/src/tangl/story/episode/action.py†L1-L44】

Next Steps
----------

* Formalize additional resource placeholders (items, relationships, concepts) by mirroring
  the Role/Setting mixin structure and registering them with the casting/scouting hooks.
* Expand namespace strategies so Actors, Locations, and future resource nodes publish the
  right facts (names, traits, states) automatically when attached to a scene or block.
* Define VM-facing controller services that translate traversal events (entry, choice
  selection, journal updates) into UI/view-model updates without bypassing the ``core``
  handler pipelines.
