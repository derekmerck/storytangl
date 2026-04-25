Stat Challenge Design
=====================

Status
------

Partially landed. The current package now has a supported one-shot challenge
surface, structured `ChallengeResult` output, donor-based situational effect
gathering, baseline growth handlers, broad stat-gate support, and an
`Adventure2` preset. Story-facing traversal wrappers and richer authored worlds
remain follow-up work.


Purpose
-------

This package already has the beginnings of a stat-resolution system:

- stat schema and competency rules
- multiple handler curves
- currencies and wallets
- tagged situational modifiers
- task resolution

What it does *not* have yet is a clean authored concept for a narrative
"challenge" as players experience it: pay a cost, attempt a check, get an
outcome quality, and map that quality to story consequences or payout.

This note describes how to assemble that missing layer incrementally without
reviving the older scratch challenge scaffolding.


What The Existing Code Already Does Well
----------------------------------------

The live package already has several strong foundations worth preserving:

- `StatSystemDefinition` and `StatDef` define a clean schema for intrinsics,
  domains, currencies, and matchup/context bonuses.
- `Stat` plus the handler classes separate internal measurement from tiered
  narrative categories.
- `HasStats.compute_competency()` already captures the core intrinsic-plus-domain
  pattern cleanly.
- `Task`, `compute_delta()`, and `resolve_task()` already express the atomic
  math of "competence versus difficulty plus modifiers."
- `SituationalEffect` already captures the simplest useful part of the old
  badge/equipment idea: tag-scoped, stat-scoped modifiers.

The scratch archive still has valuable design signals that should be promoted
carefully:

- quality-first rather than number-first narration
- currencies tied to domains
- challenge cost / difficulty / payout as a unified flow
- badges and effects as authored levers for bias and remapping
- wealth and similar broad resources modeled as capability tiers rather than
  bookkeeping-heavy numeric balances

The scratch archive also contains machinery that should *not* be promoted as-is:

- the old `challenge_block` scaffolding
- the several duplicate stat and measure implementations
- dynamic badge metaprogramming
- ad hoc delta-map parsers


Design Principles
-----------------

1. Challenges are not fairness simulators.

The system should feel predictable enough for players to learn, while still
giving authors explicit leverage to skew difficulty, payout, and narrative
framing.

2. Internal numbers, external qualities.

Internally, use `fv`, probabilities, and modifiers. Externally, project to
qualities like `poor`, `good`, `very high`, `failure`, `strong success`,
`modest reward`, and so on. Players should rarely need to see raw numbers.

3. Separate tactical currencies from broad narrative entitlements.

- `stamina`, `mana`, `focus`, and similar consumables fit `HasWallet`.
- `wealth`, `prestige`, `standing`, and similar broad affordance levels fit
  `Stat` or another quality-gated measure better than a counted wallet.

4. Keep author bias explicit.

If an author wants to tilt a scene, that should appear as normal challenge
data:

- hidden or visible modifiers
- remapped domains
- altered costs
- altered payout tables
- circumstance badges or effects

Do not introduce a separate "cheat" channel.

5. Build the atomic check before the authored loop.

The first missing piece is not a whole mini-game. It is a reliable,
inspectable, one-shot stat challenge result. Only after that exists should
we wrap it in authored traversal blocks or staged loops.


Core Concepts To Add
--------------------

1. `Stat challenge` as a first-class concept.

The current `Task` is close to the mathematical core, but it is not yet a
complete authored challenge. A challenge should bundle:

- entry cost
- tested domain or domains
- base difficulty
- scenario tags
- outcome-to-payout mapping
- optional gating requirements
- optional narrative labels

`Task` can remain the atomic resolution object, but authored content likely
wants a thin wrapper such as `ChallengeSpec` or `StatChallenge`.

2. `Challenge result` as a durable output object.

The current resolver returns only `Outcome`. The next layer should return a
structured result packet containing at least:

- resolved domain
- effective competency
- effective difficulty
- delta
- success likelihood
- sampled outcome
- cost actually paid
- reward actually granted
- active effects

This becomes the bridge between raw math and later journal projection.

3. `Effect donors` as the promoted badge abstraction.

The old badge system was trying to solve a real problem: modifiers can come
from the actor, equipment, location, opponent, memory, or story state.

The live package should not revive badge metaprogramming, but it *should*
eventually define a small common interface along the lines of:

- "this thing donates situational effects"
- "this thing donates tags"

That is enough to model swords, conditions, blessings, bribes, class traits,
or author bias without inventing a second modifier framework.

4. `Quality projection` as a separate concern.

There should be a clean distinction between:

- internal value: `fv`, wallet integers, probabilities
- projected quality: `poor`, `good`, `very wealthy`
- narrative language: "You did fairly well," "You can afford a town house"

This is especially important for broad stats like wealth, status, influence,
and reputation.


Recommended Incremental Build Order
-----------------------------------

