# Demographics: Catalog Definitions and Sampled Individuals

```{storytangl-topic}
:topics: demographics
:facets: overview, design
:relation: defines
:related: singleton, provisioning, presence, prose
```

**Status:** SLICES 1–2 IMPLEMENTED — explicit packs, honest availability, scoped
name-bank catalogs, and origin selection are implemented. Name formation and
committed profile/name ownership remain pending (slices 3–5).
**Tracking:** [issue #285](https://github.com/derekmerck/storytangl/issues/285).
**Execution:** [bounded retrofit plan](DEMOGRAPHICS_RETROFIT_PLAN.md).

## Purpose and boundaries

Demographics is an optional mechanics package for constructing consistently
flavored individuals from authored constraints and reusable population and naming
data. A world may need contemporary people, inhabitants of several kingdoms, or
sprites named Cookie Wintermint. None requires a universal model of a person.

The package may be used as a small sampler without starting a story. It still uses
Core's Singleton, Selector, catalog, and constructor-form conventions. Worlds opt
in through their domain composition; engine layers do not import the mechanic to
activate it.

Keep the useful curated data and small sampling functions. Replace global lookup
assumptions and implicit generation with explicit scoped inputs and committed
results. Do not introduce another registry, serializer, settings system, or hook
framework.

## Existing implementation and gaps

`Region`, `Country`, `Subtype`, and `NameBank` already derive from `Singleton`.
`DemographicSampler` accepts an RNG, and `HasDemographics` publishes a sampled
`DemographicData` into the namespace. This is a retrofit of the shipped package,
not a promotion of the retired scratch implementations.

The remaining gaps are concrete:

- Definition registration still uses process-global Singleton collections, while
  name-bank offers and lookup are bounded by explicitly supplied catalogs.
- Name-bank fields assume female/male given-name pools and a surname. Custom
  species, single names, and compound fairy surnames do not fit naturally.
- The sample pack deliberately covers only two name banks. Explicit coverage audits
  expose missing banks; selection policy for uncovered requests remains pending.
- Sampler inputs include contradictory region/country pairs, uncovered subtype
  banks, unused weighting arguments, and age-enum aliases that affect selection.
- `DemographicData` inherits `PersonalName`, while modern prose naming embeds a
  `PersonalName`. Actor composition needs one authoritative name and an explicit
  constructor-form persistence contract.

Historical world overlays and the sprite bank are useful behavioral precedents,
not implementations to copy. Some older overlay code was unfinished.

## Vocabulary and ownership

| Thing | Owns | Does not own |
| --- | --- | --- |
| Naming definition / name bank | Stable identity, candidate pools, formation rules, optional weights, source provenance | Per-NPC random state or a global used-name list |
| Origin/population definition | Authored origin identity and selection policy for naming data and other defaults | Every fact about everyone from that origin |
| World catalog | A bounded view of eligible definitions selected by the world's authority | Mutable copies of built-ins disguised as overrides |
| Sampled profile | Chosen values and generation provenance for one individual | Live sampling callbacks or duplicated actor identity |
| Graph-owned actor | Durable individual identity, profile, and its current authoritative name | Shared catalogs or name-bank resources |

These are responsibilities, not a requirement for five new public classes.
Reuse existing types where they fit. A bank is one selectable definition, not an
enum member for every name in its pools.

Singleton definitions are shared and treated as read-only after catalog assembly.
Use the existing `TokenCatalog` for bounded views and `Selector` for matching.
Apply explicit selection weights after candidate selection; do not add a
mechanic-specific registry or universal similarity scorer.

A graph-local token is appropriate when a definition needs a runtime representative
or per-instance overrides. It is not required for every bank consulted during a
sample. Token creation does not imply random generation. In particular,
`TokenCatalog.materialize_one()` currently makes a token, not an Actor: do not
assume that `Token[PopulationDefinition]` is already an actor factory.

## World extension and resolution

Worlds explicitly select built-in packs and contribute their own definitions.
An origin can select an existing bank, a custom bank, or a weighted mixture.
Several origins can share a bank without losing their own identity: Northern
Kingdom and River Kingdom remain different origins even if both borrow the same
naming data. No inverse country-to-kingdom mapping is needed.

An overlay selects/replaces an offered definition in the world-visible catalog;
it does not patch a shared built-in singleton in place. A world definition takes
precedence for the reference it explicitly replaces. Internal singleton identity
must remain unambiguous: world-local selection keys are not permission to create
two different objects with the same concrete singleton class and label.

Reuse the existing authority and scoped-definition resolution paths. Establish the
smallest supported declaration shape in the catalog slice, including a witness
with two worlds choosing different definitions for the same local key. If this
requires changing Core identity or restoration order, stop for a design checkpoint
rather than hiding an override map in the sampler.

The world controls correlations. Country, residence, ancestry, naming tradition,
age, pronouns, appearance, and voice are distinct facts. A fantasy bank need not
declare a country or ethnicity. Existing geographic distributions remain an
optional data pack, not mandatory fields for all generated characters.

### Implemented scope/reference shape (slice 2)

`register_pack` returns a `TokenCatalog[NameBank]` with exactly that pack's banks.
`NameBank.selection_key` uses Core's existing identifier field marker; internal
identity remains `(class, label)`. Two worlds can offer different internally named
banks for the same local key. The collision witness passes through actual World,
GraphFactory/Graph resolution, story materialization, and PhaseCtx catalog access.
No Core identity, authority, token restoration, or serializer changes are needed.

`name_catalog(*bases, overrides=...)` is explicit naming-offer composition at world
setup. Overrides replace an offer by local key before the result is published;
they never mutate a built-in or leave a hidden runtime override map. Conflicting
base keys and repeated override keys fail. If a world publishes overlapping
uncomposed catalogs, normal exact-reference ambiguity still fails; list order is
not a priority system.

`select_bank` uses Selector/TokenCatalog against only the supplied catalogs,
including when passed a live bank. Exact lookups reject ambiguity. Selector draws
use stable label/class ordering and the caller's RNG. Pure name samplers require
explicit catalogs and RNGs; world handlers obtain them from `ctx.get_token_catalogs()`
and `ctx.get_random()`. No engine layer activates demographics on a world's behalf.

`Origin(label, banks={ref: weight})` is a constructor-form-capable authored value.
Its explicit mixture validates finite non-negative weights and requires all refs,
including zero-weight refs, to resolve in scope. Draws exclude zero weights and
use sorted reference order; a positive eligible total is required. A transient
`NameSelection` retains the origin and chosen live bank. This is not actor
materialization or a durable profile/provenance owner.

Country/subtype lookup is exact. A caller can declare `fallback_bank` explicitly,
resolved in the same scope; bank presence does not change the exact coverage audit.
Geography sampling is still the historical optional policy, not a requirement on
custom origins. Actor/name ownership and profile persistence remain the slice 4
checkpoint.

## Name formation

Provide a small, data-driven repertoire:

1. Select complete name parts from pools, allowing a single name or an omitted
   family name where the definition permits it.
2. Assemble parts with declared separators and optional or required affixes.
3. Apply declared form variants, including explicit exception mappings.

The sprite example chooses a given name and assembles a family name from a stem
and suffix. A gendered surname may instead select a complete inflected form:
existing `male_surnames` data includes substitutions, not merely concatenation.
Lexical suffix selection and grammatical form selection are different rules even
when both happen to append text. A missing optional affix is valid; an empty
required pool is a declaration error.

Put these conventions on the naming definition. Worlds select the desired forms;
the sampler must not hard-code female/fairy cases or require binary pools for
every species. Normalize old resource fields at the pack-loading boundary and
update in-repo consumers together. Do not retain a second runtime model merely
to preserve old YAML spelling.

Preserve Unicode, punctuation, and intentional capitalization. Display ordering
and titles belong to personal-name/form policy, not random string cleanup.
This is not a general morphology engine, grammar language, or executable YAML DSL.

### Frequencies and variety

Uniform selection remains valid and is the default for unweighted banks. Accept
explicit weights where supplied; do not manufacture frequency claims for curated
lists. Negative weights, all-zero eligible weights, and mismatched weight domains
fail validation. A later world policy may soften observed weights or avoid roster
duplicates. Such state belongs to the roster/run, not the shared singleton.

## Sampling, lifecycle, and persistence

```text
world-visible definitions + authored constraints + explicit RNG
    -> select eligible definitions
    -> sample missing values and validate the complete result
    -> materialize the graph-owned individual with committed values
    -> project prose, portraits, credentials, and audio from that individual
```

- Authored values take precedence. Sampling fills missing values; it does not
  replace an explicitly supplied name or resample pinned facts.
- Inconsistent constraints fail descriptively. Optional dimensions may be absent;
  a requested dimension must have an eligible source or an explicit fallback.
- Pure sampling accepts the caller's RNG. Story integration uses the established
  frame/runtime RNG at setup or UPDATE; it never draws randomness during a name
  getter, JOURNAL projection, PLANNING, or restore.
- Candidate order is stable before selection. Reproducibility means the same
  constraints, RNG state, algorithm, and versioned catalog yield the same values.
  A seed alone is not a promise across arbitrary dataset updates.
- Store actual values, selected origin/bank identity, and catalog revision for
  provenance. Mutable personal-name state has one owner; later renaming must not
  leave an obsolete copy inside a second demographic naming model.
- Materialize through the existing template/provisioning path. A world handler
  may supply sampled construction inputs through normal dispatch; do not create
  an independent NPC factory or intercept every phase.
- Embedded values opt into constructor form at their owning fields. Shared
  singletons use existing reference forms, not embedded resource tables. Restore
  loads/binds the declared catalogs before resolving references, then restores
  committed values without invoking the sampler.

The first actor slice must settle whether the profile composes `PersonalName` or
the actor owns it separately. Prefer the smallest composition sharing the existing
naming value; test the actual Actor/prose composition before prescribing a new
inheritance tree. Anonymous/proper realization, role binding, and narrator
knowledge remain prose policy, not demographics.

## Resource availability and provenance

Import must work without Git LFS or a large optional name pack. Ship a small,
clearly identified regular-git sample pack for examples and required tests. The
full historical bank remains optional. Absence is distinct from malformed loaded
data; neither silently invents plausible-looking names. A world requesting
unavailable data fails descriptively unless it explicitly chooses another pack
or fallback.

Record source, extraction/revision information, transformations, and redistribution
status at pack level, with per-bank exceptions where needed. Preserve curated
FreeCities-derived material while documenting known provenance gaps. The existing
geography file describes itself as approximately 2021; do not relabel it as a
current census or make its category taxonomy universal.

Changing datasets is separate from repairing catalog scope. Faker or public
name datasets may become optional import sources; none is required for this
refresh. Inspect duplicates and coverage rather than silently changing effective
sampling weights during conversion.

## Projection and the first consumer

The proposed consumer is a small **Casting Desk** demo, borrowing credential and
presence features without changing Hall Monitor's fixed proofs. Exercise a human
bank, two world origins sharing a bank, and a custom sprite bank. Authors can pin
some facts and generate the rest, inspect the individual, and save/restore without
changing their identity.

Appearance and outfit remain Presence facts. Portraits use the existing semantic
portrait/media pipeline; renderer selection does not regenerate the person.
A voice may eventually be a selected reference-audio RIT. Nationality must not
implicitly mandate a voice. Optional DiceBear, generated portraits, or TTS remain
separate adapters, not sampler imports or required test assets.

Start with text and lightweight fixtures. Portraits, described outfits, and a
reference greeting can extend the same individual after core witnesses pass.

## Deferred until a consumer needs them

- Dataset replacement, cohort distributions, and softened frequency policies.
- Roster/family/household relationships and duplicate avoidance.
- General inflection or salient anonymous-description generation.
- Voice synthesis, model workers, automatic outfits and portrait generation.
- Catalog hot reload, cross-version regeneration, and a new RNG-stream framework.

These remain possible extensions, not prerequisites or silently closed work.
