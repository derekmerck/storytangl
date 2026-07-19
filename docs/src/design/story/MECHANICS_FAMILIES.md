Mechanics Families
==================

**Status:** 🟡 ACTIVE ARCHITECTURE NOTE  
**Layer:** author-layer capability families under `tangl.mechanics`

---

## Core Idea

`tangl.mechanics` is not a bucket of miscellaneous game systems.
It is a library of **reusable consequence grammars** plus the semantic,
projection, and writeback bindings that make those grammars story-capable.

Mechanics remain grouped by broad **families** at the package level:

- `games`
- `progression`
- `assembly`
- `demographics`
- `presence`
- later: `sandbox`, `credentials`, other world- or plugin-provided families

Within each family, we reason about implementation through a common internal
layer model rather than by forcing a filesystem reorganization up front.

---

## Internal Layers

Each mechanic family should describe which of these layers it implements and
which are intentionally absent:

### 1. Kernel

Pure deterministic rule logic.

- no story-specific prose
- no media delivery concerns
- no hidden global state
- no implicit randomness

Examples:

- matchup algebra
- slot or budget validation
- stat delta math
- option-generation policy

### 2. Domain

Semantic bindings that map abstract slots or operations onto a themed ontology.

- vocabularies
- YAML catalogs
- semantic labels
- rarity or affiliation systems
- world-specific configuration overlays

### 3. Runtime

The live artifacts used while resolving a mechanic instance.

Typical shapes:

- spec
- state
- offer / option
- intent
- resolution record
- receipt / audit artifact

### 4. Render

Projection from runtime artifacts into narrative or media-facing outputs.

- journal fragments
- media specs
- UI-facing choice text
- concise logs versus lush recap styles

### 5. Writeback

Explicit consequence application to persistent story state.

- relationship shifts
- deck or inventory edits
- world-state toggles
- reputation or progression changes
- follow-on affordances

### 6. Facade

Thin author-facing surfaces that expose the family ergonomically.

- `HasGame`
- `HasDemographics`
- `HasLook`
- future `HasOutfit`, `HasCredentials`, etc.

The facade should stay thin. The real logic belongs in kernel, runtime, render,
and writeback layers.

---

## Review Lens

For this mechanics resurrection pass, and likely for the wider engine later,
every family should be reviewable through four questions:

### Shape

What artifacts exist at rest?

- specs
- state models
- offers
- intents
- records
- fragments
- resources

### Behavior

What transitions or computations occur?

- planning
- option generation
- resolution
- projection
- writeback

### Attachment Points

Where does the family plug into the system?

- compiler or materializer
- namespace contribution
- VM phase hooks
- media adapters
- orchestrator or service response shaping

### Appearance

What does the family look like when it acts?

- prose
- journal fragments
- media fragments
- DTOs
- player-facing choices

This rubric is intentionally broader than mechanics. It is a useful way to
describe StoryTangl subsystems in general:

- what shape does it have,
- what does it do,
- where does it attach,
- what does it look like when it does it.

---

## Support and Promotion Criteria

A **fully supported mechanic family** should satisfy all of the following:

1. It declares which internal layers it implements.
2. It can be described clearly through the review lens above.
3. Randomness is explicit and controllable.
4. Writeback is explicit rather than hidden inside opaque side effects.
5. Projection is separable from kernel and writeback.
6. It does not depend on `scratch/`.
7. It does not depend on example-only internals from another active family.

Not every current family is fully supported yet. During this pass we use a
broader classification:

- **Reference**: strongest current integrated example
- **Foundation**: reusable kernel/runtime or domain surface, not fully integrated
- **Redesign**: valuable intent, but current shape should not be extended blindly
- **Incubating**: active design direction, not yet engine contract
- **Archive**: idea inventory only

---

## Current Family Matrix

### `games` — Reference

Why it stays:

- already spans kernel, runtime, projection, and limited writeback
- already attaches to VM planning, update, journal, and namespace hooks
- already gives us a thin author-facing `HasGame` facade

Review lens:

