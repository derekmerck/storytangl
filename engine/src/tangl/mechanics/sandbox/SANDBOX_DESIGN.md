# Sandbox Mechanics Design

**Status:** ASPIRATIONAL DESIGN NOTE + FIRST SPIKE CONTRACT
**Scope:** `tangl.mechanics.sandbox`
**Prior art:** `docs/src/notes/SANDBOX_FANOUT_DESIGN.md`,
`scratch/mechanics/sandbox/*`

---

## Core Thesis

A StoryTangl sandbox is not a separate interaction model. It is a
chapter-like scope of scene-locations that dynamically projects ordinary
StoryTangl choices from location links, present entities, carried inventory,
actors, world time, schedules, and local rules.

The generated choices are normal `Action` edges. They use normal target
availability, effects, call/return, journal fragments, choice diagnostics,
ledger history, and replay.

Parser UI is optional. It does not create actions. It only maps user text to
the closest current choice, diagnostic choice, or no match.

---

## Relationship To Existing Architecture

The current v38 architecture already has most of the sandbox substrate:

- `MenuBlock` is the dynamic hub shape.
- `Fanout` discovers providers.
- Planning-time handlers project dynamic `Action` edges.
- `ChoiceFragment` carries availability, blockers, accepted payload shape, and
  UI hints.
- `TraversableEdge.return_phase` supports jump-and-return interactions.
- Target-node availability expresses entry gating.
- Namespace gathering exposes caller, ancestor, role, setting, graph, and world
  locals to predicates and render.

The sandbox package should add reusable rules and schedule/time vocabulary, not
a second VM.

---

## What Sandbox Adds

### Sandbox Scope

A sandbox scope is a bounded group of related scene-locations. It behaves like a
chapter: locations inside it share namespace, time, schedules, and projection
rules.

`SandboxScope` is now the first explicit version of that idea. It is a
chapter-like ancestor that donates sandbox rules to child locations through the
same ancestor namespace/hierarchy pattern that scenes already use for child
blocks.

Current scope donations:

- shared `world_turn`
- wait defaults
- selectable scheduled events
- scheduled presence
- concept-provider events

### Sandbox Location

A sandbox location is a visitable scene-location hub. It is cursor-addressable
like a `Block` and place-like for movement and presence.

For now, `SandboxLocation` is a thin `MenuBlock` facade with:

- `links`: direction to target-location reference
- `sandbox_scope`: optional shared scope label
- location namespace such as `current_location`

Movement is not modeled as exit availability. Linked targets use normal entry
availability. If a linked location is currently unavailable, the generated
movement choice is unavailable for the same reason any ordinary StoryTangl
choice is unavailable.

### Projection Rules

Sandbox projection rules run during planning and create ordinary dynamic
`Action` edges.

Initial rule families:

- linked-location movement
- scope/global commands such as look, wait, inventory, score
- scheduled events
- present actor/object actions
- inventory-carried actions
- inventory plus local target combinations

The first package spike implements linked-location movement, wait, and
selectable scheduled events. It also introduces `SandboxScope` for scope-level
wait/event/presence donation. Object, actor, inventory, forced-event redirect,
and parser/client matching rules remain later slices.

The generated wait action intentionally mirrors the `tangl.mechanics.games`
self-loop move pattern. Both use an ordinary dynamic `Action`, a self-loop
successor, selected payload during UPDATE, and the normal ledger/journal
pipeline. The syntax can vary by mechanic family, but the re-entrant provider
pattern is shared.

Selectable and triggered scheduled events can also use existing call/return and
visit history directly. `activation` is the authored timing hint copied from
story actions: unset means a normal visible choice, `first` maps to a PREREQS
redirect before the current node journals, and `last` maps to a POSTREQS
continue after the current node journals. `return_to_location` is orthogonal to
activation; it is projected as a normal `Action` with `return_phase=UPDATE`, so
when the target scene finishes, the frame returns to the originating location.
A `once` event is not projected after its target has generic VM `_visited`
state. This covers scope-level "first time in this sandbox" beats without a
sandbox ledger or custom flag system: donate the same once-only event to every
child location, target a shared orientation block, trigger it on entry, and let
target visit history suppress future projections.

Concepts can originate events too. The sandbox projector discovers providers
from the gathered namespace and calls `get_sandbox_events(caller, ctx, ns)` on
providers that opt in. This keeps the relationship simple: actors, locations,
settings, roles, and token assets remain normal concept providers, but can
donate normal sandbox `ScheduledEvent`s when their local type or instance state
notices the right surrounding namespace.

