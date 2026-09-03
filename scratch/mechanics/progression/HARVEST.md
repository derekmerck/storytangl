Progression harvest
===================

The source-level harvest required by
``engine/src/tangl/mechanics/progression/STAT_CHALLENGE_DESIGN.rst`` before any
retirement. Its Bounded Retirement Sequence has five steps; each batch below
states the exact files, the surviving idea and its destination, what live tests
already cover, and what is deliberately deferred.

Read with `AUDIT.md`, which holds the concept-to-location table. This file holds
the semantics that are **not** in the live package and would otherwise be lost.

---

Batch 1 — authored scales and roll alternatives
-----------------------------------------------

**Files:** `stats/stat_measures/measures.py`, `stats/simple_stats.py`,
`stats/stat_measures/{base_stat,log_int_stat,normal_stat}.py`,
`stats/quantized_value.py`, `stats/enums.py`, `stats/stat_test.py`,
`stats/stat_currency.py`, `stats/stat_domains/*`

### Eleven registers over one five-tier scale

`measures.py` defines eleven parallel 1–5 scales, each a *reading* of the same
internal value in a different vocabulary:

| Register | Tier 1 → 5 |
|---|---|
| `Quality` | very low → very high |
| `Size` | tiny → huge |
| `Ability` | unskilled/novice/skilled/master/expert |
| `Difficulty` | trivial/easy/challenging/hard/impossible |
| `Result` | terrible → excellent |
| `Rarity` | very common → very rare |
| `Grade` | F/C/B/A/S |
| `Affection` | hateful → loving |
| `Trust` | terrified → loyal |
| `Willingness` | defiant → excited |
| `Grade15` | a 15-tier academic variant |

This is design principle 2 ("internal numbers, external qualities") made
concrete: one internal scale, many external vocabularies. Live `Quality` keeps
only the competence register plus `OK`/`GOOD`/`VERY_GOOD` aliases.

**Intentional tier boundaries.** `Grade` and `Grade15` carry percentage anchors
in comments — `F=70, C=80, B=90, A=99, S=100` for the five-tier, and a
40/55/60/63/67/70/73/77/80/83/87/90/93/99/100 ladder for the fifteen. These are
authored choices, not derived, and the fifteen-tier variant shows the tier count
itself was meant to be a per-world decision.

**Predicate namespace.** `measure_namespace` flattens every register into one
namespace with `NONE=0` and `MAX=100`, and `measure_of("very good")` casts
strings to tiers. That is what made badge conditions like `"{skill} very good"`
authorable, and it is the missing half of the terse-grammar story in
`README.md`.

### Roll and conversion alternatives

`simple_stats.py` carries five interconvertible representations of one stat —
`qv` (tier), float 0–1, `std` (−2.5..2.5), `int5`, `int20` — and six samplers
grouped as uniform (`d20`, `u20`) versus normal (`4d6-4`, `n20`, `4dF`, `n5`).

The resolution rules are explicit and unported:

- relative difficulty is `(difficulty − stat) / 2`
- on a 20-point scale, beat `10 + RD` with a normal sampler, or beat
  `(3, 7, 14, 17)[RD]` with a uniform one
- a margin of ≥5 (20-point) or ≥1 (5-point) is a great success or a disaster
- a natural minimum is always a disaster, a natural maximum always a major
  success, regardless of modifiers

**The design lever worth keeping:** choosing a uniform versus a normal sampler
is how an author tunes *how often* criticals and disasters occur, without
touching difficulty. Live handlers (`linear`, `logint`, `probit`) fix the
distribution and have no natural-min/max rule.

**Destination:** #112. **Covered live:** tier projection and handler arithmetic.
**Deferred:** everything above.

---

Batch 2 — governors, currency exercise, relationship coupling
--------------------------------------------------------------

**Files:** `legacy/progression-pre25/character.py`, `q_prop.py`,
`legacy/stat_domains.py`, `legacy/stats.py`

### Governor propagation runs the wrong way in the live package

Live `StatDef.governed_by` is **read-only composition**: competency is
`average(intrinsic.fv, domain.fv)`. The archived model propagates in the other
direction — a `SecondaryTrait` gain *raises its governors* and a loss lowers
them, so practising a skill feeds the attribute above it.

### Spending a currency exercises its governor

`StatCurrency` declares `governors` and the rule "governor increases with
spend/exercise, decreases with restore". Spending stamina makes you fitter;
resting does not. Nothing in the live package expresses use-based growth as a
side effect of expenditure — growth is granted by task outcome only.

### Relationship polarity flips affect signs

`Relationship` couples trust and affection to spirit with an explicit sign flip:

```
loving:  gain fear / lose trust → spirit down;  gain trust / lose fear → spirit up
hateful: gain fear / lose trust → spirit up;    gain trust / lose fear → spirit down
```

