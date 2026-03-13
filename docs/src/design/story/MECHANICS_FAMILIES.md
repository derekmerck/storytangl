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

1. Document the family model and promotion rules.
2. Refresh nearby README and docs surfaces to match the model.
3. Modernize `demographics` as the first facet-oriented spike.
4. Rescue `presence` by promoting real outfit/loadout logic out of examples and
   reducing `look` to a cleaner domain/runtime plus render shape.
5. Later, grow `progression` and `assembly` into fuller story-capable families,
   and convert `sandbox` / `credentials` from design notes into composed v38
   implementations.
