# Mechanics: Demographics

`tangl.mechanics.demographics` is a **profile/domain facet** rather than a full
resolution mechanic family.

It provides:

- resource-backed regional, country, subtype, and name-bank catalogs
- a `DemographicSampler` for sampling identity profiles
- a `HasDemographics` facet for story entities that want demographic identity in
  their local namespace

## Layer Coverage

- **Kernel**: light sampling rules and normalization helpers
- **Domain**: the primary strength of this family today
- **Runtime**: `DemographicData`
- **Render**: limited for now; mainly naming and namespace publication
- **Writeback**: not a focus of this family
- **Facade**: `HasDemographics`

## Review Lens

- **Shape**: demographic profiles, regions, countries, subtypes, and name banks
- **Behavior**: controlled profile sampling and normalization
- **Attachment points**: actor composition and namespace publication
- **Appearance**: identity and naming metadata today, richer prose/media later

## Notes

- Naming requires an explicit RNG, form, and catalog scope. Historical geography
  helpers retain their existing optional RNG policy.
- Slices 1–3 and 4a (one name owner plus durable profile/Actor composition) are
  implemented. Explicit UPDATE completion (4b) is implemented; Casting Desk (5) remains planned. See the
  [design contract](DEMOGRAPHICS_DESIGN.md) and
  [staged retrofit plan](DEMOGRAPHICS_RETROFIT_PLAN.md), tracked by
  [issue #285](https://github.com/derekmerck/storytangl/issues/285).
- The target separates shared, world-scoped naming definitions from committed
  individual profiles, including custom world origins and compound name banks.

## Data Notes

Select and register a pack explicitly before using the existing sampler:

```python
import random
from tangl.mechanics.demographics import DemographicSampler, load_pack, register_pack

pack = load_pack("sample")  # Validates and copies data; no Singleton registration.
catalog = register_pack(pack)  # Registers definitions and returns this pack's exact offers.
profile = DemographicSampler.sample_demographic(country="fra", rng=random.Random(7))
name = DemographicSampler.sample_name(
    "fra", form="female", catalogs=[catalog], rng=random.Random(7),
)
```

- Import performs no resource loading or registration. `load_pack("full")` requests
  the optional historical LFS bank; absent files and LFS pointers raise
  `PackUnavailableError`. Callers can catch that exception and explicitly select
  `sample`. Malformed YAML/schema data raises its normal parse/validation error
  and never falls back.
- Both packs use unchanged `nationalities.yaml` (approximately 2021, 215 countries,
  nine regions). `sample` contains only the two illustrative `fra`/`jpn` pools
  previously embedded in the loader. It does not support arbitrary country sampling.
  Its YAML and metadata are regular git files; required tests need no LFS/network.
- `pack.metadata` records source, revision, transformations, and known provenance
  gaps. The full revision identifies the historical repository LFS blob, not a
  verified upstream release. Curated pools retain their entries and implicit
  duplicate weights. No demonym-derived banks are created.
- `pack.countries_without_banks()` reports countries with neither a base nor any
  subtype bank; `pack.uncovered_subtypes()` reports missing **exact** country/subtype
  banks. These are audits of that pack, independent of process-global definitions;
  they do not choose fallbacks or assert that a base bank covers a subtype.
  Sample coverage: 213 countries without banks; 978 missing exact subtype banks.
  A read-only audit of the recorded full blob found 219 banks, zero countries
  without a bank, and 973 missing exact subtype banks. This does not mean every
  subtype is covered by its country base bank; an LFS pointer alone proves no coverage.
- Pure `parse_pack(metadata, geography, names)` is available for already parsed
  historical-format mappings. It validates before registration and leaves inputs
  unchanged. Definitions take live `Subtype`/`Country` references; resource parsing
  no longer happens inside model validators. The implicit
  `load_demographic_distributions()` API is retired; the caller audit found no
  source/app/world consumers outside this package.
- Definition registration remains process-global and sequential; conflicting values
  fail rather than mutating a Singleton. Catalog offers and bank selection are
  explicitly scoped. Transactional replacement is not implemented. Actor/name
  ownership is settled in 4a; the supported 4b UPDATE boundary is documented below.

## Scoped banks and origins

A definition's `(class, label)` is its global Singleton identity. An optional
`NameBank.selection_key` is an ordinary Core identifier for a world-local reference;
it is not permission to reuse an internal label for a different value.

```python
from tangl.mechanics.demographics import (
    NameBank, NameForm, NamePart, NamePool, Origin, name_catalog, select_origin,
)

river_bank = NameBank(
    label="my_world.river_names", selection_key="fra",
    forms={"plain": NameForm(
        given=NamePart(pool=NamePool(candidates=["Ari"])),
        family=NamePart(pool=NamePool(candidates=["Reed"])),
    )},
)
offered = name_catalog(catalog, overrides=(river_bank,))
origin = Origin(label="river_kingdom", banks={"fra": 1})
selection = select_origin(origin, catalogs=[offered], rng=random.Random(7))
name = DemographicSampler.sample_name(
    selection.bank, form="plain", catalogs=[offered], rng=random.Random(8),
)
```

`name_catalog` composes explicit base catalogs and explicit overrides by local key
(`selection_key` or label). It removes replaced offers before publication, leaving
source catalogs and shared definitions untouched. Conflicting base keys and repeated
override keys fail; ambiguous offers from independently published catalogs still
fail under the existing factory/graph resolver. Catalog order is not precedence.
Publish the composed catalog once, rather than also publishing its replaced base.

Worlds expose that catalog through their existing asset/module provider's
`get_token_catalogs` method. Ordinary world handlers pass
`catalogs=ctx.get_token_catalogs()` and `rng=ctx.get_random()` to selection and
sampling. This uses World → factory/graph → PhaseCtx catalog access; no engine
layer imports demographics. The tests exercise actual `World.from_script_data`,
story creation, and a `PhaseCtx` before sampling.

All name samplers require explicit catalogs and an RNG. `select_bank(ref, catalogs=...)`
resolves local identifiers/internal labels or a live bank **only within that scope**.
It never falls back to global registration. `select_bank(Selector(...), catalogs=...,
rng=...)` uniformly selects matching offered banks; candidates are deduplicated and
sorted by internal label/class. Labels should be stable authored identities when
reproducing runs. Unknown or ambiguous required references fail descriptively.

`Origin(label=..., banks={ref: weight, ...})` is a small authored value, not a country
or actor. One reference selects a bank; equal weights give a uniform mixture.
Weights must be finite, non-negative numbers, with a positive eligible total.
Every reference must resolve, even at zero weight; zero-weight offers are excluded
from the draw. Reference order is sorted before drawing. `NameSelection` is a
transient receipt retaining the original origin and selected live bank, so two
origins can borrow one bank without losing their labels. An origin can be embedded
through the existing constructor-form field marker; no custom serialization is used.
Committed UPDATE generation provenance is documented in the 4b section below.

Country lookup requests the exact `country_subtype` reference when a subtype is
present. `fallback_bank="fra"` above is a deliberate caller policy, not a statement
that the sample bank covers every French subtype. Fallback references must also
be offered by the supplied catalogs. Historical geography sampling remains the
existing optional policy; constraint/age-alias corrections and generation policy
are handled by the explicit 4b UPDATE policy below. Custom bank/origin selection needs no country or ethnicity.

## Name formation (slice 3)

`NameBank.forms` maps arbitrary caller-selected keys to `NameForm` values. A form
has optional `given` and `family` parts, at least one present. `NamePart.pool` is a
required stem pool; optional `prefix` and `suffix` pools attach literal strings
using their declared separators. An absent affix/part is `None`; an empty or
all-zero pool is invalid even when used for an optional affix.

```python
sprite = NameBank(label="my_world.sprite_names", forms={"open": NameForm(
    given=NamePart(pool=NamePool(candidates=["Cookie"])),
    family=NamePart(
        pool=NamePool(candidates=["Winter"]),
        suffix=NamePool(candidates=["mint"]),
    ),
)})
sprites = name_catalog(overrides=(sprite,))
name = DemographicSampler.sample_name(
    sprite, form="open", catalogs=[sprites], rng=random.Random(7),
)
assert name.full_name() == "Cookie Wintermint"
```

The kernel returns the existing `PersonalName`, with no automatic title and neutral
name metadata unless the caller supplies `gender`. Gender does not choose a form;
keys need not be gendered. Omitting `family` gives a single name. Exact spelling,
Unicode, case, punctuation, and separators survive; no title-casing/parser cleanup
runs. Draw order is given then family, each stem then any prefix/suffix.

`NamePart.substitutions` replaces an exact selected stem before affix assembly.
For example, `{"Abelsdóttir": "Abelsson", "Adamcová": "Adamec"}` contains complete
surname replacements; unmatched stems are unchanged. This is independent of literal
`Winter` + `mint` composition, with no grammatical inference.

`NamePool(candidates=[...], weights=[...])` uses optional positional weights. The
lengths must match; weights must be finite non-negative numbers with a positive
total. Zero positions are excluded from drawing. Unweighted pools use uniform
selection over their original entries, including repeated spellings. No entries
are deduplicated, reordered, or assigned invented frequencies.

Historical `female`/`male`/`surname`/`male_surnames` fields exist only at the resource
import boundary. `parse_pack` turns them into `female`/`male` forms, sharing the
surname pool and putting exact exceptions on the male family part. Missing, null,
or empty historical male pools explicitly reuse the female given part in the
normalized male form. There is no runtime missing-pool or gender fallback. The
read-only historical audit preserved all 385,828 candidate positions, including
901 duplicates, and all 21 exception maps; source resource bytes are unchanged.

`sample_xx_name`, `sample_xy_name`, and `sample_namebank` are retired; callers use
`sample_name(..., form=...)`. Origin mixtures select a bank; the caller's requested
form must exist on the chosen bank. `sample_demographic(..., rng=...)` now returns
only demographic facts; it takes no name-form, bank-fallback, or naming-catalog
arguments. Call `sample_name` separately when a world wants a name. Name selection
keeps its explicit scoped catalog, form, and RNG contracts.

Nested recipe values opt into existing constructor form at their owning fields.
Name banks remain ordinary Singleton references; no recipe-specific serializer or
registry is added.

## One name owner and durable facts (slice 4a)

`actor.personal_name` is the authoritative existing `PersonalName` owned by prose's
`PersonalNamedActor`/`PersonalNamedConcept`. `DemographicData` is now a profile-only
constructor-form value: optional gender, age range, country, region, and subtype.
`HasDemographics` owns and publishes those facts, with no name properties or name
cache. The obsolete `HasDemographic`/`demographics` aliases and inherited profile
name fields are removed. Worlds opt into both facets explicitly:

```python
from tangl.core import EntityTemplate, Graph
from tangl.prose.naming import PersonalNamedActor
from tangl.mechanics.demographics import HasDemographics
from tangl.persistence.serializers import JsonSerializationHandler as Json

class CastActor(PersonalNamedActor, HasDemographics):
    pass

# Already chosen values are ordinary materialization inputs, not callbacks.
chosen_name = DemographicSampler.sample_name(
    "fra", form="female", catalogs=[catalog], rng=random.Random(7),
)
template = EntityTemplate.from_data({
    "kind": CastActor, "label": "guide", "personal_name": chosen_name,
    "demographic": profile,
})
graph = Graph()
actor = template.materialize(registry=graph)
actor.personal_name.given_name = "Ari"
assert actor.name == ""  # No copied display name to become stale.
assert actor.get_ns()["full_name"] == actor.personal_name.full_name()
restored = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
assert restored.get(actor.uid).personal_name.given_name == "Ari"
```

Given+family, given-only, and family-only personal names compose with the same
profile. Namespace personal-name forms are computed from the current owned value.
Without an authored display override, prose's default proper nominal uses the
current personal name. Explicit `name` and `proper_forms` remain intentional prose
policy and are not overwritten during rename. The demographic namespace publishes
`demographic`, `demonym`, and present facts; personal naming publishes its own
`personal_name`/name-form symbols.

Owning profile/name fields and the profile's Singleton-reference fields explicitly
opt into existing constructor form. Saved graphs retain actual actor IDs, names,
and facts; Region/Country/Subtype resolve to live definitions. Bootstrap declared
catalogs/world authorities before fresh-process restore. No sampler runs during
construction, namespace reads, rendering, or restore. There is no automatic world
activation, custom serializer, NPC factory, or name-sync bridge.

4a supplies durable composition. The explicit UPDATE policy below implements 4b;
this does not install automatic setup generation. NameBank/origin provenance is
recorded in the separate completion receipt, not duplicated into the facts profile.
Casting Desk and media remain later work.

## Explicit UPDATE completion (slice 4b)

Worlds opt in by declaring an owned `GenerationRequest` and optional
`GenerationReceipt` on their actor, with `unstructurable=True` owning-field markers
(and `include=True` for the receipt). In an ordinary world `apply_update` handler,
commit the tuple returned by the one supported entry point:

```python
from tangl.mechanics.demographics import complete_generation
# In an opted-in world UPDATE handler, with its explicit actor and PhaseCtx:
# actor.personal_name, actor.demographic, actor.generation_receipt = complete_generation(
#     actor.generation_request, personal_name=actor.personal_name,
#     demographic=actor.demographic, receipt=actor.generation_receipt, ctx=ctx,
# )
```

Actors are materialized through normal templates **before** this helper fills them.
UPDATE is supported; automatic setup/construction generation is not installed.
There is no global actor scan or automatic dispatch registration. Worlds that do
not call the helper remain unchanged.

`GenerationRequest(facts={"gender", "age_range"}, name_parts={"given_name": True,
"family_name": False}, bank="fra", form="female")` requests only those dimensions.
For name parts, true means fill if the value is None; false leaves the part alone,
including intentional absence, and omitted keys request nothing. Encode intentional absence in the request,
not `model_fields_set`: constructor form elides explicitly set default None values.
A recipe with an absent family part never invents one. Non-None authored components,
titles, aliases, ordering, and prose overrides are preserved.

Choose an exact bank (optionally an explicit scoped fallback) or an `Origin` mixture.
Required references and forms are checked before drawing; country/region contradictions fail.
Bank selection stays within ctx catalogs. Fully pinned names do not draw from an
unused mixture. Facts are independent: a mononym request need not request geography,
gender, or age. Missing subtype requests require geographic constraints.

Draw order is region, country, subtype, gender, age, bank mixture, given, family.
Geographic and subtype candidates are label-sorted; region/country population
weighting is controlled by `population_weighted`. Subtypes use the declared mixture;
gender retains the existing uniform XX/XY policy; age is uniform over unique enum
values, including OTHER. No empirical gender/age weights are invented. The old
unused gender/age `weighted` switches are removed; subtype's switch now works.

The helper returns detached proposed values and a completion receipt for one normal
world UPDATE assignment. No global transaction/recovery contract is added. A receipt
makes every later call a no-op, including after author rename. It records generated
field names, selected origin, live bank, form, and definition revision (None when
unknown), without copying the authoritative name. NameBank.revision comes directly
from pack metadata or an authored world recipe, never its identity hash.

Replay has two distinct meanings: recorded diff replay reapplies actual values and
IDs without executing generation; re-execution from the same pre-event graph runs
the original deterministic draws once. Tests prove identical actor state, graph
hash and observed RNG state, followed by committed-state no-op continuation. JSON
fresh-process restore bootstraps declared world/catalogs first and makes no name
sampling calls. Dynamic creation of new actors during the helper, automatic setup
hooks, global rollback and hot reload are not supported. Casting Desk/media remain
slice 5 and later work.
