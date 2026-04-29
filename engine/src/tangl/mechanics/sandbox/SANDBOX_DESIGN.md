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
- `Action`/`TraversableEdge` can carry edge-local availability and effects,
  which gives generated choices their own activation conditions and mutations.
- `TraversableEdge.return_phase` supports jump-and-return interactions.
- Target-node availability expresses entry gating.
- Namespace gathering exposes caller, ancestor, role, setting, graph, and world
  locals to predicates and render.

The sandbox package should add reusable rules and schedule/time vocabulary, not
a second VM.

### General Contribution Pattern

Affordance projection is a general StoryTangl pattern, not a sandbox-only
mechanism.

At the VM/story boundary, containers already push scoped facts into namespace
and authorities, while nodes, edges, fragments, and handlers pull on those facts
through dependencies, predicates, render context, and phase hooks. A scene that
publishes roles, settings, stage props, or assets is already turning parent
context into child affordances.

Sandbox specializes that broader push/pull pattern for location-centered
exploration:

- location links become movement choices;
- present assets become take/read choices;
- carried assets become drop/use/light choices;
- fixtures become place-bound interactions;
- schedules and presence become time/location-sensitive events;
- visibility rules become projection filters over journal and local choices.

The important runtime truth is the contribution surface, not the authoring
category. Entity categories such as location, asset, fixture, actor, companion,
weather, or debug overlay remain useful authoring vocabulary. At runtime, the
question is: what does this scoped concept contribute, suppress, or expose for
the current phase?

For now sandbox keeps this as local mechanics code. Promotion candidates, once
a second non-sandbox consumer appears:

- a general provenance/receipt shape for phase outputs;
- story-level projection filters over journal and choices;
- a broader scoped contribution provider that can return actions, journal
  fragments, suppressions, or schedules.

Do not promote location-specific vocabulary such as exits, lockables, darkness,
or player inventory into VM. Those are sandbox/story-mechanics specializations
of the broader contribution pattern.

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
- optional `SandboxExit` values for per-link text overrides
- `sandbox_scope`: optional shared scope label
- held assets through the story-level `HasAssets` facet
- location namespace such as `current_location`

Movement is not modeled as exit availability. Linked targets use normal entry
availability. If a linked location is currently unavailable, the generated
movement choice is unavailable for the same reason any ordinary StoryTangl
choice is unavailable.

Link keys are author/import vocabulary, not graph semantics. The sandbox
projector normalizes common aliases (`n`, `s`, `e`, `w`, `u`, `d`, `in`, `out`)
into canonical `ui_hints["direction"]` values, preserves the original key as
`ui_hints["raw_direction"]`, and still accepts the compact
`{"n": "forest"}` table form. A structured `SandboxExit(target="building",
text="Enter the building")` can override display text without changing the
underlying edge model.

Structured exits can also express two common compressed-IF cases without a new
engine primitive:

```yaml
slit_streambed:
  exits:
    down: { kind: message, journal: "You don't fit through a two-inch slit!" }
outside_grate:
  exits:
    down: { through: grate, to: below_grate }
```

A message exit is a self-loop action with selected-action journal text. A
`through` exit is a normal movement action whose edge availability checks that
the named local fixture is open.

The base sandbox does not infer reverse links. Colossal Cave-style maps often
contain one-way passages, loops, blocked returns, and asymmetric text. A future
`GridSandbox` specialization can intentionally provide symmetric adjacency
defaults for RPG-map or tile-map travel.

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
- openable/lockable local fixtures

Sandbox choices can distinguish "offer this action" from "this action is
currently activatable" without new sandbox state. For example, a locked door
or nearby key can project `Unlock door` while the door is locked. The action's
edge-local availability can require `sandbox_has_key("key")`, and its
edge-local effects can unlock the target context before it journals. If the
key is missing, the choice remains a normal unavailable `ChoiceFragment`; if
the key is present, the action can be a self-loop with a one-shot
`journal_text` such as "The key turns with a click. The door unlocks."

The current runtime convention is intentionally narrow:

- action availability is evaluated against the source/predecessor scope;
- action effects apply to the target/successor scope after cursor movement;
- re-entrant actions work because source and target are the same location.

That covers "unlock the door here and journal here" and "enter the next scene
with `attacked_from_above = True`." It does not yet provide a source-side
departure effect for "leave the door behind you unlocked." If that need becomes
common, add an explicit departure-effect surface rather than overloading the
arrival-relative `effects` list.

For simple source-side state, selected-edge effect namespaces expose endpoint
objects as `_predecessor` / `_p` and `_successor` / `_s`. This is enough for
an arrival-relative action to intentionally update the place it came from:

```python
_p.locals["door_locked"] = False
```

Do not treat this as a predecessor namespace overlay. Component-injected helper
functions from the predecessor scope are future work if we find real repeated
need for them.

The first package spike implements linked-location movement, wait, selectable
scheduled events, concept-provider events, local lockable unlock choices, and a
minimal asset-presence projection. It also introduces `SandboxScope` for
scope-level wait/event/presence donation and a lightweight `player_assets`
holder.

The asset projection follows the same rule as movement projection: the current
hub donates choices from locally declared tables/state. Location-held assets can
project `Take X` and `Read X`; player-held assets can project `Drop X`; carried
assets can satisfy generated action availability such as `Unlock grate`.
Take/drop effects use the story asset transaction manager, not ad hoc locals.
This is enough for the toy Adventure subset's keys, lamp, leaflet, and
treasures. Richer object ontologies, containers/supporters, quantities, actor
inventory, and parser/client matching remain later slices.

