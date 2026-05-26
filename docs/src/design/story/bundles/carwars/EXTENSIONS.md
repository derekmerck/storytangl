# Carwars Bundle — Widget Vocabulary Extensions

**Bundle id:** `carwars`
**Vocab spec base:** `STORYTANGL_WIDGET_VOCAB.md` v1.5
**Status:** draft v0.4 · aligned to v1.5 core vocabulary
**Audience:** authors writing carwars-genre bundles; port implementers covering the carwars profile suite

This document is a **Tier P3 genre extension** (per main spec §8). It does
not modify Tier S/P1/P2 contract surfaces. It defines:

1. Typed sub-shapes that carwars bundles populate on `UIHints` and
   `RollFragment.inputs` (extending open dicts; no new top-level types).
2. The bundle's conventional usage of `PieceFragment.realized`,
   `ZoneConstraints`, and `RollFragment` for its game patterns.
3. A worked end-to-end example (the Garage turn).
4. Test patterns and port parity for these affordances.

Anything in this document that requires more than an extension to an
existing open dict is a candidate for promotion to Tier P2. Such
candidates go through the CLI Floor Rule (main spec §0.2).

The genre-specific enrichments here are advisory render hints. A client
that ignores `ui_hints.stat_check`, `ui_hints.drag`, or vehicle silhouette
layout still conforms when it renders the underlying `choice`, `piece`,
`zone`, `kv`, and `roll` surfaces with the click-pick fallbacks described
in the main spec.

---

## 0 · Genre summary

Car Wars Adventure Gamebooks combine RPG-style stat-check resolution,
inventory management, and vehicle outfitting. The patterns generalize
beyond the carwars-specific framing — equip-an-adventurer, build-a-deck,
ship-loadout, crafting bench, RNG skill checks, salvage / shopping. This
extension covers them once, named after the motivating bundle but reusable.

**Three orthogonal patterns** the carwars bundle exercises:

| Pattern | Main spec mechanism | Genre layer adds |
|---|---|---|
| Slot-style equipment zones | `ZoneConstraints.capacity` on zones with `zone_role: "slot"` | Conventions for which capacity kinds are used; layout hints for vehicle silhouettes |
| Catalog-style shopping/salvage | `PieceFragment.realized=False` in zones with `zone_role: "catalog"` | Conventions for `cost` and unavailable reasons |
| RNG stat checks | `RollFragment` (kind="dice") + a triggering `ChoiceFragment` | `ui_hints.stat_check` for pre-roll difficulty preview; `ui_hints.drag` for drag-drop equipment placement |

---

## 1 · Slot-zone conventions

A *slot* is a zone with `constraints.capacity` set, used to model an
equipment receptacle (vehicle weapon mount, adventurer hand slot, ship
hardpoint, kitchen prep station, deck synergy slot).

```js
// fragment_type: "group", group_type: "zone", zone_role: "slot"
{
  uid: "z-front-mount",
  fragment_type: "group",
  group_type: "zone",
  member_ids: ["pc-rocket-launcher"],
  constraints: {
    accepts_kind: ["weapon"],
    accepts_tags: ["mounted"],
    capacity: [
      { kind: "count",  max: 1, unit: "weapon" },
      { kind: "weight", max: 3, unit: "stone", sum_property: "weight",
        ledger_key: "vehicle.front.weight" }
    ]
  },
  layout_hints: {
    orientation: "row",
    reveal: "all",
    // genre-extension subkey for the silhouette renderer:
    silhouette: { region: "front", x: 0.5, y: 0.1 }
  },
  hints: { label_text: "front mount" }
}
```

### Conventional capacity kinds for carwars

| Capacity kind | Used for | `sum_property` | Notes |
|---|---|---|---|
| `count` | Per-mount weapon limits | (n/a) | Most common; `max: 1` is typical for weapon mounts |
| `weight` | Per-mount stone-weight limits | `weight` | Mirrors a `kv_list` row in projected state |
| `power` | Per-mount engine-load limits | `power_draw` | Same shape as weight, different ledger |
| `composite` | Vehicle-total limits | (multiple entries) | Multiple `ZoneCapacity` entries on the same zone all hold |

