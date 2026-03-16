# Hub Fanout and Sandbox Assembly

**Document Version:** 1.0  
**Status:** ACTIVE DESIGN — `vm.provision.Fanout` and `MenuBlock` planning-time action projection are implemented; refresh policy, call/return menu semantics, and sandbox scheduling layers remain deferred  
**Relevant layers:** `tangl.story.episode`, `tangl.story.fabula`, `tangl.vm.provision`, `world` / domain schedule facets

See also [SANDBOX_FANOUT_DESIGN.md](../../notes/SANDBOX_FANOUT_DESIGN.md) for the more
concrete sandbox-location interpretation of this pattern.
See also [MU_AFFORDANCES.md](../../notes/MU_AFFORDANCES.md) for relationship-bound
microconcepts that can ride on gathered providers without becoming graph peers.

---

## Problem Statement

Story hubs such as labs, taverns, city centers, dorm commons, or sandbox map
nodes should not require authors to hand-maintain a static menu of everything a
player can currently do there.

That static approach fails in exactly the cases StoryTangl should support well:

- a new affordance appears because a new role or event enters scope
- a choice should disappear because nothing interesting is currently behind it
- a choice should remain conceptually present but be unavailable for state or
  schedule reasons
- the same hub should behave differently across different runtime stories

The engine therefore needs a general way for a node to gather all currently
eligible providers from scope and project them into outgoing actions.

This document calls that pattern **hub fanout**.

---

## Core Idea

A hub is a traversable node that:

1. declares one or more selectors describing what kinds of providers it wants
2. gathers all eligible matches from scope
3. publishes those matches as affordances for the current node
4. projects the gathered affordances into dynamic actions or traversal edges

The hub itself owns very little business logic. Most authored meaning lives on
the gathered providers.

`MenuBlock` is the first concrete consumer of this pattern, but the pattern must
remain more general than menus.

---

## Definitions

### Hub

A node that assembles available actions from gathered providers.

Examples:

- "What can I do in the lab?"
- "Where do I want to go from the city center?"
- "Which currently available relationship scene should I pursue?"

### Provider

A template or instantiated node that can contribute an affordance to a hub.

Examples:

- a potion-mixing block
- a stable/training block
- an NPC interaction scene
- an exit or travel destination
- a scheduled event that is currently active

### Fanout

A selector-driven gather operation that returns **all** eligible providers,
rather than a single best provider.

This differs from ordinary dependency provisioning, which is concerned with
satisfying one requirement with one chosen provider.

### Projection

The process of turning gathered providers into dynamic affordances or actions.

Projection decides:

- action text
- whether the action is a simple edge or a call/return edge
- refresh and garbage-collection behavior
- optional grouping or ordering metadata

---

## Relationship to Existing Vocabulary

This model should reuse the existing provisioning vocabulary rather than invent
another parallel system.

- **Dependency** means "I need one provider."
- **Affordance** means "this provider should be offered here."
- **Fanout** means "gather all eligible providers and surface them as
  affordances."

In other words, a menu or sandbox hub should not be understood as a bespoke menu
engine. It should be understood as a node that gathers affordances from scope.

That framing keeps the mechanism reusable for future systems such as:

- sandbox location hubs
- party or roster management
- "all nearby actors with tag X"
- "all interactable devices in the workshop"
- "all currently active rumors in the tavern"

---

## Compile-Time vs Runtime Responsibilities

### Compiler

The compiler remains responsible only for deterministic authored structure:

- ordered blocks
- anonymous block labeling
- default-entry resolution
- bare-next inference when outgoing intent exists but no successor is listed
- preservation of authored fanout metadata on hub payloads

The compiler does **not** decide which gathered providers currently exist.

### Materializer / VM

Runtime gathering belongs in materialization and provisioning:

- determine current scope groups
- gather eligible providers
- publish affordances
- synthesize dynamic actions
- clear and rebuild dynamic actions when policy requires it

### World / Domain Schedule

The world may expose a default schedule of people, places, events, and other
providers, but the runtime story graph owns its own instantiated state.

That distinction matters:

- the world may know a default daily schedule for a violinist NPC
- one particular story may instantiate a story-specific romantic-interest
  schedule derived from that default
- many runtime stories may coexist at different times, places, and narrative
  states even when they share the same world

The world therefore provides **default scheduling knowledge**, not the full
authoritative state of every active story run.

Layered schedules and story-specific overlays are important, but they are
deferred here in favor of defining the basic hub/fanout algorithms first.

---

## Scope Model

Fanout must remain scope-aware.

Likely scope inputs include:

- current block lineage
- current scene or container
- world-provided template scope groups
- runtime entity groups
- schedule/time/location overlays

Examples:

- gather only peer blocks in the current scene
- gather all currently present NPC interactions at the current location
- gather all travel exits from this sandbox node
- gather all "lab activity" providers admitted to this context

The important rule is that labels are optional authoring conveniences, not the
only way something becomes reachable. A provider may be gathered by:

- identifier
- tags
- kind
- scope
- availability predicates
- schedule predicates

---

## Refresh Policies

Not every hub should rebuild its dynamic options on every visit.

The design should support at least these policies:

- `build_once`
  Use when the gathered option set is effectively stable for the relevant
  lifetime, such as hallway doors within one scene.