Local fixture projection is similarly narrow. `SandboxLockable` remains the
first-spike name, but it now carries enough fixture state for the Adventure
grate pattern: locked/unlocked, open/closed, openable, key, and journal text.
Locked fixtures project `Unlock X`; openable fixtures project `Open X` or
`Close X`; `through` exits can require that fixture to be open. This is enough
for the key/grate demo without promoting a full fixture ontology yet.

### Visibility Projection

Darkness is not primarily a movement constraint. It is a projection rule over
what the location can truthfully reveal.

Adventure-style darkness affects:

- location journal detail;
- visible local assets and fixture affordances;
- which carried tools remain actionable;
- later parser noun resolution, diagnostics, and movement risk.

The first implementation keeps that shape narrow. A `SandboxScope` or
`SandboxLocation` can carry `SandboxVisibilityRule`s. The default darkness rule
is active when the current location is not lit and the player has no lit light
source:

```text
not sandbox_location_lit
not sandbox_has_lit_light_source()
```

When active, it produces a `SandboxProjectionState` that can suppress the
location description, suppress local asset actions, suppress local fixture
actions, and substitute a journal fragment such as "It is now pitch dark."

This is intentionally a projection filter, not a new action model. The location
still journals through normal fragments, and the generated actions are still
ordinary `Action` edges. Carried light-source assets continue to project
turn-on/turn-off self-loop choices while darkness is active, so "lamp restores
room detail" is modeled as asset state changing the projection state on the
next render.

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
activation; it is projected as a normal `Action` with `return_phase=PLANNING`,
so when the target scene finishes, the frame returns to the originating
location and reprojects dynamic choices before journaling that location.
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

### Research Direction: Semantic Story Compression

A faithful source port is not the primary goal of the Adventure sandbox work.
The more interesting goal is semantic compression: recovering the playable
shape and feel of a legacy interactive story while factoring repeated behavior
into reusable sandbox capabilities and narrow world-authority handlers.

In this framing, the original source is a dense artifact containing room text,
parser vocabulary, object facts, procedural special cases, scoring logic, and
historical implementation constraints. The StoryTangl port does not need to
preserve those constraints bit-for-bit. It should preserve the player's
experienced affordance structure: where the player can go, what they can
notice, what they can carry, what gates progress, what hazards matter, and what
kinds of actions the world invites.

The compact IR should therefore describe world facts and trait-bearing entities
rather than copy behavior into every object declaration. Traits and components
are semantic handles that sandbox handlers and world authorities can recognize:

```yaml
assets:
  brass_lamp:
    name: brass lamp
    traits: [portable, switchable, provides_light, requires_charge]
    initial: { location: building }
    charge: 330

fixtures:
  grate:
    name: steel grate
    traits: [fixture, door, openable, lockable]
    key: keys
    connects: { outside_grate: below_grate }
```

Here `portable`, `switchable`, `provides_light`, `requires_charge`,
`openable`, and `lockable` are not bespoke mini-programs copied into each
object. They are invitations for generic sandbox contributors or
world-specific authority handlers to publish take/drop, light, timer,
open/close, lock/unlock, warning, scoring, or diagnostic affordances.

This keeps the authoring surface small:

- locations and exits as data;
- assets, fixtures, mobs, and world concepts as trait-bearing entities;
- common behavior generated from reusable traits;
- unusual behavior supplied by narrow world-authority handlers;
- parser and choice UIs rendered from the same projected choices.

The compression claim is not that every original command response survives.
The claim is that most of the recognizable story/game morphology survives after
factoring the source into reusable semantic patterns.

Possible measurements:

- source LOC or word count vs. compact IR plus handler LOC;
- percentage of rooms, exits, items, and fixtures represented;
- percentage of walkthrough actions supported;
- percentage of core puzzle dependencies represented;
- subjective feel coverage from playtesting;
- number of reusable sandbox capabilities extracted.

This positions StoryTangl as more than an IF interchange format. It becomes a
tool for identifying, compressing, and reusing the semantic structures of
interactive stories.

The current hand-compiled demo fixture is intentionally tiny. It normalizes the
high-level Adventure slice into locations, simple/string exits, message exits,
fixture-gated exits, portable assets, a light source, and one shared openable
lockable grate. The walkthrough exercises:

```text
road -> building
take keys
take brass_lamp
turn on brass_lamp
road -> valley -> slit_streambed -> outside_grate
unlock grate
open grate
down -> below_grate
west -> cobble_crawl
```

The point is not that the schema is final. The point is to keep an executable
pressure fixture while negotiating which schema choices are authoring sugar,
which are generic sandbox traits, and which require world-specific authorities.

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
inside_cave.light = false
```

Objects:

- `keys`: portable, initially in `building`
- `lamp`: portable, initially in `building`
- `leaflet`: readable, initially in `building`
- `grate`: lockable/openable, present at `cave_entrance`

Entry availability:

```text
inside_cave.available = grate_open
```

Visibility:

```text
scope.visibility_rules = [darkness]
darkness.when = not location.light and not player_has_lit_light_source
darkness.suppress_location_description = true
darkness.suppress_asset_affordances = true
darkness.suppress_fixture_affordances = true
```

The player can enter `inside_cave` after opening the grate, but without a lit
lamp the journal says only that it is pitch dark and local object choices are
hidden. The carried lamp still offers `Turn on lamp`; after it is lit, normal
room text and local object affordances return.

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
- fixture-gated exits stay unavailable until the fixture is opened
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

Colossal Cave and Zork should layer on top of this model by extracting compact
world facts:

- locations and links
- object placement
- object state
- object traits/components
- schedule/presence rules
- generated choice rules
- diagnostic response rules
- scoring rules
- original text artifacts

Ports should not require a new engine or a giant faithful reimplementation of
every source routine. They may require richer data extraction, more projection
rules, world-specific authority handlers, and transient actor support for
entities such as pirates, trolls, and grues.
