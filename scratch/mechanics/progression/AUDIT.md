Progression scratch: audit
==========================

Inventory only. **Nothing deleted.**

This audit is subordinate to
``engine/src/tangl/mechanics/progression/STAT_CHALLENGE_DESIGN.rst``, the
canonical ledger for this tree. That document states the archive stays intact
pending a source-level harvest and that the ledger alone is not permission for
bulk deletion, then gives a five-step Bounded Retirement Sequence naming the
semantics to capture first. It governs; the sort below is a starting point, not
authority to delete.

Its warning applies directly here: *a matching class name or passing live suite
is not proof of semantic parity.* Two claims in an earlier revision of this file
failed exactly that test and are corrected inline.

`scratch/mechanics/progression` carries three generations at once:

- `legacy/progression-pre25/` — the oldest, `attr`-based, `Character` and
  `Badge` era
- `legacy/` + `challenge_block/` — the middle generation, with literal
  duplicates left side by side (`task.py` and `task-2.py`,
  `situational_effect.py` and `situational_effect-2.py`)
- `stats/` — the newest scratch generation, closest to what shipped

The realized `tangl.mechanics.progression` is 41 modules and ~2,900 lines with
16 test files. It is not a thin promotion of this tree; it is a rewrite that
went further on almost every axis.

Landed, and better
------------------

| Scratch concept | Realized as |
|---|---|
| `EnumeratedValue` / `quality.py` | `Quality` (`measures.py`) |
| `MeasuredValue`, `stat_measures/*` | `Stat` plus `StatHandler` (`linear`, `logint`, `probit`) |
| `log_int_stat.py` | `LogIntStatHandler` |
| `normal_stat.py` | `ProbitStatHandler` |
| `DeltaMapHandler` | `ModifierTotals` / `modifier_stack.py` plus `growth/handlers.py` |
| `SituationalEffect` (both copies) | `effects/situational.py`, substantially richer |
| `Task`, `TaskHandler`, `task-2.py` | `tasks/task.py`, `tasks/resolution.py` |
| `challenge_block/*` | `challenges/`, `story_blocks.py` |
| `stat_domains/`, `opinionated`, `psychosomatic` | `StatSystemDefinition` plus `presets/` (fantasy, cyberpunk, adventure) and `CanonicalSlot` — data rather than hardcoded enums |
| `StatCurrency(Fungible)` | `StatDef.currency_name` plus `HasWallet`; the stat/currency link is a field, not a subclass |
| `governors` / `SecondaryTrait` | `entity/has_stats.py` |

The realized `SituationalEffect` adds axes the scratch version never had:
`competency_modifier`, `growth_modifier` (training gain, deliberately distinct
from payout), `forced_outcome`, `domain_override`, and currency remaps.

It is **not** a superset. One behavior is unported: scratch gated tags with
`applies_to_tags.issubset(tags)`, so an effect scoped to `{#combat, #night}`
required *both*. Realized `applies()` gates on intersection
(`applies_to_tags & tag_set`) and fires on either. Compound-circumstance effects
cannot currently be expressed.

Residue check
-------------

Review of the first pass asked specifically about three places where value
would hide before deleting. Checked; the residue is real but narrow.

**Stat currencies are unpaired.** The old domain maps carried a resource *and*
a depletion currency — `BODY: "stamina"  # cost: fatigue`, `MIND: "wit"  # cost:
focus`, `SPIRIT: "will"  # cost: temper, stress`. Realized `StatDef` has a
single `currency_name`. Effects can remap and scale costs
(`cost_currency_remap`, `cost_modifier`), but a stat does not declare what
spending it costs. Whether that wants a field or wants fatigue modelled as its
own stat is a design question, not an oversight to correct blind.

**The specialized domain catalogs are mostly absorbed.** `OpinionatedDomains`
mapped nine domains to currencies; the fantasy preset already carries
`body`/`stamina`, `mind`/`focus`, `charm`, and `hidden` — the last taken
straight from `CRIME: "hidden"`. What did not land is genre content for a game
that does not exist: `PRESTIGE`/influence, `PRINCESS`/presence,
`CORRUPTION`/darkness, `BEAUTY`/composure, `COMFORT`/heat. Two smaller
conventions did not land either: domain **aliases** (`CHARM = COMFORT`,
`CORRUPTION = CRIME` — one domain, two flavors) and an explicit `ANY` wildcard
domain, which the automata catalog assumes when it writes `@all-up`. Empty
`applies_to_tags` covers the wildcard semantically today.

**Two task semantics are genuinely absent.** Most of the old `TaskHandler`
mapped cleanly onto current names — `can_pay_cost` is `can_afford`,
`difficulty_delta` is `compute_delta`, `realized_payout` is outcome scaling over
`_scale_wallet`. Two did not:

- `can_receive_payout` — a **capacity** check before granting a reward. Wallets
  are uncapped and `earn()` cannot refuse, so nothing can express "you cannot
  hold any more of this".
- `_update_task_history` — per-task attempt tracking. There is no attempt count
  or past-outcome record on `Task`. The journal records what happened
  narratively; the task does not know it has been tried before, which matters
  for diminishing returns or one-shot opportunities.

Neither is a reason to keep the scratch code. Both are worth an issue if a world
wants them.