### Empty slots are visible

Per main spec §5.1 (Decision Legibility), an empty slot referenced by an
open `place` choice MUST render as a placeholder showing its label and
constraint summary. CLI port renders `[ front_mount: empty (weapon, cap 1, 0/3 stone) ]`.
The empty slot is the click-target for placement.

### Inverse: removing a placed piece (`unmount`)

Two conforming patterns. Bundle authors pick one per situation:

- **Per-slot pick choice.** Each occupied slot exposes its own `pick`
  choice (e.g., `e-unmount-front`). Simple, accessible, matches CLI floor.
- **Pieces choice over the slot's contents.** A single
  `accepts.kind="pieces"` choice with `target_zone_ref="z-front-mount"`
  and `min:1, max:1`. Lets the player select which to remove when slots
  hold multiples.

Both are conforming. Bundles MAY mix.

### Swap as compose

A swap is a `compose` choice with two parts:

```js
{
  edge_id: "e-swap-front",
  text: "Replace front weapon",
  accepts: {
    kind: "compose",
    parts: [
      { role: "remove", accepts: {
        kind: "pieces",
        constraints: { target_zone_ref: "z-front-mount" },
        min: 1, max: 1 } },
      { role: "install", accepts: {
        kind: "place",
        source_zone_ref: "z-vehicle-loose",
        target_zone_ref: "z-front-mount" } }
    ]
  }
}
```

Optional and rare; most bundles handle swap as two consecutive turns.

---

## 2 · Catalog conventions

A *catalog* is a zone whose members are `PieceFragment` instances with
`realized=False` (offers). A buy/take action commits an
`accepts.kind="pieces"` choice with `target_zone_ref` pointing at the
catalog and `target_kind: ["piece"]` (or genre-specific kind names).

```js
// PieceFragment with realized=False — an offer
{
  uid: "pc-flamethrower",
  fragment_type: "piece",
  piece_id: "flamethrower",
  kind: "weapon",
  realized: false,
  zone_ref: "z-murphs-catalog",
  properties: {
    name: "Flamethrower",
    weight: 3,
    power_draw: 1,
    ammo: 4,
    description: "Splash damage. Burns 1 fuel per shot."
  },
  cost: [{ ledger_key: "wallet", delta: -400, unit: "credit" }],
  available: true,
  hints: { label_text: "Flamethrower" }
}
```

### Use-case patterns (same shape, different framing)

| Framing | `cost` | Choice constraints |
|---|---|---|
| **Shop** | present (negative `delta`) | `min: 0`, `max: <per-visit limit>` |
| **Salvage** | absent | `min: 0`, `max: <recoverable count>` |
| **Quest reward** | absent | `min == max == K`, choice auto-commits |
| **Crafting output** | absent (cost is in the recipe's compose) | emerges from a recipe `compose` commit |

### Race conditions on availability

If a shop item runs out of stock between turns, the next envelope sends a
`control` fragment with `update` mutating the offer's `available: false`
and adding `unavailable_reason: "Out of stock until next session."`. The
offer stays visible (decision legibility); the choice referencing it
either dims that row or removes it from selectable members.

### Backend-issued realized UIDs

When a player commits to buy `pc-flamethrower`, the next envelope contains:

- A new `PieceFragment` with `realized=True` and a backend-issued
  `piece_id` (e.g., `pc-flamethrower-#a3` for the third flamethrower
  minted in this session) — placed in the player's inventory zone.
- A `control` fragment removing the offer from the catalog zone (or
  flipping its `available` to false if the catalog represents stock).

Bundles document their realized-id naming convention. Carwars uses
`<offer-piece-id>-#<session-counter>` for stackable items; for unique
items the offer's id carries forward unchanged.

---

## 3 · Pre-roll choice → `RollFragment` flow

The carwars bundle uses `RollFragment` (main spec §7.3) for stat checks.
The pattern is two envelopes:

**Envelope N** carries the *triggering* `ChoiceFragment` with a
`stat_check` ui_hint. Its `accepts.kind` is `pick` — the player commits to
attempt the check; the backend rolls.

**Envelope N+1** carries the resolved `RollFragment` (with canonical
`outcome`) and a new choice list reflecting whichever branch the roll
selected.

### `ui_hints.stat_check` typed sub-shape

```python
# Pseudo-Pydantic; lives in genre extension code, not main spec types
class StatCheckHint(BaseModel):
    label: str                            # "Driving check" / "Lockpicking"
    dice: str                             # "2d6", "1d20", "3d10"
    target: int                           # difficulty value
    against: dict[str, str] | None = None # {"piece_id": "you", "property": "driving"}
    modifier: int = 0
    success_text: str | None = None       # "5/6 chance" — pre-computed by backend
```

When `ui_hints.stat_check` is present on a choice:

- The widget MUST surface the difficulty BEFORE commit so the player
  understands the wager. CLI: `Driving 12 (2d6, +0)`. Web: a small badge
  with the dice + target + advisory probability.
- The choice's `accepts.kind` MUST be `pick` (or `compose` with a pick
  part). Anything more interactive should generate the check after the
  interactive part resolves.
