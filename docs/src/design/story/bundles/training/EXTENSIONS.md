# Training Bundle — Widget Vocabulary Extensions

**Bundle id:** `training`
**Vocab spec base:** `STORYTANGL_WIDGET_VOCAB.md` v1.5
**Status:** draft v0.2 · aligned to v1.5 core vocabulary
**Genre:** scheduled skill progression / succession-game (*Long Live the Queen*-inspired)
**Grounded in:** `worlds/coronate_the_regent` (StoryTangl demo world)
**Audience:** authors writing training-style bundles; port implementers covering the training profile suite

This document is a **Tier P3 genre extension** (per main spec §8). It
introduces no new top-level vocabulary; it codifies conventions on top
of v1.5 for scheduled-training gameplay.

The training-specific enrichments are advisory labels and previews over
core choices, projected rows, pieces, and rolls. A client that ignores
the skill-category styling or stat-check preview still conforms when it
renders the same choices and backend-authored outcomes.

---

## 0 · Genre summary

Training bundles model **scheduled accumulation with gated payoffs**:
the player makes repeated choices about how to spend a constrained
resource (study weeks, training periods, lessons), accumulates skills /
inventory / flags, and meets pre-scheduled events whose outcomes
depend on accumulated state.

The reference instance is `worlds/coronate_the_regent`: four weeks,
two skills (combat, charm), two scheduled events (prince audience,
dragon fight), one inventory unlock (dragonslayer sword), plus a
mood-as-tag-modifier mechanic. This document describes what the demo
*currently* exercises and the conventions it establishes. Forward
direction (full LLtQ-style skill trees, calendar widgets, per-skill
XP curves) is acknowledged as Tier P3 *aspirational* — not in scope
for the current contract.

**Three orthogonal patterns** the training genre exercises:

| Pattern | Main spec mechanism | Genre layer adds |
|---|---|---|
| Repeated constrained choices (study weeks) | `ChoiceFragment(accepts.kind="pick")` for two-option weeks; `compose` for richer schedules | conventional `ui_hints.emphasis` per skill category |
| Scheduled event with skill check | `RollFragment(kind="dice", against: {piece_id, property})` | `ui_hints.stat_check` preview on the triggering choice (carwars convention reused) |
| Conditional outcome routing | Backend evaluates `_conditions` on continues; next envelope reflects branch | `ProjectedState` deltas + `KvRow.delta` previews show what changed |

---

## 1 · Domain vocabulary mapped to v1.5

| Training concept | v1.5 surface |
|---|---|
| Player (regent / heir / pupil) | The cursor; not a piece. Player stats are `ProjectedState` `kv_list` rows. |
| Stat (intrinsic: body, mind, spirit) | `ProjectedState` row keyed by stat name, with `hint="bar"` and `max` populated |
| Skill (governed: combat, magic, charm) | `ProjectedState` row keyed by skill name, with `hint="bar"`. Author MAY also surface as `PieceFragment(kind="skill")` in a skill-tree zone when richer rendering wanted. |
| Mood | `ProjectedState` `scalar` with `kind="mood"`, value = mood name; alternatively a `kv_list` row with `emphasis` highlighting active mood |
| Wallet (coin, stamina) | `ProjectedState` `kv_list` with `hint="bar"` rows |
| Inventory (dragonslayer sword, flags) | Either inventory `kv_list` with `BadgeListValue` for flags, OR a zone of `PieceFragment(kind="item")` for richer rendering |
| Week / schedule | `ProjectedState` `scalar` ("Week 2 of 4") or `kv_list` with annotated rows |
| Study choice | `ChoiceFragment(accepts.kind="pick")` for two-option weeks; `accepts.kind="compose"` for richer multi-period weeks (forward direction) |
| Scheduled event | A non-choice envelope sequence; the player's choice happened on the prior turn (e.g., "Receive the visiting prince" vs. "Train at arms"), and this envelope resolves the consequence |
| Skill check | `RollFragment(kind="dice")` with `against: {piece_id: "player", property: <stat_name>}` and `inputs` describing the difficulty |
| Inventory unlock | `update` control fragment adding a flag to the inventory `BadgeListValue`, OR a new `PieceFragment(kind="item", realized=True)` appearing in the inventory zone |
| Outcome branch | The backend evaluates conditions; the next envelope reflects whichever branch fired |
| Ending | Sequential `content` + `attributed` fragments; projected sections frozen at terminal state |

