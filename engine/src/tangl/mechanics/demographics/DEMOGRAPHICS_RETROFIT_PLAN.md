# Demographics Modernization Retrofit

```{storytangl-topic}
:topics: demographics
:facets: design, tests
:relation: documents
:related: singleton, provisioning, presence, prose
```

**Status:** SLICES 1–3 AND 4a IMPLEMENTED — naming and durable Actor/profile
composition are implemented. Slice 4 is split: 4b lifecycle generation/provenance
and real replay remain planned, as does Casting Desk (5). Full slice 4 is not complete.
**Contract:** [Demographics design](DEMOGRAPHICS_DESIGN.md).
**Tracker:** [#285](https://github.com/derekmerck/storytangl/issues/285).

## Delivery policy

Keep each slice independently reviewable and the package usable after every merge.
Reuse existing sampling, Singleton/TokenCatalog, Selector, materialization, and
constructor-form seams. Update in-repo consumers when a surface changes; do not
add compatibility aliases without an actual outside consumer. Keep dataset
replacement, broad personal-name parser changes, and media generation separate.

The user explicitly authorizes replacing the old public API and test bench where
they encode the retired design. Verify consumers on current main first; the
current source/apps/worlds scan finds none outside this package. Preserve useful
data and behavioral requirements, not signatures, compatibility aliases, or
print-only tests. Build new assertions around the revised contract, and retain or
adapt existing tests that still exercise it. This is permission for a clean API
refresh across the slices, not a requirement to replace everything in slice 1.

Tests must assert values, world isolation, and actual persistence, rather than
only printing plausible names. Use small regular-git fixtures and explicit RNGs.
Do not fetch LFS or install renderers/models to run the required witnesses.

## 1. Make pack loading explicit and honest

**Capability:** use a known small pack or an explicitly requested full pack,
without import-time fabrication.

**Chokepoint:** resource loading in `data_models.py` and package initialization.
Separate parsing/normalization from registration. Retain historical pools; identify
the sample pack as sample data. Remove synthetic demonym-name fabrication. World
composition or a standalone caller explicitly chooses packs. Audit subtype-to-bank
coverage rather than assuming every country has every requested bank.

**Witnesses / done when:**

- Import with an absent full pack or an LFS pointer succeeds without loading it.
- Selecting an unavailable pack fails descriptively; the sample pack works.
  Malformed loaded data fails rather than looking like absent optional data.
- Loading is deterministic and repeatable without mutating parsed input. Fixtures
  do not globally clear unrelated world definitions to make tests pass.
- Pack metadata records source/revision and known provenance gaps; in-repo callers
  explicitly select their intended data.

Do not generalize resource management across the engine for this slice.

## 2. Resolve banks through world-visible catalogs

**Capability:** worlds choose custom banks without leaking into one another;
several authored origins can borrow one bank.

**Chokepoint:** `Country.namebank()` and sampler candidate resolution. Pass a
bounded catalog into sampling and reuse authority resolution for scoped references.
Define the smallest origin-to-bank declaration, including an explicit weighted
mixture. Geography remains an optional origin policy.

**Witnesses / done when:**

- Worlds A and B expose the same local key with different definitions; neither
  changes the other's results or the built-in definition.
- Two origins sharing a bank retain their distinct origin identities.
- Exact selection, Selector eligibility, stable candidate ordering, and explicit
  world precedence work. Unknown references fail clearly.
- No new global registry, duplicate Singleton identity, or custom singleton
  serializer is introduced.

**Checkpoint before code:** verify the declaration/reference shape against current
catalog APIs. If they cannot express this scope, bring back the smallest collision
witness and implicated contract before changing Core.

**Checkpoint result / implemented:** Core identifier fields and explicit bounded
TokenCatalog offers express the local-key collision without foundational changes.
`NameBank.selection_key` is a normal identifier; definitions retain unique internal
labels. `name_catalog` replaces explicit offers before world publication, rather
than changing factory precedence or shared Singleton values. Pure selection and
name samplers require explicit scope; world handlers use existing context catalog
access. `Origin` declares a finite non-negative weighted reference mixture, and a
transient `NameSelection` preserves the origin and bank. Exact subtype lookup and
explicit fallback policy remain separate. Tests cover two actual worlds in both
initialization orders, real story/context access, scoped exact/Selector selection,
invalid/zero weights, deterministic order, and constructor-form embedding of the
new origin value. No actor persistence or name-formation refresh is claimed.

## 3. Generalize the small naming kernel

**Capability:** complete-part banks and compound banks share the sampler.

**Chokepoint:** `NameBank`, pack normalization, and name sampling methods. Add only
selection, simple assembly, and explicit form substitutions. Allow omitted parts
according to the definition; a sprite need not have a country or binary name pool.

**Witnesses / done when:**

- A human fixture preserves complete given/family forms; a sprite fixture selects
  a given name, stem, and required suffix.
- Optional suffix absence works; an empty required pool fails at load.
- Explicit surname-form exceptions work without being mistaken for suffixes.
- Unicode, capitalization, separators, and authored single names survive.
- Uniform and weighted selection are deterministic; invalid weights fail.
  Duplicate entries are handled deliberately during data conversion.

Migrate definitions, in-repo data, and callers together. Do not invent a general
name grammar or silently rebalance the historical bank.

**Implemented:** `NameBank.forms` contains `NameForm` given/family declarations,
with `NamePart` stem/substitution/affix assembly over ordered `NamePool` candidates
and optional positional weights. Callers choose an arbitrary form key and receive
the existing `PersonalName`; omitted parts and neutral/unrestricted forms work
without geography. The old binary runtime fields/samplers are removed. Historical
fields normalize once at the import boundary, including explicit male-pool reuse,
without changing data bytes or multiplicity. Tiny fixtures prove formation,
substitutions, invalid declarations, fixed-RNG weighted/unweighted draws, owned
value JSON constructor form, and real-world catalog/origin use. The read-only full
bank audit verifies its recorded hash and all original pools/maps. Geographic
profile/name ownership is resolved below in 4a; lifecycle generation remains 4b.

## 4a. One name owner and durable Actor/profile composition — implemented

**Ownership:** `actor.personal_name` is the existing authoritative `PersonalName`
field from prose's PersonalNamedConcept/PersonalNamedActor. `DemographicData` no
longer inherits it; it contains optional demographic facts and shared references.
HasDemographics publishes facts without shadowing Actor.name or storing a name.
A world composes the facets explicitly and supplies chosen values through ordinary
EntityTemplate/story materialization. No automatic sampling or syncing bridge.

**Implemented witnesses:**

- Actual World + EntityTemplate materialization creates one graph-owned Actor with
  independent owned name/profile values and live definition references.
- Given+family, given-only, and family-only names work. Mutation/replacement changes
  namespace and prose forms/default nominals; explicit name/proper_forms overrides
  remain intentional policy.
- Graph constructor form through real JSON preserves actor ID, actual values and
  live Region/Country/Subtype references. Fresh-process restoration bootstraps the
  declared catalogs/world authorities and succeeds with all samplers disabled.
- Namespace reads and rendering consume no frame RNG; no sampler runs in getters,
  constructors, or restoration. Owning field markers reuse existing machinery.

**Checkpoint result:** the composed Actor works without Core identity, authority,
or restoration changes. The only generic prose correction uses the current owned
PersonalName as the default nominal when no authored display name exists, and
projects current personal-name symbols through normal namespace contribution.
Pure APIs are separate: sample_name returns PersonalName; sample_demographic returns
facts only. Neither automatically materializes an individual.

## 4b. Sample missing facts at the lifecycle boundary — planned

**Capability:** preserve authored inputs, generate missing facts once at normal
setup/UPDATE boundaries, and retain committed results/provenance through replay.

**Remaining witnesses / full slice 4 acceptance:**

- Pinned fields win; only missing values consume RNG under a settled budget.
  Contradictory geographic constraints and uncovered required naming selections
  fail descriptively; explicit fallback remains separate from exact coverage.
- Age aliases do not accidentally add weight. Advertised weighting options work
  or are removed; broader age/name parser changes remain separate.
- Decide and persist generation provenance, including selected origin/bank and
  catalog revision, without duplicating the authoritative personal name.
- Normal setup/UPDATE generation uses frame RNG through existing dispatch and
  EntityTemplate materialization; no automatic generation in model validators,
  getters, PLANNING/JOURNAL, or structure().
- A real ledger witness proves exactly-once generation, no resampling during
  restore/replay, actual committed values, and preserved authored facts.

4a's graph/JSON witnesses do not claim lifecycle generation or ledger replay.
Reassess the generation/provenance contract before 4b implementation; no parallel
NPC/token factory or global rollback policy is implied.

## 5. Ship a small Casting Desk consumer

**Capability:** demonstrate the refresh without destabilizing existing Hall Monitor
or credential fixtures.

Generate and inspect a small cast with authored origin/species/facts. Exercise the
human and compound-sprite cases and two origins sharing a bank. An ordinary choice
creates another individual. Use the established world/service walkthrough harness.

**Witnesses / done when:**

- The demo uses declared catalogs only; identical versioned inputs and seed give
  the same committed cast.
- Namespace/prose forms and an optional credential refer to the same actor.
- Save/restore retains individuals without regeneration.
- The world README explains intent and the demonstrated capability; add its line
  to the world index according to repository governance.
- Required tests need no LFS, network access, GPUs, or optional renderers.

Text completes the initial demo. A separate follow-up may add Presence/outfit
prose, an opt-in portrait, and a reference-audio greeting through existing media
paths. They are not prerequisites for completing slices 1–4.

## Completion and follow-ups

#285 can close when slices 1–3, 4a–4b, and 5 land with their behavioral witnesses. Update design
status and the package README then. Record still-desired advanced work as deferred
follow-ups rather than claiming the whole synthetic-NPC/media problem is solved.

Slices 1–3 and 4a are the implemented boundary. Reassess the generation/provenance
checkpoint before 4b; this sequence is not permission to
refactor foundational contracts opportunistically.