- `success_text` is advisory; if absent, the port may compute its own
  preview ("5/6 chance" for 2d6 vs 12). The client MUST NOT use this
  preview to gate commit; it's purely informational.

### `RollFragment.inputs` for `kind: "dice"` rolls

The carwars bundle uses `kind: "dice"` exclusively. The `inputs` shape:

```json
{
  "dice":     "2d6",
  "rolled":   [4, 5],
  "modifier": 0,
  "total":    9,
  "target":   12
}
```

`RollFragment.outcome` is one of `"success"`, `"fail"`, `"crit_success"`,
`"crit_fail"`. Bundles MAY define additional outcome strings for genres
with finer gradation (`"partial"`, `"with_cost"`).

### CLI floor rendering

```text
> drive
  Driving check (2d6 vs 12, modifier +0).
  rolled: 4 + 5 = 9.
  outcome: fail.
  The wheel jerks under you.
```

The **outcome word is not optional** — every roll renders its outcome
verbatim so transcripts are auditable. Per main spec §5.2, the visual
ritual on the web port is skippable to this CLI-equivalent rendering.

---

## 4 · `ui_hints.drag` typed sub-shape

Drag-and-drop is a presentation enhancement of `accepts.kind="place"`.
Per main spec §5.3 (Input Parity), every drag interaction MUST also work
as a two-step click-pick. The drag hint structure tells the web port how
to wire the drag affordance; ports that don't support drag (CLI, tkinter)
ignore the hint entirely.

```python
# Genre-extension typed sub-shape on UIHints
class DragHint(BaseModel):
    enabled: bool = True
    grab_zone_ref: str                    # uid of the source zone
    drop_zone_refs: list[str]             # uids of valid target zones
    preview: Literal["capacity", "blocker", "ghost"] | None = None
    fallback_label: str | None = None     # "Drag to mount, or click each step"
```

### Floor rule (mandatory)

> Drag-and-drop is a **presentation enhancement** of a click-pick choice.
> Every choice with `ui_hints.drag` MUST have an equivalent click-pick
> interaction reachable in the same turn. The CLI port ignores
> `ui_hints.drag` entirely.

This is just §5.3 applied to drag specifically. A web port test asserts
that for every `place`-accepting choice with `ui_hints.drag`, a click-pick
sequence (click the source piece, click the target zone) produces an
identical commit payload.

### Capacity preview during drag

When `preview = "capacity"`, the slot tile updates its capacity bar live
as the user drags a candidate piece over it. The client computes the
projected overflow by reading:

1. The target zone's projected capacity (from `ProjectedState.kv_list`
   row keyed by `target_zone.constraints.capacity[].ledger_key`).
2. The dragged piece's `properties.<sum_property>` value.

