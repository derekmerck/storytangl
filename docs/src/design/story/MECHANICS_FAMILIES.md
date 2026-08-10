Mechanics Families
==================

**Status:** 🟡 ACTIVE ARCHITECTURE NOTE  
**Posture:** optional, world-adopted extension families under `tangl.mechanics`

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

Within each family, we reason about implementation through a common set of
facets rather than by forcing a filesystem reorganization up front. These are
review lenses, not additional engine layers.

---

## Family Facets

Each mechanic family should describe which of these facets it implements and
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

The shared rendering boundary is described in
[Episode-to-Syuzhet Rendering](EPISODE_SYUZHET_RENDERING.md): phase-assembled
namespaces feed typed content adapters, while individual mechanics contribute
semantic facts without owning prose, media, or other presentation policy.

Convergence does not require every family to share one base class or generic
manager. Each family keeps its own kernel and specialized folds while exchanging
compatible identity, discovery, interaction, commitment, receipt, and projection
artifacts through the existing runtime lifecycle.

### Mechanics as pressure systems

The strongest mechanics are not merely examples of attaching a minigame to the
narrative engine. They attach in a way that lets authors avoid enumerating the
cross-product of every earlier choice, current condition, available resource, and
possible outcome as a bespoke decision tree.

Compact minigames still have an important place as **resolution grammars** inside
that larger system. Rock-paper-scissors can drive a duel whose authored actions are
heavy attack, feint, and defend; the algebra resolves the exchange while injury,
position, reputation, equipment, and future retaliation supply its pressure and
consequence. A card game may score hands like poker while players strategically
raise, bluff, or call through a multiplayer rock-paper-scissors kernel. The reusable
value lies in the small, legible resolution grammar, not in presenting it as an
isolated diversion.

Resolution and concrete realization need not always occur in the intuitive order.
When supporting details were hidden and did not participate in the player's choice,
the mechanic may resolve the strategic exchange first and then materialize artifacts
consistent with that result. The card game can construct or reveal a hand after the
round so it beats the losers or loses to the winner. This is constrained realization,
not arbitrary contradiction:

```text
committed strategies + stakes
  -> abstract resolution
     -> outcome constraints
        -> materialized cards, blows, evidence, or other diegetic details
           -> narrative and media projection
```

Anything already observed or mechanically operative remains committed truth and
cannot be rewritten merely to justify the result. But latent details may be sampled,
assembled, or generated from the resolved constraints. This lets a tiny game kernel
support rich deterministic or procedural content without making authors enumerate
every possible hand, exchange, or presentation in advance.

None of this complexity is mandatory. The default challenge should remain the
simplest legible contract: establish the relevant state, accept the player's move,
resolve it through the kernel, and commit the result. Perceived fairness is an
authorial and narrative tool, not a universal engine invariant or a score every
mechanic must calculate. A scenario may add tells, hidden information, responsive
opponents, late realization, or outcome steering only when those devices create
useful pressure.

What matters to the player is the presented causal contract. A fair-seeming contest
should preserve enough consistency and responsiveness for the player's move to feel
meaningful; an intentionally unfair contest should preserve the intended experience
of coercion, corruption, fate, comedy, or dramatic necessity. Internal orchestration
may be simpler or more directed than its diegetic presentation, provided it does not
accidentally contradict facts the story has committed. The engine should make
ordinary fair play easy and leave bounded intervention seams available, not require
every author to configure a theory of fairness before resolving a challenge.

The authored unit is therefore better understood as a **pressure system** than as
a branch. A world supplies populations, rules, resources, authority, histories,
consequences, and presentation policy. A scenario selects and narrows those inputs.
The mechanic combines them into currently available interventions, evaluates the
committed choice, and writes durable results that later situations may interpret.

```text
state + rules + resources + authority + history
  -> available interventions and their costs
     -> committed action and multi-axis evaluation
        -> durable consequences
           -> facts, relationships, and resources for future pressures
```

This does not require one universal correctness or morality score. The same action
may be evaluated independently as:

- **available** under the participant's current authority, inventory, location,
  knowledge, and relationships;
- **rules-correct** under the scenario's institutional or procedural policy;
- **evidentially supported** by what was visible or established when the action was
  committed;
- **beneficial or harmful** to the participant, candidate, institution, faction, or
  world according to authored consequence logic;
- **easy or difficult** in time, attention, resources, reputation, exposure, skill,
  or other tunable costs;
- **durable**, producing artifacts, memories, relationships, injuries, upgrades,
  permissions, obligations, or world facts that affect later scenarios.

These axes remain separate so an action can be procedurally correct, institutionally
rewarded, personally safe, and disastrous for somebody else. Conversely, an action
may violate policy, cost the player dearly, and still produce an authored compassionate
outcome. The engine records attributable facts and applies explicit rules; the world
decides what those facts mean and when their consequences return to the story.

Mechanic families contribute different parts of this pressure grammar:

- **assembly** is a foundational adapter. It turns durable components and their
  relationships into capabilities, restrictions, defects, resource budgets, and
  other semantic facts that downstream mechanics can consume;
- **progression and badges** accumulate durable changes in competency, reputation,
  permission, and history, altering the costs and possibilities of later actions;