- **Shape:** game state, move payloads, round records, journal fragments
- **Behavior:** move provisioning, resolution, terminal-state routing
- **Attachment points:** VM phase handlers plus namespace injection
- **Appearance:** interactive choices and round recap fragments

### `progression` — Foundation

Why it stays:

- strong kernel and runtime primitives
- clear stat system, task, handler, and outcome surfaces

Current gap:

- render and writeback are still thinner than the family wants long-term

Review lens:

- **Shape:** stat systems, stats, tasks, effects, contexts
- **Behavior:** competency math, modifier aggregation, task resolution
- **Attachment points:** currently mostly direct library use
- **Appearance:** still modest and mostly caller-defined

### `assembly` — Foundation

Why it stays:

- it is a useful constrained optimization kernel, not an incidental example
- slot and budget algebra are reusable across outfits, vehicles, credentials,
  and other authored loadouts

Review lens:

- **Shape:** slots, groups, budgets, slotted containers
- **Behavior:** assignment, validation, resource constraint checking
- **Attachment points:** facet-style embedded containers on entities
- **Appearance:** generally projected by higher-level families

### `demographics` — Foundation, first modernization spike

Why it stays:

- useful domain/profile facet
- valuable for actor identity, namespace publication, and future projection

Current gap:

- historically written as a standalone generator library rather than a v38
  mechanics facet

Review lens:

- **Shape:** demographic profiles, regions, countries, subtypes, name banks
- **Behavior:** controlled sampling and profile construction
- **Attachment points:** actor composition and namespace export
- **Appearance:** naming and identity metadata today; richer prose/media later

### `presence/wearable` and `presence/ornaments` — Foundation

Why they stay:

- they are reusable presence/runtime primitives
- they feed future look, outfit, and presentation families

Review lens:

- **Shape:** wearable tokens, ornament entities, states, coverage regions
- **Behavior:** state transitions and visibility or coverage reasoning
- **Attachment points:** future loadout and appearance surfaces
- **Appearance:** item or body-detail description

### `presence/look` — Redesign

Why it stays, but under redesign:

- the intended appearance layer is strong
- the current implementation still needs broader render/media intersections
  cleaned up even after the first facade rescue

Required direction:

- keep the new deterministic description surface and structured media payload
  contract, then continue separating richer render/media intersections from the
  body-trait profile itself
- stop depending on example-only assembly code
- keep it thin enough to act as a facade over better runtime and projection
  surfaces

### `sandbox` — Incubating

Direction:

- schedule + namespace + fanout + redirects
- not a standalone traversal subsystem

### `credentials` — Incubating

Direction:

- game kernel + asset collection + render + writeback
- not a direct legacy port target

### `scratch/mechanics` — Archive

Use:

- idea source
- prior art
- test inspiration
- design vocabulary

Do not treat it as a promotable runtime surface without rederiving the design
against v38 contracts.

---

## Mechanics Convergence

The lower StoryTangl strata remain deliberately generic:

- core supplies entities, registries, graphs, selectors, references, and
  dispatch;
- VM advances story state through phase-governed movement and activity on that
  graph;
- story projects committed graph activity through the journal.

Mechanics overlay an interoperable vocabulary for the detailed things a
participant can possess, inspect, alter, combine, contest, repair, move, and
trade. They should not become separate game engines. Specialized interactions
remain graph-native and share the same identity, phase, persistence,
affordance, transaction, progression, and presentation contracts.

The converging vocabulary is:

- **assembly managers** own collections of durable components;
- **components** carry identity, state, provenance, and facets;
- **facets** describe capabilities without creating another dispatch system;
- **interactive game handlers** adopt facets into contextual choices,
  validation, costs, and outcomes;
- **presence** projects graph state into dynamic descriptions and visible
  affordances;
- **media generation** may render those projections on demand;
- **transactions** move ownership and value through explicit committed
  operations;
- **stats and progression** support evaluation, repair, racing, combat, and
  improvement;
- **StoryTanglish interaction vocabulary** expresses those operations through
  portable choices, accepts contracts, fragments, UX events, and story-info
  projections rather than client-specific widgets;
- **journal projection** remains the narrative output surface.