If the sum exceeds the projected `max`, the slot tile turns red. This is
purely advisory; the backend re-validates on drop.

### Reduced motion

With `prefers-reduced-motion`, no drag ghost, no preview animation. The
slot tile turns its border green/red statically as the candidate piece is
held over it (via keyboard navigation or screen-reader-friendly focus
rings), and the click-pick model is preferred in any conflict.

---

## 5 · Worked example — Garage turn

The classic outfitting scenario: the player is at Murph's Auto, deciding
which weapons to mount on the Beast (their interceptor) before heading
back into combat. Six fragments per envelope, demonstrating slot zones,
catalog with offers, place + pieces accepts, capacity ledger, and
optional drag affordance.

### Turn N — entering the Garage

```js
fragments: [
  // Scene-setting prose
  { uid: "f-prose-1", fragment_type: "content", content_format: "md",
    content: "Murph's Auto, end of the strip. Your **Beast** sits on the "
           + "lift, hood up, oil pan dripping. Murph wipes his hands on a "
           + "rag and looks up. \"What'll it be today?\"" },

  // Scene group
  { uid: "f-scene", fragment_type: "group", group_type: "scene",
    member_ids: [ ... ] },

  // Vehicle status zone
  { uid: "z-vehicle-status", fragment_type: "group", group_type: "zone",
    member_ids: ["pc-the-beast"],
    layout_hints: { orientation: "row" },
    hints: { label_text: "Beast — your interceptor" } },

  // Slot zones — the vehicle's mount points
  { uid: "z-front-mount", fragment_type: "group", group_type: "zone",
    member_ids: ["pc-rocket-launcher"],
    constraints: {
      accepts_kind: ["weapon"],
      capacity: [
        { kind: "count",  max: 1 },
        { kind: "weight", max: 3, sum_property: "weight",
          ledger_key: "vehicle.front.weight" }
      ]
    },
    layout_hints: { orientation: "stack",
                    silhouette: { region: "front" } },
    hints: { label_text: "front mount" } },

  { uid: "z-turret", fragment_type: "group", group_type: "zone",
    member_ids: [],
    constraints: {
      accepts_kind: ["weapon"],
      capacity: [
        { kind: "count",  max: 1 },
        { kind: "weight", max: 4, sum_property: "weight",
          ledger_key: "vehicle.turret.weight" }
      ]
    },
    layout_hints: { silhouette: { region: "top" } },
    hints: { label_text: "turret" } },

  { uid: "z-back-mount", fragment_type: "group", group_type: "zone",
    member_ids: [],
    constraints: {
      accepts_kind: ["weapon"],
      capacity: [
        { kind: "count",  max: 1 },
        { kind: "weight", max: 2, sum_property: "weight",
          ledger_key: "vehicle.back.weight" }
      ]
    },
    layout_hints: { silhouette: { region: "back" } },
    hints: { label_text: "back mount" } },

  // Catalog zone — Murph's wares (offers)
  { uid: "z-murphs-catalog", fragment_type: "group", group_type: "zone",
    member_ids: ["pc-flamethrower", "pc-armor-plate", "pc-vulcan",
                 "pc-rl-mk2"],
    layout_hints: { orientation: "grid", reveal: "all" },
    hints: { label_text: "Murph's wares" } },

  // Loose-parts zone — owned but not mounted
  { uid: "z-vehicle-loose", fragment_type: "group", group_type: "zone",
    member_ids: ["pc-spare-armor", "pc-spare-tire"],
    layout_hints: { orientation: "row" },
    hints: { label_text: "parts on hand" } },

  // Realized pieces (mounted weapons + spares)
  { uid: "pc-rocket-launcher", fragment_type: "piece", piece_id: "rl-1",
    kind: "weapon", realized: true,
    zone_ref: "z-front-mount",
    properties: { name: "Rocket Launcher", weight: 3, power_draw: 1, ammo: 4 },
    hints: { label_text: "Rocket Launcher" } },

  { uid: "pc-spare-armor", fragment_type: "piece", piece_id: "sa-1",
    kind: "armor", realized: true,
    zone_ref: "z-vehicle-loose",
    properties: { name: "Spare armor", weight: 2 },
    hints: { label_text: "Spare armor" } },

  // Offers (realized: false)
  { uid: "pc-flamethrower", fragment_type: "piece", piece_id: "flamethrower",
    kind: "weapon", realized: false,
    zone_ref: "z-murphs-catalog",
    properties: { name: "Flamethrower", weight: 3, power_draw: 1, ammo: 4 },
    cost: [{ ledger_key: "wallet", delta: -400, unit: "credit" }],
    available: true,
    hints: { label_text: "Flamethrower",
             description_text: "Splash damage. Burns 1 fuel per shot." } },

  { uid: "pc-rl-mk2", fragment_type: "piece", piece_id: "rl-mk2",
    kind: "weapon", realized: false,
    zone_ref: "z-murphs-catalog",
    properties: { name: "Rocket Launcher Mk II", weight: 3, ammo: 6 },
    cost: [{ ledger_key: "wallet", delta: -650, unit: "credit" }],
    available: false,
    unavailable_reason: "Out of stock until next session.",
    hints: { label_text: "Rocket Launcher Mk II" } },

  // Choices
  { uid: "f-choice-mount", fragment_type: "choice",
    edge_id: "e-mount", text: "Mount a weapon.",
    accepts: {
      kind: "place",
      source_zone_ref: "z-vehicle-loose",
      predicate_ref: "is_open_weapon_slot"
    },
    ui_hints: {
      hotkey: "1",
      drag: {                                  // genre-specific
        enabled: true,
        grab_zone_ref: "z-vehicle-loose",
        drop_zone_refs: ["z-front-mount", "z-turret", "z-back-mount"],
        preview: "capacity"
      }
    } },

  { uid: "f-choice-unmount-front", fragment_type: "choice",
    edge_id: "e-unmount-front", text: "Remove front weapon.",
    accepts: {
      kind: "pieces",
      min: 1, max: 1,
      constraints: { target_zone_ref: "z-front-mount" }
    },
    available: true,
    ui_hints: { hotkey: "2" } },

  { uid: "f-choice-buy", fragment_type: "choice",
    edge_id: "e-buy", text: "Buy from Murph's.",
    accepts: {
      kind: "pieces",
      min: 0, max: 5,
      constraints: { target_zone_ref: "z-murphs-catalog",
                     target_kind: ["weapon", "armor"] }
    },
    ui_hints: { hotkey: "3" } },

  { uid: "f-choice-leave", fragment_type: "choice",
    edge_id: "e-leave", text: "Hit the road.",
    accepts: { kind: "pick" },
    ui_hints: { hotkey: "4" } },

  { uid: "f-interpret-command", fragment_type: "choice",
    edge_id: "interpret_command", text: "Try a command.",
    accepts: { kind: "raw_command" },
    ui_hints: { hotkey: ">" } }
]
```