- `refresh_on_entry`
  Rebuild every time the player enters the hub. This is the likely default for
  reactive sandbox hubs such as a lab or tavern.

- `refresh_on_update`
  Rebuild whenever the broader update/provision cycle runs. This is the most
  reactive and should be used sparingly.

The refresh policy controls dynamic action garbage collection as well as
re-gathering.

---

## Projection Rules

Projection from gathered provider to action should be explicit and lightweight.

The minimal projection contract is:

- `source`: the hub where the choice is presented
- `target`: the gathered provider node
- action text defaults from provider metadata
- action edge tags mark it as dynamic/fanout-generated

Useful provider-side metadata includes:

- `action_text`
- `menu_text`
- indicator text or other UI hints
- call/return hints for subroutine-style interactions
- ordering/grouping hints

Availability should remain source-centered at choice time, while target
eligibility is handled during gather/filter. If the target needs extra gating,
that gating should participate in provider eligibility rather than being hidden
inside ambiguous edge behavior.

---

## Sandbox as a Fanout Consumer

The motivating sandbox case is a location hub that assembles itself from:

- currently available activities
- present roles/NPC interactions
- local events
- reachable exits or travel options

This avoids the classic brittle "city center menu" problem where the author must
manually keep the hub synchronized with everything interesting that might happen
there.

Instead:

- providers declare themselves through templates, tags, scope, and availability
- time/location/schedule determine which providers are currently eligible
- the hub gathers only the interesting currently valid affordances
- the hub projects them into actions

This enables more reader-friendly behavior such as:

- never forcing the player to hunt for the exact correct place/time click
- showing only currently interesting destinations
- allowing the scheduler to move interesting content toward the reader's chosen
  direction rather than rigidly locking progress behind one exact route

---

## Re-entrant Providers and Cycle Instances

Hub fanout becomes especially useful when the gathered providers are
**re-entrant** rather than one-shot destinations.

Examples:

- repeatable activities at a location hub
- minigame or challenge blocks that loop until terminal conditions resolve
- reusable interaction scenes that may be invoked from several hubs
- short subgraph patterns that compress a recurring "do thing -> resolve ->
  return" structure

The important design question is not merely "can this be revisited?" but **what
kind of revisit it is**:

- **Reuse the same provider instance**
  Appropriate when the provider's local state is itself the thing being
  revisited, as with a persistent challenge block or a stable location
  activity.

- **Call into a provider and return**
  Appropriate when the provider behaves like a subroutine and should not need to
  know which hub invoked it. In that case the hub projects a call/return-style
  affordance and the VM return stack carries the re-entry semantics.

- **Instantiate a fresh cycle instance**
  Appropriate when each visit should leave an auditable, separately identified
  trail in the journal or replay history rather than folding all visits into one
  provider node. This is the more expensive but more explicit option.

This should be understood as a general traversal principle, not a sandbox-only
quirk. Hubs, activity loops, and game blocks are all consumers of the same
underlying pattern: a node projects one or more re-entrant affordances whose
result eventually returns the cursor to a recognizable continuation point.

---

## Minimal Data Shape

The first-pass runtime payload for a hub should preserve data roughly like:

```python
class HubFanoutConfig:
    selectors: list[SelectorLike]
    scope_policy: str
    refresh_policy: str
    projection_policy: str
```

`MenuBlock` may own the first concrete fields, but the data model should be
named and structured so that later sandbox hubs, roster hubs, or other fanout
consumers can reuse it.

Likewise, a gathered affordance record may eventually want to preserve:

- provider uid
- provider label
- selector origin
- projection metadata
- dynamic edge ids created from it

---

## Non-Goals

This design note does **not** attempt to define:

- full layered schedule instancing for world vs. story-specific schedules
- complete sandbox map or travel APIs
- final author-facing YAML syntax for selectors or hub declarations
- a final persistence/replay representation for fanout affordance caches

Those are important follow-ups, but they should build on the simpler fanout
machinery rather than precede it.

---

## Implementation Direction

Near-term engine work should proceed in this order:

1. Preserve hub/fanout metadata on compiled episode payloads.
2. Add generic fanout gathering in the provisioning/runtime layer.
3. Represent gathered providers as affordances attached to the caller/hub.
4. Add a projection step that turns gathered affordances into dynamic actions.
5. Add explicit refresh-policy handling and stale dynamic-action cleanup.
6. Reuse the same mechanism for sandbox hubs, not just menus.

This keeps the mechanism generic while still delivering immediate value through
`MenuBlock`.

---

## Current Implementation Status

As of March 2026:

- compile-time entry resolution, anonymous blocks, and bare-next inference are
  implemented on the v38 story compiler surface
- a lightweight `MenuBlock` runtime payload exists so hub metadata can survive
  compilation
- full runtime fanout gathering and affordance projection are **not** yet
  implemented on the current v38 surface

So the architecture described here is partially present, but the core fanout
runtime still needs to be built.

---

## Related

- `docs/src/design/story/menu_block.md`
- `docs/src/design/traversal/ENTRY_RESOLUTION.md`
- `docs/src/design/planning/PROVISIONING.md`
- `tangl.story.episode.MenuBlock`
- `tangl.story.fabula.StoryCompiler`
- `tangl.vm.provision.Requirement`
- `tangl.vm.provision.Affordance`
- `docs/src/notes/SANDBOX_FANOUT_DESIGN.md`
