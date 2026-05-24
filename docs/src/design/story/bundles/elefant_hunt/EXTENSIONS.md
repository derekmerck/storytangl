# Elefant Hunt Bundle — Widget Vocabulary Extensions

**Bundle id:** `elefant_hunt`
**Vocab spec base:** `STORYTANGL_WIDGET_VOCAB.md` v1.5
**Status:** draft v0.2 · aligned to v1.5 core vocabulary
**Genre:** graph-traversal sandbox board game ("inspired by Tom Wham's *Elefant Hunt*, Dragon Magazine #88, 1984")
**Engine reference:** `BOARD_GAME_SANDBOX_DESIGN.md`
**Audience:** authors writing graph-traversal sandbox bundles; port implementers covering the elefant_hunt profile suite

This document is a **Tier P3 genre extension** (per main spec §8). It
introduces no new top-level vocabulary; it codifies conventions on top
of v1.5 for graph-traversal sandbox / board-game gameplay.

It is also the spec's **worked proof-of-concept for the journal-as-story
claim** (§0.8): a board game whose mechanics produce a recognizable
Proppian arc transcript from procedural mechanics, without authored
fiction beyond per-location flavor.

---

## 0 · Genre summary

Graph-traversal sandbox games model **traversal of a typed location
graph with mechanical encounters**: the player moves through a
directed graph of named locations, draws random outcomes from
backend-private pools, accumulates assets, and returns to scoring
locations. The board is not a hex grid — it is a *graph*, with
typed nodes and typed edges. Movement is choice-among-exits, not
position-on-grid.

**Three orthogonal patterns** the genre exercises:

| Pattern | Main spec mechanism | Genre layer adds |
|---|---|---|
| Graph board with typed locations | `zone` group with `layout_hints.graph={nodes, edges}` | conventional location `kind` tags (`port`, `hazard`, `hunting_ground`, `graveyard`, `lost_city`, `trail`, `junction`) |
| Backend-private random pool | engine-side `TokenPool` (contract-invisible) + `RollFragment(kind="custom")` for outcomes | the canonical example of §0.3 backend authority — the client never sees pool composition |
| Composite encounter resolution | `RollFragment(kind="custom")` with structured `inputs` and `outcome` | auto-assign vs. interactive-assign as two conforming variants |

This bundle is also the worked proof-of-concept for §0.8 journal-as-
story (see §6 below).

---

## 1 · Domain vocabulary mapped to v1.5

| Elefant Hunt concept | v1.5 surface |
|---|---|
| Board | `GroupFragment(group_type="zone", zone_role="board")` with `layout_hints.graph={nodes, edges}` |
| Location (port, trail, hazard, junction, hunting ground, graveyard, lost city) | Sub-zone of the board, with `kind` tag carrying the location type; `hints.label_text` for the player-facing name |
| Exit | `Edge` entry in `layout_hints.graph.edges` with stable UID, `kind` (`clockwise`, `return`, `left`, `right`, `probabilistic`), and `predicate_ref` for parity-gated branches |
| Hunter (hired mob) | `PieceFragment(kind="hunter")` with `owner=cursor_id` (multi-cursor) or `null` (single-cursor); `properties: {name, hunting_value, status}`; lives in the expedition zone, removed via `delete` on loss |
| Animal (captured) | `PieceFragment(kind="animal")` with `properties: {species, point_value, is_killer}`; lives in expedition zone until scored |
| Ivory marker | `PieceFragment(kind="ivory")` with `properties: {value: null}` until scored at port |
| Relic marker | `PieceFragment(kind="relic")` with `properties: {value: null}` until scored at port |
| Supply | `ProjectedState` `kv_list` row keyed by `supplies`, `hint="bar"`, `max` set per starting port |
| Score | `ProjectedState` `scalar` with `kind="score"`, per-cursor; incremented at port returns |
| Animal pool (engine `TokenPool`) | **Engine state. NOT in the UI contract.** Client sees only `RollFragment.inputs.drawn` on hunt resolution. |
| Movement | `ChoiceFragment(accepts.kind="pick")` over the location's open exits |
| Hazard resolution | `RollFragment(kind="dice")` + conditional `update`/`delete` control fragments |
| Hunt resolution | `RollFragment(kind="custom")` with structured `inputs` and `outcome`; one fragment per encounter |
| Random event / encounter table | `RollFragment(kind="table")` with `inputs: {table_id, row, label}` |
| Port scoring | Backend computes; emits a `RollFragment` per ivory/relic (3d6 valuation) plus `update` to score; `delete`s scored assets; `update` resets supplies |