### Projected state — the ledger

```js
sections: [
  { section_id: "wallet", title: "Wallet", kind: "wallet",
    value: {
      value_type: "kv_list",
      items: [
        { key: "credits", value: 1240, unit: "cr" }
      ]
    } },

  { section_id: "vehicle_load", title: "Vehicle load", kind: "score",
    value: {
      value_type: "kv_list",
      items: [
        { key: "total_weight", value: 4, max: 12, unit: "stone",
          hint: "bar", emphasis: "warn" },
        { key: "front",  value: 3, max: 3, unit: "stone",
          hint: "bar", emphasis: "warn" },
        { key: "turret", value: 0, max: 4, unit: "stone", hint: "bar" },
        { key: "back",   value: 0, max: 2, unit: "stone", hint: "bar" }
      ]
    } }
]
```

### Two paths through this turn

**Click flow.** Click `front mount` in the vehicle silhouette → the
`e-unmount-front` choice expands inline → click `Rocket Launcher` →
commit. The control fragment from the next envelope moves the piece's
`zone_ref` from `z-front-mount` to `z-vehicle-loose`. Click `Buy` → the
catalog zone becomes selectable → click `Flamethrower` → click the buy
button. Backend mints `pc-flamethrower-#a3`, places it in
`z-vehicle-loose`, debits the wallet. Click `front mount` → pick
`Flamethrower`, commit.

