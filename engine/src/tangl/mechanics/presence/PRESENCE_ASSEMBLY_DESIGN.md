# Presence / Body-Attachment & the Assembly Instrument

```{storytangl-topic}
:topics: presence, assembly
:facets: overview, design
:relation: defines
:related: media, open_link, credentials, token
```

**Status:** DESIGN + FIRST IMPLEMENTATION SLICE. The question is how to avoid a family
of parallel systems that all look like "components attached to a body/vehicle/entity,
with slots, visibility, constraints, and projections."

> Issue tracking: see the "Presence / body-attachment unification" issue and the
> assembly-core issues (#131 umbrella → #194/#195/#196). This doc holds the *what
> and why*; the issues hold the *where-next*.

## Implementation status

`OutfitManager` now uses the assembly-layer `ComponentManager` path: it is still
embedded on `HasOutfit`, but its assigned wearables are graph members stored by UUID
and dereferenced through the owning actor's registry. `HasOutfit.outfit` opts into
constructor-form persistence with `json_schema_extra={"include": True,
"unstructurable": True}`, so mutated outfit state survives graph round-trips without
making the outfit manager a graph item.

This resolves the first serialization identity bug for outfits. The body-attachment
generalization below remains the design target for ornaments, injuries, cybernetics,
robot parts, vehicles, and credential packets.

## Current shape

- `OutfitManager` is a real `ComponentManager[Wearable]` using the shared
  `SlottedContainer` slot, validation, budget, and facet APIs.
- `WearableType` is an `AssetType`; `Wearable` is a token wrapper over that type.
- `Ornamentation` is still a plain `Node` with `collection: list[Ornament]`.
- `Ornament` is an `Entity` with `body_part: BodyPart`, `ornament_type: OrnamentType`, `text: str`.
- `Look` composes `Look`, `OutfitManager`, and `Ornamentation` into prose and media
  payloads, but does not currently feed outfit coverage into ornament visibility.
- `BodyRegion`/`BodyPart` support coarse/fine masks. `WearableLayer.BODY` exists;
  `WearableLayer.INNER` is documented as hiding the body.

## What ornaments are

Actor-bound distinguishing marks: tattoos, scars, burns, brands, piercings, marker
ink. They are not assets because they are unique to an actor's body and are not
inventory/transfer objects. A red dragon tattoo can be token-like and state-bearing
without becoming a transferable asset.

## Design options

### A. Keep `Ornamentation` mostly as-is
Add an outfit-aware `visible_items(outfit=...)`; make `Look.describe()` pass
outfit-covered regions into ornamentation; keep `OrnamentType` enum + `Ornament`
body-bound. Smallest change; preserves tests. But keeps a parallel list-manager
beside `OutfitManager` and does not help cybernetics/injuries/robot parts.

### B. Make `Ornamentation` homologous with outfit
`OrnamentationManager(SlottedContainer[Ornament])`, slots keyed by `BodyPart`/
`BodyRegion`, visibility by comparing ornament masks with outfit coverage. Aligns
with `OutfitManager`; keeps marks distinct from inventory; opens a clean path for
piercings/makeup/wounds/cybernetics. Still needs a generalized visibility/layer
policy so each manager doesn't roll its own body-mask math.

### C. Tokenize ornaments without treating them as inventory
`BodyMarkType(Singleton)` + `BodyMark = Token[BodyMarkType]`: general type is the
definition (tattoo/scar/burn), token carries instance overrides (text, body_part,
severity, visibility). Matches the "general type + specific override" wearable
pattern; keeps marks graph-local and state-bearing. Requires deciding whether
`AssetType` is "tokenizable concept type" or only "holdable asset type."

### D. Adopt ornaments into outfit as BODY-layer components
Marks live in an outfit-like container at `WearableLayer.BODY`; clothes at `INNER`+
hide body-layer components by region. One layered visibility model, natural for
makeup/piercings/prosthetics/armor. But risks making `OutfitManager` too broad —
clothing, wounds, limbs, implants are not all one domain, and injuries/cybernetics
carry mechanical consequences clothing does not.

## Generalization pressure

The same pattern recurs across likely mechanics: robot parts (slots, compatibility,
power/weight budgets), cybernetics/prosthetics (body slots, visibility, power),
injuries (body slots, severity, restrictions), weapons/tools in hand (hand slots,
action availability), credentials/components (slots, expiration, acceptance policy),
vehicle outfitting (slots, capacity, power/weight budgets).

**Common instrument** (the assembly layer):
slotted component assignment (`SlottedContainer`) · optional budgets
(`BudgetTracker`) · region/part occupancy & coverage masks · visibility projection ·
domain-specific validation and consequences.

**Domain-specific pieces stay separate:** outfit (clothing state + prose);
ornamentation/body marks (skin-layer detail); injury (impairment + action gating);
cybernetics/robotics (capabilities, dependencies, resource budgets).

## Recommended direction

Do not collapse ornaments directly into `OutfitManager` yet. Instead:

1. Add an explicit `BodyAttachment`/`BodyLayerComponent` vocabulary carrying
   `body_part`/mask, `layer`/attachment stratum, optional `visible_when_covered`,
   optional domain tags/capabilities.
2. Promote `Ornamentation` to a slotted manager over that vocabulary.
3. Give `OutfitManager` a small coverage API: `covered_parts()`/`covered_mask()`,
   possibly `visible_components()`.
4. Make `Look` ask the managers for visible projection rather than doing coverage math.
5. Reuse the same body-slot/visibility instrument for injuries and cybernetics
   before creating separate managers with near-identical assignment rules.

## First low-risk slice

Before deep model changes (validates the cross-manager visibility contract without
committing to tokens vs assets vs body-layer):

- Add `OutfitManager.covered_mask()` using ON/CLOSED worn items at `INNER`+.
- Teach `Ornamentation.describe_visible_items(outfit=...)`.
- Update `Look.describe()` and media payloads to omit ornaments hidden by outfit.
- Test: an arm tattoo is hidden by a shirt/coat and visible when uncovered.