Rough sort, pending the bounded sequence
----------------------------------------

Everything not named in the next section *appears* superseded — a starting
point for the harvest in STAT_CHALLENGE_DESIGN.rst, not a deletion list. That
document names specific semantics to capture from `stats/`,
`progression-pre25/character.py`, `q_prop.py`, `measured_value.py`,
`legacy/task.py`, `delta_applier.py`, and `task-2.py` before any of them go. That is roughly 42 of the 46 files,
including all of `stats/`, all of `legacy/` except the two badge sources, all of
`challenge_block/` except `situational_effect-2.py`, and both test trees. Each
has a strictly better realized counterpart in the table above.

Still on the table
------------------

Four files, and they are all about **badges** — which is why this audit was
worth doing before writing that design note.

### 1. The terse effect grammar — specified, never implemented

`README.md` is the only place this exists. There is no parser anywhere, in
scratch or in the engine:

```
#x                          activity is in domain x
@x-up / @x-down             cost down, difficulty down, reward up (and inverse)
@x-up-up                    magnitude stacking
@x+cost-up/down             one axis at a time
@x+difficulty-up/down
@x+payout-up/down
@x-cheap/dear               alias for x+cost-down/up
@x-easy/hard                alias for x+difficulty-down/up
@x-bonus/malus              alias for x+reward-up/down
@x-inv                      invert rewards in domain x
@x-is-y                     remap domain x onto domain y
@x-prohibited               cannot act in domain x
```

The realized `SituationalEffect` already has the semantics for most of it —
`applies_to_tags` is `#x`, the four modifier fields are the axes,
and `domain_override` is `@x-is-y`. What is missing is the **authoring
shorthand**, plus three operators with no realized equivalent:

- magnitude stacking (`@x-up-up`)
- reward inversion (`@x-inv`)
- **prohibition (`@x-prohibited`)**. `forced_outcome` is not an equivalent:
  `resolve_challenge()` spends the cost before applying the override — its own
  comment says "Cost is still paid (the attempt happened)" — then derives payout
  and growth from the forced result. Prohibition is an availability gate, not an
  outcome override, and the shorthand work must supply one.

This matters because the automata catalog is written in this notation
(`'@all-up'`, `'@combat-up'`, `'@damage-down'`). Nothing can read it today.

### 2. `legacy/progression-pre25/badge.py` — nested badge conditions

A spike on the hard part. Badges are named `Condition` expressions that may
reference *other badges by name*:

```python
badges = {
    'p1':   Condition(expr="prop1 >= 10"),
    'both': Condition(expr="p1 and p2"),
    'three': Condition(expr="both or p2"),
}
```

`nested_eval` resolves badge names inside expressions recursively. This is
exactly the dependency graph that can cycle, and the reason the old tree
reached for a topological sort. No realized equivalent.

### 3. `legacy/progression-pre25/skilled.py` — the badge API and tier occlusion

The clearest statement of the intended shape:

```python
Badge(uid=f'{k}_minor', effects=..., conditions=[f'{k} very low'])
Badge(uid=k,            effects=..., conditions=[f'{k} ok'],        hides=[f'{k}_minor'])
Badge(uid=f'{k}_major', effects=..., conditions=[f'{k} very good'], hides=[f'{k}_minor', k])
```

Four fields: `uid`, `effects`, `conditions`, `hides`. Note that `hides` is doing
**tier occlusion** here — each competence tier conceals the ones below it — not
just concealment. The automata catalog's `adv_combat hides combat` is the same
pattern in a different skin, so one mechanism covers both.

Also note the import: `from tangl.story.asset.badge import Badge`. A badge was
always meant to live in the asset package, which matches "a persistent token
carrying a fact that is not consumed on use".

Conditions are authored as quality-tier phrases (`"{k} ok"`, `"{k} very good"`)
using the competence register.

### 4. `challenge_block/situational_effect-2.py` — activation lifecycle

`GlobalEffectType(Lockable, Conditional)` with `active` / `activate()` /
`deactivate()` is the dynamic-assignment half: an effect that turns itself on
and off from world state rather than being granted once. Keep as the statement
of that lifecycle; the code is not a porting target.

The badge socket already exists
-------------------------------

`effects/donors.py` defines `EffectDonor` — "things that donate situational
effects" — plus `TagDonor` and `gather_donor_effects()`. That is precisely the
socket a badge plugs into. There is no `Badge` type in the engine, but the
interface it would implement is already built and already consumed by challenge
resolution.

So the badge work is not "add a subsystem". It is: a persistent fact token that
implements `EffectDonor` and `TagDonor`, plus conditional assignment with
nested references, plus `hides` occlusion, plus a parser for the shorthand its
catalogs are written in.

One small nuance worth keeping
------------------------------

Scratch `EnumeratedValue` read one scale in two registers —
`V_POOR = V_EASY`, `GOOD = HARD` — so a tier is "good" competence or "hard"
difficulty depending on which side of the challenge you are reading. Realized
`Quality` keeps the competence register (`OK`, `GOOD`, `VERY_GOOD`) but not the
difficulty one, even though `SituationalEffect` carries both
`difficulty_modifier` and `competency_modifier`. Cheap to add as aliases if
difficulty authoring ever wants the vocabulary.