**Drag flow.** Drag `Flamethrower` from the catalog onto `front mount`.
The web port posts two commits: `e-buy` for the offer first, waits for
the realized piece's UID, then `e-mount` with that UID as the
`piece_id`. Two commits, one gesture. The bundle's drag handler is
responsible for the choreography; the contract is unchanged.

In both flows, the CLI port sees the same envelopes and renders them
identically — just without the silhouette graphics. Per §5.3 (Input
Parity), the click flow IS the CLI floor.

### CLI port rendering of this turn

```text
Murph's Auto, end of the strip. Your Beast sits on the lift, hood up,
oil pan dripping. Murph wipes his hands on a rag and looks up. "What'll
it be today?"

[Beast — your interceptor]
  front mount: Rocket Launcher (3 stone)        [cap 1, 3/3 stone]
  turret:      empty                              [cap 1, 0/4 stone]
  back mount:  empty                              [cap 1, 0/2 stone]

[parts on hand]
  - Spare armor (2 stone)
  - Spare tire (1 stone)

[Murph's wares]
  - Flamethrower             400 cr   (3 stone, 4 ammo)
  - Armor plate              200 cr   (2 stone, +2 armor)
  - Vulcan gun               300 cr   (2 stone, 10 ammo)
  - Rocket Launcher Mk II    650 cr   (out of stock)

-- ledger --
  credits: 1240 cr
  vehicle load:
    total: 4/12 stone (warn)
    front: 3/3 stone (warn)
    turret: 0/4 stone
    back:  0/2 stone

1) Mount a weapon.
2) Remove front weapon.
3) Buy from Murph's.
4) Hit the road.
>
```

---

## 6 · Combat-resolution patterns

Carwars combat uses `RollFragment` for hit/miss/damage resolution.
A typical exchange:

### Turn N — attack choice

```js
{ uid: "f-choice-attack", fragment_type: "choice",
  edge_id: "e-attack-thug", text: "Fire the rocket launcher at the thug.",
  accepts: { kind: "pick" },
  ui_hints: {
    hotkey: "1",
    stat_check: {
      label: "Gunner check",
      dice: "2d6",
      target: 8,
      against: { piece_id: "you", property: "gunnery" },
      modifier: 1,
      success_text: "10/12 chance to hit"
    }
  }
}
```

### Turn N+1 — the roll

```js
{ uid: "f-roll-attack", fragment_type: "roll",
  label: "Gunner check",
  kind: "dice",
  inputs: {
    dice: "2d6",
    rolled: [3, 6],
    modifier: 1,
    total: 10,
    target: 8
  },
  outcome: "success",
  narrative: "The rocket streaks across the highway and detonates "
           + "against the thug's quarter panel. Sparks fly.",
  against: { piece_id: "you", property: "gunnery" },
  ritual_hints: {
    skip_label: "Skip the roll",
    auto_skip_after_seen: false,    // first roll always shown
    allow_replay: true,
    duration_ms: 1800
  }
}
```

### Damage as a follow-on roll

If hit, a damage roll follows in the same envelope (or the next):

```js
{ uid: "f-roll-damage", fragment_type: "roll",
  label: "Damage",
  kind: "dice",
  inputs: { dice: "1d6", rolled: [4], modifier: 0, total: 4 },
  outcome: "success",
  narrative: "4 points of damage.",
  ritual_hints: { duration_ms: 800, auto_skip_after_seen: true }
}
```

The `auto_skip_after_seen: true` lets later instances of the same
fragment-type-shape play instantly on replay — so the *first* damage roll
of a session is shown in full but the tenth is instant. Per §5.2, the
player can override either way.

### Combat as multi-actor rounds