Convergence does not require every family to share one base class or generic
manager. Each family keeps its own kernel and specialized folds while exchanging
compatible identity, discovery, interaction, commitment, receipt, and projection
artifacts through the existing runtime lifecycle.

### World-adopted mechanics and scenario layers

Mechanics are world-agnostic kernels. They define durable state, operations,
resolution, and interchange artifacts without assuming a particular setting or
presentation. A world adopts a mechanic by exposing the catalogs, providers, and
behavior authorities that the mechanic may use. World domain logic may specialize
the mechanic with subclasses, additional handlers, or modified policy, but those
changes remain local to that world's authority surface rather than mutating the
global mechanic.

Adoption has four authored/runtime layers:

```text
World authority
  -> scenario or consumer type
     -> configured scenario instance
        -> materialized entity, encounter, or situation
```

- The **world** controls which local, system-provided, or explicitly imported
  catalogs and authorities are visible.
- The **scenario type** selects from those resources and defines the interaction
  class: its ordinary actions, dispositions, rules, and extension logic. It may be
  a bespoke Python subtype such as a hall-monitor or robot-vetting block; mechanics
  convergence does not require all policy to become data.
- The **scenario instance** configures one invocation: quantities, distributions,
  objectives, exceptions, and special encounters or actions.
- The **materialized instance** carries the durable state for one participant,
  packet, assembly, encounter, generated actor, or current sandbox situation.

Catalogs answer what can exist. Scenario-type policy determines how those things
are interpreted. Scenario-instance distributions determine what a particular run
contains. Narrative and media projection determine what the resulting logical state
is called and how it appears.

| Mechanic | World exposes | Scenario type defines | Scenario instance configures | Concrete instance |
| --- | --- | --- | --- | --- |
| credentials | credential catalogs and handlers | selected catalog, actions, dispositions, policy | encounter count, disposition distribution, special cases | character, packet, defects, expected disposition |
| outfits | wearable catalogs and projections | slots, dress rules, actions, scoring | challenges, contestants, rounds, special garments | actor, outfit assembly, environment, result |
| sandbox | templates, maps, schedules, actors, affordance providers | exploration and interaction policy | active region, objectives, population, events | current location, present actors, state, affordances |
| demographics | system name banks plus world-specific providers | population or NPC archetype profile | trait distributions, population size, exceptions | NPC with committed traits, name, and provenance |
| progression | skills, upgrades, badges, challenges | advancement and evaluation policy | starting state, curve, rewards, special challenges | actor capabilities, history, and current condition |

This authority boundary is not a permanent ban on cross-world reuse. A future
world dependency may explicitly import and re-export a catalog or behavior registry,
making it part of the importing world's authority surface. Runtime consumers still
resolve only through their bound world; they do not reach into another loaded world
by name. Foundational system providers, such as ordinary real-world name banks, may
be mounted into every world deliberately, while bespoke providers remain local or
explicitly imported.

Catalog implementations must preserve that boundary. Nominating a catalog from a
world is insufficient if the catalog then searches a process-global population of
all instances of its token class. A token catalog therefore represents an explicit,
bounded set of definitions. Scenario types select a world-local catalog reference;
internal world/catalog/item qualification may remain a persistence detail.

Credentials are the first demanding convergence case. A credential packet
combines durable component identity, visible evidence, hidden truth, inspection
findings, holder bindings, provenance, generated media, contextual choices,
phase purity, replay, and persistence.

Its central hidden-information rule is:

> Contribute choices from visible existence; disclose hidden validity only
> through committed resolution.

Components contribute state and facet vocabulary. The credentials game handler
continues to own menus, time costs, validation, mediation, and disclosure.
Planning must not mutate graph state; graph-backed materialization belongs at a
setup or UPDATE boundary.

### Demonstration worlds as conformance surfaces

The demonstration worlds are integration fixtures, not disposable examples.
Each should exercise one or two pieces of the shared vocabulary before later
worlds compose a broader range:

- the credentials world exercises hidden-information inspection and mediation;
- the hall-monitor reskin must prove that the credentials loop is
  genre-neutral;