The same event moves spirit in opposite directions depending on how the
character feels about the other party. Registers for this exist in batch 1
(`Affection`, `Trust`, `Willingness`); the coupling rule does not exist anywhere
live.

**Destination:** passive change → #207; campaign policy → #208; relationship and
voiced-skill policy → its story consumer, adjacent to #340. **Covered live:**
`governed_by` declaration and validation. **Deferred:** all three rules above.
**Explicitly not promoted,** per the sequence: the generated-class and
`QualityProperty` descriptor machinery in `q_prop.py`.

---

Batch 3 — tier boundaries and within-tier sampling
---------------------------------------------------

**Files:** `legacy/measured_value.py`, `legacy/measures.py`,
`legacy/test_stats.py`, `legacy/tests/*`, `legacy/basic_stats.yaml`

Two deliberate behaviors, both absent live:

- **A downward rounding bias.** `qv = round(ev - 0.1)` — the comment says "a
  very small bias to round *down* the qv", so a value must clear a tier boundary
  decisively to be read at the higher tier.
- **Within-tier random sampling.** `random_value_from_level(level)` converts a
  tier back to a float by sampling *within* the tier, so round-tripping a
  quality is deliberately lossy and slightly noisy rather than snapping to a
  tier centre.

Values clamp to 0–20 across linear, log, and normal handlers.

**Destination:** #112. **Covered live:** handler arithmetic and tier projection,
under different boundary rules. **Deferred:** the rounding bias and within-tier
sampling. Per the sequence, a passing live suite is not proof of parity here —
the live boundaries simply differ.

---

Batch 4 — schema discrimination and wrapper ownership
------------------------------------------------------

**Files:** `challenge_block/challenge_block.py`, `activity_block.py`,
`activity_script_models.py`, `challenge_block/task.py`

Both surviving ideas are *questions*, recorded verbatim from the source rather
than answered:

- **Schema discrimination.** "How do we indicate these are allowed block types
  in the story script schema?" and "how do we indicate that `task` discriminates
  Activities from other types of Blocks?" — authoring-schema questions, now
  owned by the authoring/validation track (#286).
- **Wrapper ownership.** `ChallengeBlock(StatChallenge, Block)` makes the block
  *be* the challenge by inheritance. Live `story_blocks.py` instead composes,
  keeping challenge data separate from the block. The archived approach is the
  rejected alternative; recording that it was considered.

**References checked:** nothing outside the design doc imports these.
**Destination:** #286 for the schema questions. **Covered live:**
`story_blocks.py` end to end. **Deferred:** nothing; the composition choice is
settled.

---

Batch 5 — tag matching, delta algebra, result history
-------------------------------------------------------

**Files:** `legacy/task.py`, `legacy/delta_applier.py`,
`challenge_block/task-2.py`, `challenge_block/situational_effect.py`,
`challenge_block/situational_effect-2.py`

### All-of tag matching

`legacy/task.py` gates with `applies_to_tags.issubset(tags)` — an effect scoped
to `{#combat, #night}` requires **both**. Live `SituationalEffect.applies()`
gates on intersection and fires on **either**. Compound-circumstance effects
cannot be expressed live. This is the single clearest unported semantic in the
tree.

### Two delta algebras, deliberately not merged

`delta_applier.py` applies `value * relative + value + absolute` — a
`(absolute, relative)` pair where `relative` is a fraction around **identity
zero**, so `0.1` means +10%.

Live `SituationalEffect` sums proportional modifiers and applies `1 + sum`,
clamped to `[-1, 1]` — a scale factor around **identity one**.

Per the sequence, these are recorded as disagreeing and are *not* reconciled
into an implied common contract. The archived form also supports absolute and
relative change in one operation per key; the live form separates additive
axes (difficulty, competency) from proportional ones (cost, reward, growth).

`task-2.py`'s own weighting methods (`cost_for`, `difficulty_for`,
`payout_for`) are unimplemented `# todo` stubs, so it contributes intent, not an
algebra.

### Result history

Both task generations carry `history: list[tuple]` on the task and update it on
resolution. Live `Task` has no attempt count or outcome record, so a task cannot
know it has been tried — which forecloses diminishing returns and one-shot
opportunities. The journal records the narrative event; the task does not record
the attempt.

**Destination:** #112 for the algebra and history; the all-of tag gap is already
recorded as unported in `STAT_CHALLENGE_DESIGN.rst`. **Covered live:**
intersection tag gating, proportional modifier folding, outcome resolution.
**Deferred:** all-of matching, per-key combined absolute/relative deltas, task
attempt history.

---

Retained after the harvest
--------------------------

`README.md` (the terse effect grammar, which has no parser anywhere),
`legacy/progression-pre25/badge.py` (nested badge conditions),
`skilled.py` (badge tier occlusion), and
`challenge_block/situational_effect-2.py` (effect activation lifecycle) — all
four for #421, plus `AUDIT.md` and this file.