For multi-actor exchanges (you vs three thugs), the bundle currently emits
one `RollFragment` per actor. A future genre extension could introduce a
typed `CombatReport` fragment that summarizes the round; for now the
prose `content` fragments between rolls carry the narration. This is
a deferred Tier P3 candidate.

---

## 7 · Edge cases — canonical responses

| Situation | Where caught | Player sees |
|---|---|---|
| Slot kind mismatch (try to mount engine in weapon slot) | client may pre-empt via `accepts_kind`; backend → `interpretation.result = "blocked"`, `blocked_reason = "Front mount only accepts weapons."` | inline transcript, slot tile flashes red |
| Capacity overflow (place exceeds weight max) | client previews via projected `kv_list` row + dragged piece's `weight`; backend → `interpretation.result = "blocked"`, `blocked_reason = "Front mount: 7 of 6 stone."` | slot bar shows projected over-fill before commit; hard error after |
| Empty catalog (shop sold out) | runtime emits `z-murphs-catalog` with `member_ids: []`; the buy choice has `available: false`, `unavailable_reason: "Shop is empty."` | catalog zone renders as `(no offers)`; choice button disabled with reason |
| Salvage min not met (must pick at least 1) | client validator on `accepts.pieces.min`; commit disabled | "pick at least one" reason chip on the commit button |
| Stat-check fail-branch (rolled below target) | next envelope's `RollFragment` with `outcome: "fail"` AND a different choice list (the fail branch) — backend's call | transcript shows roll + outcome; choice list updates |
| Stat-check crit failure | `outcome: "crit_fail"` AND optional `ritual_hints.duration_ms` extension on the bundle | same as fail; bundles MAY add a one-shot animation, but per §5.2 still skippable |
| Repair partial (paid but not enough) | backend's commit response carries an `interpretation` of the validation, OR a normal envelope with prose explaining what was repaired | transcript clarifies what was actually repaired |
| Offer no longer available (race) | next envelope updates `available: false` on the offer; client re-renders disabled row | catalog row dimmed with `unavailable_reason` |

---

## 8 · Testing patterns

### Vue component tests (Vitest + @vue/test-utils)

- `SlotZone` — render empty / occupied / over-capacity (preview);
  kind-mismatch rejection; click-pick path; drag-drop path with
  `ui_hints.drag`; reduced-motion fallback.
- `Catalog` — render `zone_role: "catalog"` with mix of available and
  unavailable offers; cost stripe; selection model; cart-roundtrip.
- `RollWidget` — render every `outcome` value the bundle uses; against-
  stat callout; reduced-motion (no shake); CLI fallback (narrative +
  inputs summary + outcome word).
- `AnnotatedKvRow` — bar / fraction / delta variants; emphasis states;
  fallback when `value` is plain scalar.

### Integration tests (Vitest + JSDOM)

- Catalog with one `available: false` offer + one whose cost exceeds the
  ledger ⇒ both rendered as disabled with reason.
- A `place` commit synthesized from click flow vs drag flow ⇒ payload
  identical (modulo timestamp).
- `RollFragment` with each `outcome` ⇒ transcript line includes literal
  outcome word; visual ritual respects reduced-motion preference.
- Skip on a `RollFragment` with `duration_ms: 1800` ⇒ canonical-instant
  rendering reaches the next-turn choices in < 100ms.

### E2E (Playwright)

- **Garage happy path.** Boot → unmount RL from front → buy Flamethrower
  from catalog → mount in front → ledger updates (weight, wallet) match
  expected.
- **Capacity overflow.** Try to add a 4-stone weapon to a 3-stone-cap
  slot ⇒ client preview shows red BEFORE commit; if the preview is
  bypassed (e.g. CLI port), backend rejects with
  `interpretation.result = "blocked"` and the slot stays unchanged.
- **Stat-check fork.** Pick a `stat_check` choice → next envelope contains
  a `RollFragment` AND a different choice list (fail branch verified).
- **Sold-out offer.** Catalog with one `available: false` offer ⇒ button
  disabled with reason text, `pc-rl-mk2` row dimmed.