- the logical-adder reskin exercises the same underlying logic through different
  content and feeling;
- the separate Twine-loader demo remains a codec surface while round-trip
  fidelity and loss tracking mature; later it should support an explicit parity
  comparison rather than replace the canonical reskin;
- the sandbox / Colossal Cave world exercises movement among location nodes,
  location-driven activity fan-out, presence, mobile roles, and declarative
  capability-conditioned opportunities;
- the CarWars worlds exercise vehicle assembly, inventory, repair, loadouts,
  transactions, racing, and combat.

The eventual robot chopshop is the comprehensive integration target. It is a
capstone because one graph-owned assembly feeds several mechanics, not merely
because several minigames appear in the same world. Installed parts and upgrades
derive legality indications, challenge effects and capability tags, visible
condition, available work, and progression opportunities. Permits authorize
derived indications but do not duplicate assembly truth. Repair, installation,
legalization, purchase, and sale then commit changes to that same object.

The player sources, evaluates, legalizes, repairs, modifies, races, and trades
those robots while using sandbox behavior to move among the relevant activity
hubs. Travel and arrival expose location-specific work, encounters, and mobile
roles, so movement between the yard, inspection station, workshop, registry,
market, and track also advances the surrounding story rather than merely
selecting a different mechanics screen.

The archived catalogs favor symmetric three-value axes such as benign / neutral
/ harmful. Treat that as an authoring discipline, not an engine cardinality or a
reason to hard-code world enums. The convergence proof is that the same authored
component can contribute through several established facet channels while each
handler retains its specialized fold.

The robot also travels with the player. At each sandbox location, the active
story state and local problems are matched against capabilities donated by the
player, inventory, present actors, and the robot's current assembly. That match
may expose a new activity, alter a challenge, or trigger a companion
intervention. Locations declare requirements and outcomes; companions declare
capabilities and interaction vocabulary. Neither side contains a catalog of the
other side's concrete labels.

The Colossal Cave demonstration is the smaller proof surface for this exchange.
Its pirate and dwarves can be real scheduled mobile actors rather than anonymous
room-event probabilities, while retaining an ambient encounter policy. A few
additional declarations can then give those actors persistent state and richer
interactions, or give the player a mobile companion whose capabilities change
the cave's fanout without rewriting its rooms.

A mechanics change is incomplete when its focused tests pass but the relevant
demonstration worlds no longer compose or demonstrate the shared vocabulary.

---

## CalvinCards as Exemplar

`scratch/mechanics/calvin_cards` is the clearest local example of the target
mental model.

What it demonstrates:

- the **same kernel** can be rebound to multiple semantic catalogs
- mechanical artifacts can be projected through different narrative voices
- a compact resolution grammar can produce strong story output

Why it matters:

- it separates abstract strategy and matchup logic from vocabulary and flavor
- it implies explicit runtime artifacts such as offers, intents, records, and
  receipts
- it makes writeback visible as the difference between a toy and a story-capable
  mechanic

This is why StoryTangl mechanics are better framed as **families of consequence
grammars** rather than just “minigames.”

---

## Current Implementation Priorities

1. Make token catalogs explicit bounded collections exposed by a world authority;
   scenario types select a local catalog reference without naming or searching a
   world.
2. Continue the credentials vertical through that corrected authority seam: one
   world can expose both border and school catalogs, while two separately loaded
   worlds remain isolated even when local catalog and item ids collide.
3. Build the full hall-monitor conformance scenario through the four-layer
   world/type/instance/encounter model without adding credentials-specific engine
   vocabulary.
4. Retire credential compatibility fields only after the manager-backed border and
   hall-monitor paths have been exercised side by side.
5. Normalize credential defects and connect credential components to presence and
   media projection.
6. Reconcile vehicle and loadout vocabulary with assembly, transactions, and
   progression.
7. Extend the Adventure sandbox with one scheduled mobile actor and one
   capability-bearing companion contribution, without world-specific choice
   projection branches.
8. Exercise the combined vocabulary, sandbox traversal, and activity hubs in
   the robot chopshop flow.