Phase 1: Minimal one-shot stat challenge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:
    Prove the smallest authored check loop.

Implement:

- a lightweight `StatChallenge` or `ChallengeSpec`
- a `ChallengeResult`
- a resolver that wraps existing `Task` math
- one preset that feels like "Fighting Fantasy lite"

Scope:

- two or three intrinsics at most
- one cost channel, e.g. `stamina` or `mana`
- one tested domain per challenge
- one fixed payout table keyed by outcome quality
- no training, equipment remapping, or opposed resolution yet

Example flavor:

- `strength`, `magic`
- `hp` and `mana` or `stamina` and `mana`
- a `fight` check costs stamina and yields injury, loot, or progress

Why first:
    This proves the user-facing challenge contract before any subsystem
    explosion.

Phase 2: Outcome quality and payout mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:
    Promote outcome quality from a raw enum into a reusable authored scale.

Implement:

- explicit payout mapping by outcome band
- support for partial or zero payout on failure
- optional non-currency aftermath, e.g. tags, flags, or simple state deltas

This is the point where "modest reward," "good reward," and "excellent
reward" become real authored concepts.

Phase 3: Badge and equipment modifiers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:
    Promote the useful part of the old badge idea.

Implement:

- a common "effect donor" seam for actors, equipment, conditions, and story
  state
- effect gathering from multiple sources
- optional tag donation in addition to direct numeric modifiers

Examples:

- sword gives a `#fight` competency boost
- heavy armor makes `#stealth` harder
- curse remaps `body` costs onto `will`

Do *not* implement the old dynamic badge metaprogramming.

Phase 4: Quality-gated narrative resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:
    Support things like wealth, standing, and access without making players
    track fine-grained numbers.

Implement:

- quality-gated availability checks
- explicit support for costs or gates expressed as minimum quality rather than
  currency spend
- a projection layer for narrative labels

Examples:

- `wealth >= high` can afford a townhouse
- `prestige >= good` grants access to a salon
- `reputation <= poor` locks certain patron routes

This phase is where "wealth is a stat" becomes a first-class supported style.

Phase 5: Skills and governed domains
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:
    Lift the system from bare intrinsics into a proper intrinsic-plus-skill
    model.

Implement:

- a stronger authored pattern for governed skills
- more domain-first challenge presets
- optional skill growth hooks keyed to challenge difficulty and outcome

The live competency rule already supports this mathematically. This phase is
about authoring and progression semantics, not new probability math.

Phase 6: Opposed and remapped challenges
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:
    Promote the richer author-bias tools from the archive.

Implement:

- opposed checks where one side's competency becomes the other's difficulty
- domain remapping
- cost remapping
- context-sensitive advantage

Examples:

- a duel tests `fight` against enemy `fight`
- a mind-control curse turns `body` resistance into `will`
- bribery replaces a social difficulty with a wealth cost

This should still reuse the same atomic `ChallengeResult` shape.

Phase 7: Authored traversal integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:
    Make challenges first-class story interactions.

Implement:

- a simple story/VM block or mixin for one-shot challenges
- JOURNAL projection from `ChallengeResult`
- POSTREQ routing by outcome band
- optional repeatable or staged challenge loops

Important:
    Do not start here. The authored block should come *after* the core
    challenge result is stable.


What A First Live Preset Should Look Like
-----------------------------------------

The first world-facing preset should be deliberately tiny:

- intrinsics: `strength`, `magic`
- currencies: `stamina`, `mana`
- optional broad stat: `wealth`
- domains: either none, or a single `fight` domain governed by `strength`
- outcomes: `disaster`, `failure`, `success`, `major_success`

This gives us:

- a simple dungeon or Fighting Fantasy shape
- a clean baseline for future modifiers
- a place to prove that numbers can stay internal while qualities stay public


Mapping Numbers To Narrative
----------------------------

The system should treat narrative phrasing as a projection layer rather than
as the stat system itself.

For example:

- `Stat(fv=13.5)` might project to `high`
- `Outcome.SUCCESS` plus a small payout might project to "You managed it,
  though only modestly."
- `wealth: high` might project to "You can afford a respectable townhouse,"
  without exposing a cash total

This keeps the engine numerically coherent while preserving the authored,
qualitative feel you want.


Recommended Immediate Next Steps
--------------------------------

1. Add a `ChallengeResult` type next to `Task` and `resolve_task()`.
2. Add a tiny `StatChallenge` wrapper around `Task` with outcome-to-payout
   mapping.
3. Add one minimal fantasy preset aimed at `strength`, `magic`, `stamina`,
   and `mana`.
4. Add a very small authored proof world with one or two one-shot checks.
5. Only after that, add effect donors and quality-gated wealth/access.


Non-Goals For The First Pass
----------------------------

- no nested challenge framework
- no giant badge DSL
- no fine-grained economic simulation
- no attempt to make the system "fair"
- no requirement that players ever see raw numeric values
