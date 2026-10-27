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
- Slice 1 (explicit packs and honest availability) is implemented. Slices 2–5
  remain planned. See the
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
register_pack(pack)          # Reuses identical definitions; rejects conflicting labels.
profile = DemographicSampler.sample_demographic(country="fra", rng=random.Random(7))
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
- Registration is process-global and sequential; it does not implement scoped
  world overlays or transactional catalog replacement. A conflicting definition
  fails rather than mutating an existing Singleton. Scoped selection and actor/name
  ownership remain the slice 2 and slice 4 design checkpoints.

## Credits

The name bank was primarily compiled from the FreeCities Twine game. Additional
demographic data such as populations and demonyms were scraped from the web.