---

## 2 · Mood as growth modulator

`worlds/coronate_the_regent` introduces a clever mechanic:
**mood doesn't gate skills; it modulates training gains per tag.**

```python
# excerpt from coronate_the_regent.domain
MOOD_EFFECTS = {
    "martial": [
        SituationalEffect(applies_to_tags={"#martial"}, growth_modifier=1.0),
        SituationalEffect(applies_to_tags={"#courtly"}, growth_modifier=-0.5),
    ],
    "studious": [
        SituationalEffect(applies_to_tags={"#courtly"}, growth_modifier=1.0),
    ],
}
```

The rendering convention: **mood projects as both a state indicator
AND as cost-preview deltas on each affected study choice**.

```js
// projected mood scalar
{
  section_id: "mood",
  title: "Mood",
  kind: "mood",
  value: { value_type: "scalar", value: "martial" },
  hints: { icon: "sword", style_tags: ["mood-indicator"] }
}

// study choice surfaces the mood-adjusted preview
{
  uid: "f-choice-combat",
  fragment_type: "choice",
  edge_id: "e-train-combat",
  text: "Train at arms",
  accepts: { kind: "pick" },
  ui_hints: {
    hotkey: "1",
    cost_previews: [
      { ledger_key: "skills.combat", delta: 2, unit: "xp" }
    ],
    stat_check: null  // no check, just a gain preview
  }
}

{
  uid: "f-choice-charm",
  fragment_type: "choice",
  edge_id: "e-train-charm",
  text: "Study courtly graces",
  accepts: { kind: "pick" },
  ui_hints: {
    hotkey: "2",
    cost_previews: [
      { ledger_key: "skills.charm", delta: 1, unit: "xp" }  // halved by martial mood
    ]
  }
}
```

**`cost_previews.delta` carries positive values for gains.** Per the
v1.5 spec, `CostPreview.delta` is signed; the name "cost" is
historical. A bundle showing a gain preview MAY render the user-
facing text as "+2 combat" while the contract field stays
`cost_previews`. Do not invent `gain_previews`.

**The mood-modulated value is computed backend-side.** The client
renders what the backend tells it. If the player has martial mood,
the preview for charm-training shows the *modulated* gain (`+1`,
half of the base `+2`), not the unmodulated number. This is §0.3
backend authority: the math is the backend's, the rendering is the
client's, and the contract surface is the rendered preview.

---

## 3 · Scheduled events and skill checks

A scheduled event is just the next envelope in the sequence, whose
content reflects whichever branch the prior choice took. The check
is a `RollFragment(kind="dice")` with `against` referencing a stat.

```js
// envelope after player chose "Receive the visiting prince"
fragments: [
  { uid: "f-prose-prince", fragment_type: "content",
    content: "The prince watches you across the receiving hall. The
              guards lower their eyes. You step forward and bow." },

  // The skill check fires immediately
  { uid: "f-roll-audience", fragment_type: "roll",
    label: "Prince's audience",
    kind: "dice",
    inputs: {
      dice: "1d20",
      rolled: [14],
      modifier: 0,
      total: 14,
      target: 10,    // computed backend-side from prince difficulty + charm
      probability_text: "12/20"
    },
    outcome: "success",
    narrative: "The prince leaves visibly charmed by your bearing.",
    against: { piece_id: "player", property: "charm" },
    ritual_hints: {
      skip_label: "Skip the roll",
      auto_skip_after_seen: false,
      duration_ms: 1400
    } },

  // Result: an inventory flag is set
  { uid: "f-inv-update", fragment_type: "control",
    ref_type: "section", ref_id: "inventory",
    payload: {
      value: {
        value_type: "badges",
        items: ["impressed_prince"]   // added to existing badges
      }
    } },

  // Next-turn choice list
  { uid: "f-choice-next", fragment_type: "choice",
    edge_id: "e-week3",
    text: "Begin Week 3.", accepts: { kind: "pick" },
    ui_hints: { hotkey: "1", emphasis: "primary" } }
]
```