---

## 2 · Board topology

The board is a single zone with `layout_hints.graph`. Each location is
its own sub-zone (so it has an addressable UID, a `kind`, and a
`label_text`). Edges have stable UIDs.

```js
{
  uid: "z-board",
  fragment_type: "group",
  group_type: "zone",
  zone_role: "board",
  member_ids: [
    "z-port-stanley", "z-trail-1", "z-river-crossing", "z-trail-2",
    "z-hunting-ground-3", "z-albert-falls", "z-elefant-graveyard",
    "z-lost-city", "z-port-livingston", /* ... */
  ],
  layout_hints: {
    graph: {
      nodes: ["z-port-stanley", "z-trail-1", /* ... */],
      edges: [
        { uid: "e-stanley-trail1", a: "z-port-stanley", b: "z-trail-1",
          kind: "clockwise" },
        { uid: "e-trail1-river", a: "z-trail-1", b: "z-river-crossing",
          kind: "clockwise" },
        { uid: "e-albert-left", a: "z-albert-falls", b: "z-hunting-ground-4",
          kind: "left" },
        { uid: "e-albert-right", a: "z-albert-falls", b: "z-lost-city",
          kind: "right" },
        { uid: "e-quicksand-even", a: "z-quicksand", b: "z-trail-3",
          kind: "probabilistic", predicate_ref: "die_even" },
        { uid: "e-quicksand-odd", a: "z-quicksand", b: "z-lost-marker",
          kind: "probabilistic", predicate_ref: "die_odd" }
      ]
    }
  },
  hints: { label_text: "The expedition map" }
}
```

**Location sub-zones** carry their semantic role in `kind`:

```js
{
  uid: "z-port-stanley",
  fragment_type: "group",
  group_type: "zone",
  member_ids: ["pc-port-clerk", "z-stanley-catalog"],
  kind: "port",
  hints: { label_text: "Port Stanley",
           style_tags: ["scoring-location", "resupply"] }
}

{
  uid: "z-river-crossing",
  fragment_type: "group",
  group_type: "zone",
  member_ids: [],
  kind: "hazard",
  hints: { label_text: "River crossing",
           style_tags: ["probabilistic-hazard"] }
}

{
  uid: "z-hunting-ground-3",
  fragment_type: "group",
  group_type: "zone",
  member_ids: [],
  kind: "hunting_ground",
  properties: { encounter_size: 3 },
  hints: { label_text: "Watering hole" }
}
```

**Conventional location `kind` tags:**

| Kind | Meaning | CLI prefix glyph |
|---|---|---|
| `port` | Scoring, resupply, hire | `⚓` |
| `trail` | Empty transit; consumes supplies | `·` |
| `hazard` | Probabilistic or guaranteed loss | `!` |
| `junction` | Player chooses next direction | `▲` |
| `hunting_ground` | Encounter draws from animal pool | `🏹` (or `*`) |
| `graveyard` | Special reward + cost | `†` |
| `lost_city` | Special reward + cost | `🛕` (or `#`) |

**Conventional edge `kind` tags:**

| Kind | Meaning |
|---|---|
| `clockwise` | Forward along the standard route |
| `return` | Direct return path (typically to nearest port) |
| `left` / `right` | Player choice at junction |
| `probabilistic` | Backend evaluates `predicate_ref` (typically die-parity) |

---

## 3 · Movement

Movement is `accepts.kind="pick"` over the current location's
available exits. The cursor moves; no piece is placed.

```js
{
  uid: "f-choice-move",
  fragment_type: "choice",
  edge_id: "e-clockwise",   // matches the edge UID
  text: "Continue clockwise to the watering hole.",
  accepts: { kind: "pick" },
  ui_hints: { hotkey: "1", emphasis: "primary" }
},
{
  uid: "f-choice-return",
  fragment_type: "choice",
  edge_id: "e-return-stanley",
  text: "Turn back to Port Stanley.",
  accepts: { kind: "pick" },
  ui_hints: { hotkey: "2", emphasis: "subtle" }
}
```