- **sandbox presence, locations, and schedules** determine which actors, resources,
  problems, and opportunities are currently in scope, allowing the same durable
  state to produce different local fan-outs without rewriting each location;
- **transactions** move artifacts, custody, value, and authority between participants
  through explicit commitments and receipts;
- **games and contests** turn gathered facts into bounded offers, costs, resolution,
  and writeback;
- **credentials, combat, racing, and similar capstones** combine several families at
  once: assemblies and capabilities, hidden or visible evidence, opposing objectives,
  resource pressure, institutional rules, risk, progression, and durable consequence.

Special authored encounters remain valuable. The goal is not to eliminate bespoke
storytelling, but to reserve it for distinctive meaning and dramatic events rather
than using it to manually restate every mechanical combination. A named candidate,
companion, weapon, waiver, injury, or prior betrayal can remain a durable graph-owned
fact and re-enter later namespaces, offers, and rendering. When an author adds a new
consequence after the fact, existing structured history supplies the context without
requiring every earlier passage to have anticipated that exact branch.

Projection completes the pattern. Narrative, dialogue, UI fragments, and media are
derived from the same committed semantic state, so deterministic or generated content
can remain synchronized with the pressures that produced it. Rendering does not own
the mechanic's truth, and the mechanic does not hard-code one prose, visual, or audio
realization.

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

Phase 8 gives the family a shared, transient `CredentialDefect` vocabulary.
The packet manager and mediated game state derive defects; policy folds them into
pass/deny/arrest; renderers consume the same observations without owning a second
status interpretation.

Its central hidden-information rule is:

> Contribute choices from visible existence; disclose hidden validity only
> through committed resolution.

Components contribute state and facet vocabulary. The credentials game handler
continues to own menus, time costs, validation, mediation, and disclosure.
Planning must not mutate graph state; graph-backed materialization belongs at a
setup or UPDATE boundary.

### Demonstration worlds as conformance surfaces

The demonstration worlds are integration fixtures and architectural probes, not
disposable examples. Each serves three related purposes:

- an **author-facing example** provides a reusable pattern for constructing an
  interaction;
- an **engine conformance case** proves that the shared mechanics, VM, journal, and
  rendering contracts compose;
- a **representational experiment** tests whether the interesting, non-grindy part
  of an inspiration can be reconstructed from stable primitives, declarative
  world/scenario data, and a small bespoke residual.

The third purpose is story-compression-adjacent, but it does not require a ratio of
source lines to authored data. The useful evidence is whether narratively distinct
examples repeatedly decompose into the same small vocabulary while their bespoke
code increasingly describes their identity rather than rebuilding recurrence,
hidden information, response mediation, consequence persistence, or content
projection.

Each substantial exemplar should therefore retain a lightweight decomposition
record alongside its design or world notes:

1. **Source inspiration** — the encounter, system, or experience being approximated.
2. **Experiential invariant** — what must remain interesting or recognizable to the
   player.
3. **Pressure structure** — objectives, hidden and disclosed facts, resources,
   preparation, interventions, costs, and consequences.
4. **StoryTangl mapping** — the kernels, scoped concepts, catalogs, assemblies,
   offers, transactions, schedules, persistence, and projection surfaces used.
5. **Deliberate approximation** — what differs from the inspiration by choice rather
   than by accident.
6. **Bespoke residual and framework friction** — what still requires special logic,
   what encoded awkwardly, and what reusable primitive the attempt may have exposed.
7. **Parity status** — which invariants have been demonstrated mechanically,
   narratively, and through a playable client.

These are design-provenance records, not benchmark scorecards. Comparing them across
the inhaler dilemma, recurring forgery, bribed denial, accomplice-assisted guessing,
environmentally transformed combat, scheduled pirate, inner voices, and robot
chopshop makes reimplementation choices concrete without pretending that narrative
fidelity is a single number. Persistent friction shared by several exemplars is
evidence for a missing coordinate; one-off residual is often exactly where authored
specificity belongs.

Each world should exercise one or two pieces of the shared vocabulary before later
worlds compose a broader range:

- the credentials world exercises hidden-information inspection and mediation;
- the hall-monitor reskin proves that the credentials loop is
  genre-neutral;
- a combined credentials conformance world proves that one world can host
  multiple locally authored scenario types, each selecting a bounded local catalog
  without mutating the shared kernel;
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

1. Complete: token catalogs are explicit bounded collections exposed by a world
   authority; scenario types select a local catalog reference without naming or
   searching a world.
2. Complete: one combined world exposes both border and school catalogs, while two
   separately loaded worlds remain isolated even when local catalog and item ids
   collide.
3. Complete: the Hall Monitor conformance scenario exercises the four-layer
   world/type/instance/encounter model without credentials-specific engine vocabulary.
4. Retire credential compatibility fields now that the manager-backed border and
   hall-monitor paths have been exercised both separately and in one world.
5. Complete: normalize credential defects as a shared derived vocabulary; retain
   presence and media projection as the next credential integration.
6. Reconcile vehicle and loadout vocabulary with assembly, transactions, and
   progression.
7. Extend the Adventure sandbox with one scheduled mobile actor and one
   capability-bearing companion contribution, without world-specific choice
   projection branches.
8. Exercise the combined vocabulary, sandbox traversal, and activity hubs in
   the robot chopshop flow.