**The fork lives on the backend.** If the audience had failed, the
next envelope would have skipped the `impressed_prince` flag and
proceeded directly to week 3. Per spec §7.3, the player has nothing
to decide about the roll itself; the ritual is skippable per §5.2
Time Parity.

### `ui_hints.stat_check` preview (carwars convention reused)

When a *prior* choice triggers the check, surfacing the difficulty
helps the player understand the wager. Reused directly from carwars
EXTENSIONS:

```js
{
  uid: "f-choice-audience",
  fragment_type: "choice",
  edge_id: "e-receive-prince",
  text: "Receive the visiting prince",
  accepts: { kind: "pick" },
  ui_hints: {
    hotkey: "1",
    stat_check: {
      label: "Audience",
      dice: "1d20",
      target: 10,
      against: { piece_id: "player", property: "charm" },
      modifier: 0,
      success_text: "12/20 chance"
    }
  }
}
```

CLI rendering:

```
1) Receive the visiting prince  [Audience: 1d20 vs charm, 12/20]
```

---

## 4 · Inventory unlocks

The dragonslayer sword pattern: a purchase, an inventory mutation, a
downstream effect.

```js
// At the merchant: the offer
{
  uid: "f-offer-sword",
  fragment_type: "piece",
  piece_id: "dragonslayer-sword",
  kind: "weapon",
  realized: false,
  properties: { name: "Dragonslayer sword", description: "Said to slay dragons." },
  cost: [{ ledger_key: "coin", delta: -3 }],
  available: true,
  hints: { label_text: "Dragonslayer sword" }
}

// Buy choice
{
  uid: "f-choice-buy-sword",
  fragment_type: "choice",
  edge_id: "e-buy-sword",
  text: "Buy the dragonslayer sword (3 coin)",
  accepts: {
    kind: "pieces", min: 1, max: 1,
    constraints: { target_zone_ref: "z-merchant-catalog" }
  },
  blockers: [
    {
      code: "insufficient_coin",
      message: "You only have 2 coin.",
      refs: ["coin"]
    }
  ],
  available: false  // when player has < 3 coin
}
```

After commit, the next envelope:

```js
[
  { uid: "pc-sword-realized", fragment_type: "piece",
    piece_id: "dragonslayer-sword", kind: "weapon",
    realized: true,
    zone_ref: "z-inventory",
    properties: { name: "Dragonslayer sword" },
    hints: { label_text: "Dragonslayer sword" } },

  { uid: "f-content-buy", fragment_type: "content",
    content: "The merchant pockets your coin and hands you the sword.
              It is heavier than you expected." },

  // wallet projection updates by way of next envelope's ProjectedState
  // (no control fragment needed — ProjectedState is re-projected per turn)
]
```

**Effect on downstream rolls.** Per `coronate_the_regent`, holding
the sword causes the dragon-fight check to fire with `forced_outcome:
MAJOR_SUCCESS`. The client never sees this rule directly — the dragon
check's `RollFragment.outcome` simply reads `"success"`, with no
explanation of why. Per §0.3 / §0.6 backend authority and narrative
authoring stance, this is exactly right: the mechanism is invisible
to the client, the outcome is canonical.

---

## 5 · Weekly study commit (richer compose form)

