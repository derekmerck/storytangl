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

- Sampling now accepts an optional RNG so callers can make the behavior explicit
  and reproducible without changing existing defaults.
- Slices 1–2 (explicit packs and scoped bank/origin selection) are implemented.
  Slices 3–5 remain planned. See the
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
profile = DemographicSampler.sample_demographic(
    country="fra", catalogs=[catalog], fallback_bank="fra", rng=random.Random(7),
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
  Full coverage must be audited with actual full data; an LFS pointer cannot prove it.
- Pure `parse_pack(metadata, geography, names)` is available for already parsed
  historical-format mappings. It validates before registration and leaves inputs
  unchanged. Definitions take live `Subtype`/`Country` references; resource parsing
  no longer happens inside model validators. The implicit
  `load_demographic_distributions()` API is retired; the caller audit found no
  source/app/world consumers outside this package.
- Definition registration remains process-global and sequential; conflicting values
  fail rather than mutating a Singleton. Catalog offers and bank selection are
  explicitly scoped. Transactional replacement and actor/name ownership are not
  implemented; the slice 4 checkpoint remains open.

## Scoped banks and origins

A definition's `(class, label)` is its global Singleton identity. An optional
`NameBank.selection_key` is an ordinary Core identifier for a world-local reference;
it is not permission to reuse an internal label for a different value.

```python
from tangl.mechanics.demographics import NameBank, Origin, name_catalog, select_origin

river_bank = NameBank(
    label="my_world.river_names", selection_key="fra",
    female=["Ari"], surname=["Reed"],
)
offered = name_catalog(catalog, overrides=(river_bank,))
origin = Origin(label="river_kingdom", banks={"fra": 3, "jpn": 1})
selection = select_origin(origin, catalogs=[offered], rng=random.Random(7))
name = DemographicSampler.sample_namebank(
    selection.bank, catalogs=[offered], rng=random.Random(8),
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
Committing actor provenance remains slice 4.

Country lookup requests the exact `country_subtype` reference when a subtype is
present. `fallback_bank="fra"` above is a deliberate caller policy, not a statement
that the sample bank covers every French subtype. Fallback references must also
be offered by the supplied catalogs. Historical geography sampling remains the
existing optional policy; constraints, age aliases, and profile ownership remain
later work. Custom bank/origin selection needs no country or ethnicity.

## Credits

The name bank was primarily compiled from the FreeCities Twine game. Additional
demographic data such as populations and demonyms were scraped from the web.