### World Time And Schedule

Time and schedule are the main genuinely new vocabulary.

The old scratch sandbox work centered on world turn, world time, mobile actors,
forced events, and selectable events. In v38 those become:

- `world_turn` in locals
- derived `WorldTime`
- explicit `advance_world_turn(...)`
- schedule matching against time, location, and optional presence
- forced scheduled events as ordinary redirects
- selectable scheduled events as ordinary generated choices

### Parser As Client Adapter

Parser IF looks like a different interaction model because the menu is hidden.
Architecturally it is still choice selection.

The parser maps input to a current choice:

```text
player text -> current Action edge or no match
```

Some generated choices can be diagnostic:

```text
"use sword on door" -> cannot_use_item_on_target -> journal response -> return
```

That response feels like parser failure, but it is still normal StoryTangl
traversal.

### Research Direction: Parser Input As Affordance-Field Rasterization

Traditional parser IF is input-order. It starts with the player command and
casts it into the world, asking which object/action it intersects. This is
roughly ray tracing: the command is the ray, grammar provides the ray model,
and world state is queried after syntax has been inferred.

Sandbox can invert that direction into an object-order pipeline. The current
world state first projects meaningful affordances into an interaction buffer:
movement actions, object actions, inventory actions, hidden parser-only
actions, unavailable-but-recognizable actions, diagnostic responses, and global
commands. Each projected affordance contributes command signatures and match
metadata. The player command then samples this affordance field.

Resolution becomes a compositing problem:

- choose the strongest affordance fragment;
- report ambiguity when fragments overlap;
- report unavailability when the best match has unsatisfied requirements;
- report unknown input when nothing covers the command.

This reframes parser IF as a renderer over state-generated affordances rather
than an interpreter that owns semantic meaning. The world decides what can be
meant; the parser chooses among projected meanings.

This is not part of the first sandbox implementation. It is a useful research
frame for later parser-like clients, debug affordance views, and legacy IF
imports where we want parser play to remain a UI projection over ordinary
StoryTangl choices.

---

## What Is Out Of Scope For The First Spike

- A parser engine.
- A separate action, attempt, resolution, or ledger model.
- A full parser-IF object ontology.
- Zork-grade ambiguity, quantities, containers, supporters, daemons, or NPC
  routines.
- Importing Colossal Cave or Zork before the toy sandbox proves the shape.

Ambiguity and payloads can come later through `Action.accepts` and
`choice_payload`.

---

## Four-Room Toy Example

Scope: `tiny_cave_scope`

Locations:

- `road`
- `building`
- `cave_entrance`
- `inside_cave`

Links:

```text
road.east -> building
road.west -> cave_entrance
building.west -> road
cave_entrance.east -> road
cave_entrance.down -> inside_cave
inside_cave.up -> cave_entrance
```

State:

```text
world_turn = 0
inventory = []
grate_locked = true
grate_open = false
lamp_lit = false
```

Objects:

- `keys`: portable, initially in `building`
- `lamp`: portable, initially in `building`
- `leaflet`: readable, initially in `building`
- `grate`: lockable/openable, present at `cave_entrance`

Entry availability:

```text
inside_cave.available = grate_open and lamp_lit
```

Scheduled event:

At `world_turn == 2`, if the player is at `road`, a traveler event appears.
If forced, it is an ordinary redirect. If selectable, it is an ordinary dynamic
choice.

Scope-level once event:

The scope donates `Take in your surroundings` to all four locations. The event
targets an `orientation` block, returns to the originating location, and is
projected only while `orientation` has not been visited. Selecting it from any
location marks the shared target visited, so the event disappears everywhere in
the scope.

First acceptance tests:

- movement choices are generated from `links`
- target entry availability gates `inside_cave`
- `wait` advances `world_turn`
- a selectable scheduled event matches only at the requested time and location
- a scope-level once event can be selected from any location, return, and then
  disappear everywhere
- a role/provider concept can donate a sandbox event through the gathered
  namespace
- all output remains normal journal fragments and `ChoiceFragment`s
- replay of the same choices reaches the same state

---

## Legacy IF Import Direction

Colossal Cave and Zork should layer on top of this model by extracting tables:

- locations and links
- object placement
- object state
- schedule/presence rules
- generated choice rules
- diagnostic response rules
- scoring rules
- original text artifacts

Ports should not require a new engine. They may require richer data extraction,
more projection rules, and transient actor support for entities such as pirates,
trolls, and grues.