`coronate_the_regent` uses `accepts.kind="pick"` for its two-option
weeks. A richer training bundle (full LLtQ-style "morning study +
afternoon study") uses `compose`:

```js
{
  uid: "f-choice-week",
  fragment_type: "choice",
  edge_id: "e-week5-schedule",
  text: "Plan Week 5",
  accepts: {
    kind: "compose",
    parts: [
      {
        role: "morning",
        accepts: {
          kind: "pieces",
          min: 1, max: 1,
          constraints: { target_zone_ref: "z-available-courses" }
        }
      },
      {
        role: "afternoon",
        accepts: {
          kind: "pieces",
          min: 1, max: 1,
          constraints: { target_zone_ref: "z-available-courses" }
        }
      }
    ]
  }
}
```

The commit payload:

```json
{
  "edge_id": "e-week5-schedule",
  "payload": {
    "parts": {
      "morning":   { "piece_ids": ["course-rhetoric"] },
      "afternoon": { "piece_ids": ["course-economics"] }
    }
  }
}
```

This is forward direction — coronate_the_regent doesn't yet use it,
but the contract is ready when a bundle does.

---

## 6 · Worked example — Week 2 of coronate_the_regent

### Envelope at start of week 2

```js
fragments: [
  { uid: "f-prose-w2", fragment_type: "content",
    content: "Week 2. A royal visitor is expected." },

  // Three choices
  { uid: "f-c-prince", fragment_type: "choice",
    edge_id: "e-prince", text: "Receive the visiting prince",
    accepts: { kind: "pick" },
    ui_hints: {
      hotkey: "1", emphasis: "primary",
      stat_check: { label: "Audience", dice: "1d20", target: 10,
                    against: { piece_id: "player", property: "charm" },
                    success_text: "varies with charm" }
    } },
  { uid: "f-c-combat", fragment_type: "choice",
    edge_id: "e-combat", text: "Train at arms instead",
    accepts: { kind: "pick" },
    ui_hints: { hotkey: "2",
      cost_previews: [{ ledger_key: "skills.combat", delta: 2, unit: "xp" }] } },
  { uid: "f-c-charm", fragment_type: "choice",
    edge_id: "e-charm", text: "Study courtly graces instead",
    accepts: { kind: "pick" },
    ui_hints: { hotkey: "3",
      cost_previews: [{ ledger_key: "skills.charm", delta: 2, unit: "xp" }] } }
],

projected_state: {
  sections: [
    { section_id: "schedule", title: "Schedule", kind: "calendar",
      value: { value_type: "scalar", value: "Week 2 of 4" },
      hints: { icon: "calendar" } },
    { section_id: "mood", title: "Mood", kind: "mood",
      value: { value_type: "scalar", value: "—" } },
    { section_id: "stats", title: "Stats", kind: "stats",
      value: {
        value_type: "kv_list",
        items: [
          { key: "body",   value: 10, max: 20, hint: "bar" },
          { key: "mind",   value: 10, max: 20, hint: "bar" },
          { key: "spirit", value: 10, max: 20, hint: "bar" },
          { key: "combat", value: 12, max: 20, hint: "bar", emphasis: "ok" },
          { key: "magic",  value: 10, max: 20, hint: "bar" },
          { key: "charm",  value: 10, max: 20, hint: "bar" }
        ]
      } },
    { section_id: "wallet", title: "Wallet", kind: "wallet",
      value: {
        value_type: "kv_list",
        items: [
          { key: "coin", value: 3, unit: "c" },
          { key: "stamina", value: 5, max: 5, hint: "bar" }
        ]
      } },
    { section_id: "inventory", title: "Inventory", kind: "inventory",
      value: { value_type: "badges", items: [] } }
  ]
}
```

### CLI rendering

```
Week 2. A royal visitor is expected.

[Schedule] Week 2 of 4
[Mood]     —
[Stats]
  body   10/20 (bar)
  mind   10/20 (bar)
  spirit 10/20 (bar)
  combat 12/20 (bar)  (ok)
  magic  10/20 (bar)
  charm  10/20 (bar)
[Wallet]
  coin    3 c
  stamina 5/5
[Inventory] (none)

1) Receive the visiting prince  [Audience: 1d20 vs charm, varies with charm]
2) Train at arms instead  (+2 combat xp)
3) Study courtly graces instead  (+2 charm xp)
> 1

(commits e-prince)

The prince watches you across the receiving hall. The guards lower
their eyes. You step forward and bow.

  [Audience: 1d20 vs charm]
  rolled: 14  +0  = 14  vs target 10
  outcome: success
  The prince leaves visibly charmed by your bearing.

1) Begin Week 3.
```

---

## 7 · Forward direction (Tier P3 aspirational)

The current `coronate_the_regent` demo is intentionally minimal.
Conventions a richer training bundle would land:

| Forward feature | v1.5 surface |
|---|---|
| Skill tree visualization | `GroupFragment(group_type="zone", zone_role="skill_tree")` with `layout_hints.graph={nodes, edges}`; each skill as `PieceFragment(kind="skill", properties: {level, max_level, xp, xp_to_next})` |
| Skill-prereq gating | `Blocker[]` on choice with `refs` to required-skill pieces |
| Per-skill XP-to-next | `KvRow` with `value: 47`, `max: 60`, `hint: "bar"`, `unit: "xp"` |
| Calendar visualization | `ProjectedState` `kv_list` with one row per remaining week, `emphasis` for scheduled events |
| Inventory zone (richer than badges) | `GroupFragment(group_type="zone", zone_role="inventory")` of `PieceFragment(kind="item")` |
| Romance / relationship tracks | `ProjectedState` `kv_list` keyed by NPC, `hint="bar"`, `emphasis` for status |

None of these require new vocabulary. They're convention-level
extensions that ship when a bundle author needs them.

---

## 8 · Port parity addendum

| Widget | Web (Vue) | CLI | tkinter | Hypothetical Ren'Py |
|---|---|---|---|---|
| Mood indicator | icon + label chip | `[Mood] <mood>` line | `Label(icon, text)` | side image |
| Stat row (`bar`) | progress bar with value/max label | `<key> <value>/<max> (bar)` | `ttk.Progressbar` | stat screen widget |
| Stat row (`delta`) | `+2` inline, color-coded | `<key> <value> +2` | `Label` with color tag | screen action |
| Schedule scalar | tile or banner | `[Schedule] <text>` | large `Label` | top banner |
| Study choice (with `cost_previews`) | button + cost chip | `<n>) <text> (+<delta> <ledger>)` | `Button` + `Label` | `menu:` item |
| Study choice (with `stat_check`) | button + difficulty badge | `<n>) <text> [<label>: <dice> vs <prop>, <p>]` | `Button` + tooltip | `menu:` with `if` |
| Skill check roll | one-shot animation | `[<label>] rolled: ... outcome: ...` | inline `Text` | screen with portrait |
| Inventory unlock | toast / item card | `* gained: <item>` | `Toplevel` notify | `notify()` |
| Ending | scrolled narrative | wrapped prose | full-screen `Text` | `scene` + `say` sequence |

---

## Appendix — Prior art

*Long Live the Queen* (Hanako Games, 2012) is the canonical reference
for scheduled-training succession games. Its design DNA traces back
to *Princess Maker* (1991) and forward through *Magical Diary*,
*Cute Knight*, and countless visual-novel hybrids. The genre's
defining tension is **commitment under uncertainty**: the player
must commit study time before knowing exactly which check it will
pay off, and the joy is watching accumulated decisions intersect
with pre-scheduled events.

`worlds/coronate_the_regent` is a deliberate *micro-instance* of
this genre — four weeks instead of forty, two skills instead of
forty, two events instead of dozens. The compactness is the point:
the demo proves the contract handles the genre's full shape
(scheduling, gating, branching, payoff) without needing the genre's
full *content*.

The training genre overlaps with farming-life simulators (*Stardew
Valley*'s weekly festivals), management games (*Two Point Hospital*'s
scheduled events), and tabletop XP-based RPGs (D&D session-by-session
progression). The vocabulary lifts cleanly.

The training *engine architecture* is documented in
`tangl.mechanics.progression` (stat systems, situational effects,
stat challenges). The engine-side `StatChallenge`, `Outcome`,
`SituationalEffect`, `LinearGrowthHandler` are authoring concerns;
this document is rendering contract.

---

*End of training EXTENSIONS v0.1.*
