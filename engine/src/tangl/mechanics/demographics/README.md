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
- This family is the first modernization spike because it is useful, small, and
  low-risk while still exercising the new facet contract.

## Data Notes

- The authoritative datasets live in YAML resources and may be large enough to
  sit behind git-lfs.
- Lightweight fallbacks remain available so tests can run without the full
  dataset.

## Credits

The name bank was primarily compiled from the FreeCities Twine game. Additional
demographic data such as populations and demonyms were scraped from the web.
