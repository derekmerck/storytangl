# Presence / Body-Attachment & the Assembly Instrument

```{storytangl-topic}
:topics: presence, assembly
:facets: overview, design
:relation: defines
:related: media, open_link, credentials, token
```

**Status:** IMPLEMENTED FOUNDATION + ACTIVE GENERALIZATION. Outfit and wardrobe
managers use the shared owner-bound assembly path; presence text and portrait
projections are active consumers, including credential-card composition. Outfit
coverage filters ornaments in Look, namespace, and presence text projections;
broader body-attachment unification remains open.

> Current issue tracking: #283. The earlier assembly issues #131 and
> #194/#195/#196 are closed implementation history. This doc holds the *what and
> why*; the open issue holds the remaining where-next.

## Implementation status

`OutfitManager` now uses the assembly-layer `ComponentManager` path: it is still
embedded on `HasOutfit`, but its assigned wearables are graph members held in slot wallets owned by the
actor's graph. `HasOutfit.outfit` opts into
constructor-form persistence with `json_schema_extra={"include": True,
"unstructurable": True}`, so mutated outfit state survives graph round-trips without
making the outfit manager a graph item.

`WardrobeManager` applies the same identity rule to inactive clothing storage. It is
embedded on `HasWardrobe`, persists by constructor-form recursion, references a graph-owned wallet for its broad storage slot, and can expose that slot through the transaction
layer's component-slot holder adapter. A dressing offer moves one stored wearable out
of the wardrobe and assigns it into the active outfit; the outfit manager still owns
body-region/layer legality and validation.

This resolves the first serialization identity bug for outfits. The body-attachment
generalization below remains the design target for ornaments, injuries, cybernetics,
robot parts, vehicles, and credential packets.

## Current shape

- `OutfitManager` is a real `ComponentManager[Wearable]` using the shared
  `SlottedContainer` slot, validation, budget, and facet APIs.
- `WardrobeManager` is a storage-side `ComponentManager[Wearable]` for graph-member
  wearables not currently assigned to the active outfit.
- `WearableType` is an `AssetType`; `Wearable` is a token wrapper over that type.
- `Ornamentation` is an embedded `Entity` with `collection: list[Ornament]`.
- `Ornament` is an `Entity` with `body_part: BodyPart`, `ornament_type: OrnamentType`, `text: str`.
- `Look` uses `OutfitManager.covered_mask()` for ornament descriptions and tokens;
  bundled ornament namespace and presence text use the same coverage decision.
- `LookMediaPayload` carries assigned wearable instance IDs, fully qualified singleton kind and
  label, state, coverage, layer, and color. Assigned items remain in the handoff
  when open, off, or covered; a world adapter interprets those facts against its
  own catalog. Off items are omitted from worn-outfit prose. The Modiste
  adapter owns that mapping, not Presence. A garment's assignment slot and its
  covered body regions are separate facts, and renderer masks derive from the selected
  artwork. Current slot validation requires the garment to cover its slot's region;
  an upper-slot garment covering only legs needs a future eligibility design.
- `BodyRegion`/`BodyPart` support coarse/fine masks. `WearableLayer.BODY` exists;
  `WearableLayer.INNER` is documented as hiding the body.

## What ornaments are

Actor-bound distinguishing marks: tattoos, scars, burns, brands, piercings, marker
ink. They are not assets because they are unique to an actor's body and are not
inventory/transfer objects. A red dragon tattoo can be token-like and state-bearing
without becoming a transferable asset.

The actor embeds its ornament manager, and the manager exclusively owns its mutable
marks. Both fields use constructor-form embedding, preserving each local identity and
concrete kind with the actor. Neither manager nor marks is registered in the graph.
This ownership policy is separate from possible future shared body attachments.

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

## Partially landed low-risk slice

The first slice validates the cross-manager visibility contract without committing
to tokens vs assets vs body-layer:

- `OutfitManager.covered_mask()` uses ON/CLOSED worn items at `INNER`+.
- Ornament description accepts the resulting covered-part mask.
- Look prose, media, namespace and presence rendering apply the coverage mask;
  direct body-only and ornament-only facets remain usable without an outfit.
