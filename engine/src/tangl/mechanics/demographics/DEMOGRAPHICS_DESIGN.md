# Demographics Subsystem Design Review

```{storytangl-topic}
:topics: demographics
:facets: overview, design
:relation: defines
:related: singleton
```

**Status:** DESIGN REVIEW — intentionally separate from general cleanup. Demographics
is an old, mostly standalone subsystem whose interesting questions are
design/API/data-extension, not comment hygiene. Do the review *before* changing code.

> Issue tracking: see the "Demographics design review" issue (deferred; trigger = a
> world needs custom namebanks/cultures). This doc holds the *what and why*.

## Current shape

- Package: `engine/src/tangl/mechanics/demographics/`
- Tests: `test_demographics.py`, `test_demographics_builtins.py`
- Data: `resources/nationalities.yaml`, `resources/world_names.yaml`
- Core types: `Region`, `Country`, `Subtype`, `NameBank` as `Singleton` subclasses;
  `DemographicData` as the sampled runtime profile; `HasDemographics` as a
  namespace-publishing facet; `DemographicSampler` as the pseudo-front-end API.

## Why it deserves its own pass

- Written before the dispatch-era architecture; stable partly because it has almost
  no dependency on the rest of the engine.
- `Singleton` is doing useful dynamic-enum/catalog work here.
- Resource data is large and historically accreted (FreeCities-derived namebanks plus
  fantasy/genre extensions).
- The hard questions are world/domain extension: how does a world inject/override
  namebanks? how should fantasy cultures map to real regional naming data? are
  Region/Country/Subtype the right authored vocabulary? compose catalogs through
  dispatch, resource managers, package resources, overlays, or constructor inputs?
  how to configure weighted sampling/gender/age/family-name-order/titles without a
  settings blob?

## Existing TODOs (the raw material)

- `data_models.py`: sampling weights; subtypes→enum; ethnicity-aware namebanks;
  region/country-by-name; overlays.
- `sampler.py`: artificial gender weighting; age distributions by region.
- `demographic.py`: family-name-first from country/language; titles from parent role.

## Review questions

**Catalog model** — keep `Singleton` catalogs or introduce an explicit catalog object
owning regions/countries/subtypes/namebanks? If `Singleton` stays, how do tests/worlds
safely isolate/overlay instances? Should `Subtype` become a true enum, or is dynamic
singleton identity the point for fantasy cultures?

**World extension** — package-resource discovery for demographic resources? overlays
merge-by-label vs replace-by-label vs explicit inheritance? `country.namebank(subtype)`
vs `DemographicCatalog.resolve_namebank(...)`?

**Dispatch hooks** — candidates: choose candidate regions/countries/subtypes/namebanks;
weight candidates; postprocess sampled profile; contribute role/title/language naming
rules. Risk: dispatch can make a mostly-pure sampler harder to reason about unless
hooks are isolated behind a catalog/policy object.

**Faker-like API** — a stable facade (`sample_name`, `sample_profile`,
`sample_actor_demographics`, `resolve_namebank`) delegating to a catalog/policy.

## Suggested next step

1. Map current singleton/catalog lifecycle and import-time resource loading.
2. Identify side-project/fantasy namebanks if present here or in sibling dirs.
3. Sketch two extension designs: (a) minimal overlay files loaded by world/package
   resources; (b) explicit `DemographicCatalog` + optional dispatch hooks.
4. Only then decide which TODO comments become code, docs, or issues.