- **Drag fallback.** Disable JS drag events ⇒ click-pick path still works
  end-to-end.
- **Time parity check.** Time-to-canonical-outcome on web port (skip
  invoked) ≤ CLI-port time-to-canonical-outcome + 100ms tolerance for
  every fixture in `bundles/carwars/fixtures/`.

### Conformance smoke (CI)

- For every fixture with a `zone_role: "slot"`, assert each slot has a
  `hints.label_text` and a `constraints.capacity` declaration.
- For every offer (`PieceFragment` with `realized: false`), assert
  `properties.name` is set and `cost` is either present or
  intentionally absent (salvage/quest framing).
- For every `RollFragment`, assert `outcome` is in the canonical set
  for the bundle (`{success, fail, crit_success, crit_fail}`) and
  `narrative` is present.
- For every choice with `ui_hints.drag`, assert there's an equivalent
  click-pick path producing the same commit payload (Input Parity).
- For every `RollFragment` with `ritual_hints.duration_ms > 0`, assert
  the web port's skip key produces the canonical-instant rendering.

---

## 9 · Port parity addendum (carwars-specific widgets)

| Widget | Web (Vue) | CLI | Hypothetical tk | Hypothetical map renderer |
|---|---|---|---|---|
| `SlotZone` | tile in vehicle silhouette; capacity bar; drag target | `[ slot_label: contents (cap, used/max unit) ]` | `ttk.Labelframe` + listbox | nodes on the vehicle silhouette |
| `Catalog` | card grid with cost stripes | numbered list with cost column | listbox + per-row buttons | n/a (use list view) |
| `RollWidget` | inline transcript card; one-shot tumble anim | `rolled: a + b = T → outcome` | inline `Text` widget | inline transcript card |
| Annotated kv row | bar / fraction / delta | `key: value [/ max] [unit]` | `ttk.Progressbar` for `bar` | sidebar |
| `place` choice | combined click-or-drag in silhouette | numbered two-step pick | listbox + `mount` button | click-on-silhouette |
| `unplace` choice | per-slot `×` chip | `unmount <slot>` | listbox + `unmount` button | click-on-silhouette |
| Plural cost previews | inline `·`-joined chips | `(− 120 cr · − 1 period)` | text label | tooltip |
| `stat_check` ui_hint | small badge on choice button | `[Driving 12, 2d6, +0]` suffix | `Label` next to button | overlay on map node |
| `drag` ui_hint | drag-drop interactions | (ignored) | (ignored) | drag on silhouette |

---

## Appendix — BGG mechanism coverage

The carwars bundle exercises the following BGG-top-20 game mechanisms via
the patterns above. This is informational; not contract.

| BGG mechanism | Carwars realization | Vocab elements used |
|---|---|---|
| Variable Player Powers | Vehicle stats and weapon templates | `PieceFragment.properties`, `predicate_ref` |
| Action Points | Period-based turn budgets | `cost_previews` with `unit: "period"` |
| Dice Rolling | Stat checks, damage | `RollFragment(kind="dice")`, `ui_hints.stat_check` |
| Hand Management | Inventory zones | `zone_role: "hand"`, `accepts.kind: "pieces"` |
| Set Collection | Outfitting matched weapon systems | `accepts.pieces.constraints.same_property` |
| Press Your Luck | Combat continuation choices | branching choices after `RollFragment` |
| Resource Management | Wallet, weight, ammo | annotated `kv_list` with `max`/`hint: "bar"` |
| Variable Phase Order | Combat initiative | per-turn `metadata` ordering hints (advisory) |
| Modular Board | Map-zone variants | `zone_role: "field"` + `layout_hints.graph` |
| Income | Per-turn credit grants | projected `kv_list` deltas with `hint: "delta"` |

Mechanisms requiring more than the above (bidding, area control, pattern
building) are open candidates for genre-extension work; some depend on
`predicate_ref` registration (main spec §7.4).

---

*End of carwars EXTENSIONS v0.4.*