**Hazardous exits** carry `ui_hints.emphasis: "warning"` or
`"danger"` so the CLI's `(!)` markers and the web's color treatment
both surface the risk. Per main spec §5.1 Decision Legibility, the
hazard's nature is rendered as a `kv_list` row in the location's
status or in projected state ("Probabilistic: 1-in-6 lose an
animal").

**At junctions**, the player gets one choice per direction; at
probabilistic splits, the backend evaluates the predicate and emits
just *one* exit choice (or none — the result is forced).

### `ui_hints.encounter_check` optional preview

Hazardous or probabilistic movement choices MAY advertise the visible
part of the risk with a genre-specific hint:

```python
class EncounterCheckHint(BaseModel):
    label: str                            # "River crossing"
    risk_text: str | None = None          # "1-in-6 lose an animal"
    predicate_ref: str | None = None      # opaque backend predicate id
    consequence_text: str | None = None   # player-facing consequence summary
```

This is not a client-side roll. It is an advisory display over the same
backend-authoritative `predicate_ref` and `RollFragment` flow described
in the main spec. CLI ports render it as a short suffix; richer ports
may badge or color the exit.

---

## 4 · Hunters as mobs

```js
{
  uid: "pc-zartan",
  fragment_type: "piece",
  piece_id: "hunter-zartan",
  kind: "hunter",
  owner: null,  // single-cursor; multi-cursor sets cursor_id
  zone_ref: "z-expedition",
  properties: {
    name: "Zartan",
    hunting_value: 4,
    status: "fit"  // "fit" | "injured" | "lost"
  },
  hints: { label_text: "Zartan (HV 4)" }
}
```

**Loss is a `delete` control fragment.** When a hazard kills a hunter,
the backend emits:

```js
{ uid: "f-loss-zartan", fragment_type: "control",
  ref_type: "fragment", ref_id: "pc-zartan",
  // no payload; this is a delete
  fragment_type: "delete" }
```

Accompanied by a `content` fragment with the narrative: "The river
takes Zartan. The rest of the expedition presses on."

Per §0.8 journal-as-story, narrative `content` accompanies every
narratively significant state change. The CLI transcript reads as
prose.

---

## 5 · The hunt — composite RollFragment

The hunt resolution is the most complex single fragment in this
bundle. Per the engine design, the hunt is **one resolution event,
not a game loop** — it produces a single `RollFragment(kind="custom")`
with structured inputs and outcome.

```js
{
  uid: "f-roll-hunt-3",
  fragment_type: "roll",
  label: "Hunt at the watering hole",
  kind: "custom",
  inputs: {
    drawn: [
      { species: "hippo",  point_value: 6, is_killer: true },
      { species: "zebra",  point_value: 2, is_killer: false },
      { species: "vulture", point_value: 1, is_killer: false }
    ],
    assignments: [
      { hunter: "Zartan",  target: "hippo",   d6: 5, total: 9 },
      { hunter: "Ned Net", target: "zebra",   d6: 3, total: 5 },
      { hunter: "Skip",    target: "vulture", d6: 1, total: 2 }
    ],
    captures: ["hippo"],
    escapes: ["zebra", "vulture"],
    casualties: []
  },
  outcome: "mixed_success",
  narrative: "You spot a hippo and two zebras—no, a zebra and a
              vulture, circling. Zartan brings the hippo down with a
              clean shot. Ned Net's zebra slips through the reeds.
              Skip rolls a one; the vulture takes wing and is gone.",
  ritual_hints: {
    skip_label: "Skip the hunt",
    duration_ms: 2400,
    allow_replay: true
  }
}
```

**Two conforming variants:**

1. **Auto-assign** (MVP per engine design): the backend greedily
   assigns hunters to animals by `hunting_value` and emits the
   `RollFragment` with `assignments` populated. Player has no
   pre-roll choice; the hunt just resolves.

2. **Interactive assign**: the prior envelope contains a
   `ChoiceFragment(accepts.kind="compose")` with N parts, one per
   drawn animal:

   ```js
   {
     accepts: {
       kind: "compose",
       parts: [
         { role: "hippo_assignment",
           accepts: { kind: "pieces", min: 1, max: 1,
                      constraints: { target_zone_ref: "z-expedition",
                                     target_kind: ["hunter"] } } },
         { role: "zebra_assignment",
           accepts: { kind: "pieces", min: 1, max: 1,
                      constraints: { target_zone_ref: "z-expedition",
                                     target_kind: ["hunter"] } } },
         /* ... */
       ]
     }
   }
   ```

   After commit, the resolution `RollFragment` fires.

**Engine `TokenPool` is invisible.** The client never sees the animal pool's
composition. `inputs.drawn` materializes only the animals actually
drawn for this encounter. Per §0.3 backend authority, the client
renders what's given; pool state is engine territory.

This is the canonical worked example for §0.3.

---

## 6 · Hazard examples

### River Crossing (probabilistic loss)

Backend emits on entry:

```js
[
  { uid: "f-prose-river", fragment_type: "content",
    content: "The river runs fast and brown. You wade in, supplies held high." },

  { uid: "f-roll-river", fragment_type: "roll",
    label: "River crossing",
    kind: "dice",
    inputs: { dice: "1d6", rolled: [6], target: 6 },
    outcome: "failure",  // a 6 means loss in original Wham rules
    narrative: "A zebra is lost to the current.",
    ritual_hints: { duration_ms: 1000 } },

  { uid: "f-loss-zebra", fragment_type: "control",
    ref_type: "fragment", ref_id: "pc-animal-zebra-1",
    fragment_type: "delete" },

  // proceed to next location
  { uid: "f-choice-next", fragment_type: "choice",
    edge_id: "e-trail-3",
    text: "Continue along the trail.",
    accepts: { kind: "pick" },
    ui_hints: { hotkey: "1", emphasis: "primary" } }
]
```

### Albert Falls (mandatory next-turn junction)

Albert Falls is a junction whose exits are *suppressed until the
next turn*. Per §0.6 narrative authoring stance, this is the
backend authoring state on demand: the player arrives, the backend
emits a content fragment and no choices, then the next envelope
opens both junction exits.

```js
// Arrival envelope
[
  { uid: "f-prose-albert", fragment_type: "content",
    content: "Albert Falls roars below. You make camp at the cliff's
              edge, considering your next move." }
  // No choices — cursor is parked
]

// Next-turn envelope
[
  { uid: "f-choice-left", fragment_type: "choice",
    edge_id: "e-albert-left", text: "Take the western path.",
    accepts: { kind: "pick" }, ui_hints: { hotkey: "1" } },
  { uid: "f-choice-right", fragment_type: "choice",
    edge_id: "e-albert-right", text: "Take the eastern path.",
    accepts: { kind: "pick" }, ui_hints: { hotkey: "2" } }
]
```

The client doesn't know exits will be suppressed; it just renders
what's in the envelope. Per §0.3 / §0.6, the contract surface is the
rendered turn, not a world-model query.

### Elefant Graveyard (special: cost + reward)

```js
[
  { uid: "f-prose-graveyard", fragment_type: "content",
    content: "Bones, white and vast, scatter the clearing. The smell of
              old grass and older time." },

  // Cost: lose one elefant if held
  { uid: "f-elefant-loss", fragment_type: "control",
    ref_type: "fragment", ref_id: "pc-animal-elefant-1",
    fragment_type: "delete" },
  { uid: "f-prose-loss", fragment_type: "content",
    content: "The young elefant breaks free at the sight and crashes into
              the trees." },

  // Reward: ivory marker
  { uid: "pc-ivory-1", fragment_type: "piece",
    piece_id: "ivory-1", kind: "ivory",
    zone_ref: "z-expedition",
    properties: { value: null },  // resolved at port scoring
    hints: { label_text: "Ivory marker" } },
  { uid: "f-prose-ivory", fragment_type: "content",
    content: "You pry loose a tusk fragment. It will fetch something at
              market." }
]
```

---

## 7 · Port scoring

At port return, the backend emits a sequence of `RollFragment`s for
ivory and relic valuations (3d6 each), aggregates the score, and
`delete`s the scored assets.

```js
[
  { uid: "f-prose-return", fragment_type: "content",
    content: "Port Stanley. The harbormaster greets you with a ledger." },

  { uid: "f-roll-ivory-1", fragment_type: "roll",
    label: "Ivory appraisal",
    kind: "dice",
    inputs: { dice: "3d6", rolled: [5, 4, 6], total: 15 },
    outcome: "success",
    narrative: "The ivory weighs out at 15 points." },

  { uid: "f-roll-relic-1", fragment_type: "roll",
    label: "Relic appraisal",
    kind: "dice",
    inputs: { dice: "3d6", rolled: [2, 1, 3], total: 6 },
    outcome: "modest",
    narrative: "The artifact is curious but not valuable: 6 points." },

  // Apply score
  { uid: "f-score-update", fragment_type: "control",
    ref_type: "section", ref_id: "score",
    payload: { value: { value_type: "scalar", value: 47 } } },

  // Delete scored assets
  { uid: "f-del-ivory", fragment_type: "control",
    ref_type: "fragment", ref_id: "pc-ivory-1",
    fragment_type: "delete" },
  { uid: "f-del-relic", fragment_type: "control",
    ref_type: "fragment", ref_id: "pc-relic-1",
    fragment_type: "delete" },

  // Reset supplies, offer next expedition
  { uid: "f-choice-next", fragment_type: "choice",
    edge_id: "e-resupply",
    text: "Resupply and depart again (consumes 4 stamina).",
    accepts: { kind: "pick" }, ui_hints: { hotkey: "1" } },
  { uid: "f-choice-end", fragment_type: "choice",
    edge_id: "e-end-session",
    text: "End the expedition.",
    accepts: { kind: "pick" }, ui_hints: { hotkey: "2", emphasis: "subtle" } }
]
```

---

## 8 · Solitaire mode — beat the blind

Solo play variant. A target score is drawn at game start and revealed
at session end. The bundle MAY surface the target as a `ProjectedState`
section with `kind="target"`, value hidden behind a placeholder until
revealed:

```js
{
  section_id: "target",
  title: "Par",
  kind: "target",
  value: { value_type: "scalar", value: "—" },
  hints: { style_tags: ["hidden-until-reveal"] }
}
```

At session end, the backend emits a `control` updating `value` to the
revealed par, then renders the win/loss commentary.

---

## 9 · Multi-cursor framing (Tier P1 target)

Per main spec §1.5 (Tier P1), each player is a cursor with their own
channel. Single-cursor hot-seat is the v1.x reality; multi-cursor is
the future direction once §1.5 graduates.

**Single-cursor hot-seat:** the bundle emits "Pass the keyboard to
Player Red" content fragments between turns. Each player's score and
expedition are projected with `kind="score_<player_name>"` so all
players can see all scores.

**Multi-cursor target:** per §1.5 per-cursor projection of shared
state:

- The board is shared world state. Each cursor sees the board zone
  in its envelopes.
- Each hunter `PieceFragment` carries `owner=<cursor_id>`. Cursor
  A sees their own hunters and (per `visibility="public"`) the
  positions of other cursors' parties.
- The animal pool stays engine state (the `TokenPool`); no cursor
  sees pool composition.
- When cursor A captures animals, cursor B's channel receives a
  `delete` for the relevant encounter zone members and a `content`
  fragment narrating the capture ("Hunter Red bags a hippo at the
  north watering hole.").
- Score projections are per-cursor; the projected `kv_list` of
  *all* players' scores is also visible to every cursor.

**Ape Man as cross-cursor interaction.** Per the engine design, the
Ape Man rule lets one player's interaction modify another player's
inventory. Implementation: the affected cursor receives a control
fragment authored by the other cursor's commit. This is the one
genuine cross-cursor mechanism, and it falls cleanly under §1.5's
"backend coordinates shared world state."

---

## 10 · The journal-as-story validation

Per main spec §0.8, this bundle is the worked proof-of-concept for
the journal-as-story claim. The test:

1. Run a complete expedition through `cli_reference_port.py`.
2. Capture stdout.
3. Read the result.

**Expected transcript shape** (per the design doc, slightly
formalized):

```
Port Stanley. The harbormaster greets you with a ledger. You hire
two hunters and load four days of supplies.

  1) Set off into the interior.
  > 1

You move deeper into the interior. Camp. Consumed 1 supply.

  1) Continue to the river.
  > 1

The river runs fast and brown. You wade in, supplies held high.
  [River crossing]  rolled 6 / target 6
  A zebra is lost to the current.

  1) Continue along the trail.
  > 1

You move deeper still. Camp. Consumed 1 supply.

  1) Approach the watering hole.
  > 1

You spot a hippo and two zebras—no, a zebra and a vulture, circling.
Zartan brings the hippo down with a clean shot. Ned Net's zebra slips
through the reeds. Skip rolls a one; the vulture takes wing and is
gone.

  [Hunt at the watering hole]
    captures: hippo
    escapes:  zebra, vulture

  1) Continue clockwise.
  2) Turn back to Port Stanley.
  > 2

[long return journey, abbreviated]

Port Stanley. The harbormaster greets you with a ledger.

  [Ivory appraisal]  rolled 5 + 4 + 6 = 15
  The ivory weighs out at 15 points.

Expedition returns to Port Stanley. Score: 21 points.

  1) Resupply and depart again (consumes 4 stamina).
  2) End the expedition.
```

**The claim:** this transcript reads as a naturalist's field notes
or a pulp adventure log — without any prose beyond per-location
flavor and outcome narratives. The Proppian arc (departure → trials
→ boons → return → recognition) emerges from graph topology and
fragment sequencing.

**The test:** check this transcript in
`engine/contrib/conformance/transcripts/elefant_hunt_one_expedition.txt`
and update with each bundle revision. The smoke-test assertion: a
human reader recognizes it as a story.

This is also the artifact to point at when explaining StoryTangl to
outsiders: "this is what falls out, with no extra authoring."

---

## 11 · Port parity addendum

| Widget | Web (Vue) | CLI | tkinter | Hypothetical Godot |
|---|---|---|---|---|
| Board zone | graph diagram with location nodes | `[map]` ascii sketch + current-location marker | `Canvas` with nodes | 3D scene, top-down camera |
| Location (active) | highlighted node + nameplate | location heading + `[<kind>]` tag | bordered `Frame` | spotlight + camera focus |
| Exit choice | button per exit | `<n>) <text>` | `Button` | clickable path |
| Hunter piece | portrait chip with HV badge | `<name> (HV <n>)` line | small portrait card | NPC actor |
| Animal captured | thumbnail in expedition tray | line in expedition list | small icon | inventory shelf |
| Hazard roll | one-shot animation + result | inline outcome line | brief flash + label | rolling die overlay |
| Hunt roll | composite animation (draw, assign, resolve) | structured block with sections | tabbed `Frame` per phase | cinematic sequence |
| Score | tile with number + delta | line: `score: <n>` | large `Label` | scoreboard prop |
| Multi-cursor turn pass | "Pass to Player X" banner | line: `--- Pass to <name> ---` | modal `Toplevel` | curtain transition |

---

## Appendix — Prior art

Tom Wham's *Elefant Hunt* (Dragon Magazine #88, 1984) is the
namesake. Wham's design DNA traces through *Snit's Revenge* (1977),
*The Awful Green Things from Outer Space* (1979), and his other
magazine-insert games — all characterized by compact rules, named
locations carrying narrative weight, and dice-driven mechanics that
generate quotable session stories.

Adjacent designs the vocabulary supports: *Magic Realm* (1979) with
its tiled exploration map; *Tales of the Arabian Nights* (1985) with
its encounter-table-driven narrative; *Hellboy: The Board Game* (2019)
with its mission-graph traversal. Modern legacy / campaign games
(*Pandemic Legacy*, *Gloomhaven*) share the directed-graph-with-
typed-locations DNA at a higher complexity ceiling.

**Reframing the colonial premise.** The original Elefant Hunt is a
1980s safari game and shows it. The mechanics support a contemporary
reframing as **wildlife conservation / ecotourism / nature
photography**: animals are captured *alive*, lost animals are
penalized, and the Ape Man's explicit role is animal liberation.
"Elefant Ecotourism" or "wildlife survey" fits the same graph and
the same pool draws. The genre profile is medium-neutral; the
narrative skin is bundle-authored.

The engine-side architecture (`SandboxScope`, `SandboxLocation`,
`SandboxExit`, `SandboxMob`, `TokenPool`) is documented in
`BOARD_GAME_SANDBOX_DESIGN.md`. The engine-side abstractions are
authoring concerns; this document is rendering contract. **The
TokenPool, in particular, is contract-invisible** — clients never see
it directly, only its draw outcomes. This is the canonical example
of §0.3 backend authority working under pressure.

---

*End of elefant_hunt EXTENSIONS v0.1.*
