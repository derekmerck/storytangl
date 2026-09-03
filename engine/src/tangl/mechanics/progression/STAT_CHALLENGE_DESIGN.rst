Stat Challenge Design
=====================

.. storytangl-topic::
   :topics: progression
   :facets: design, notes
   :relation: documents
   :related: games, transaction, assembly


Status
------

The baseline is integrated. The current package has a supported one-shot challenge
surface, structured `ChallengeResult` output, donor-based situational effect
gathering, baseline growth handlers, broad stat-gate support, and an
`Adventure2` preset. Situational effects now carry full three-axis magnitude
modifiers -- `cost_modifier`, `difficulty_modifier`, and `reward_modifier` --
plus a distinct `growth_modifier` for training gain (cost/reward are
proportional wallet adjustments clamped to a `1 + sum` factor over [-1, 1];
growth scales `GrowthHandler.grow(gain_scale=...)`). A situational
`forced_outcome` provides a hard authored override of the rolled outcome
(fumble/fail/pass/critical); when several apply the most severe wins, so a
prohibition dominates a blessing. ``HasStatChallenge`` and ``HasTraining`` now
attach these operations to ordinary story blocks; ``coronate_the_regent`` is the
compiled-world proof. The phase proposals below are historical design rationale,
not an up-to-date implementation checklist. Issue #112 owns deferred progression
research, #207 passive drift/recovery, and #208 campaign/meta-resource semantics.


Purpose
-------

This package already has the beginnings of a stat-resolution system:

- stat schema and competency rules
- multiple handler curves
- currencies and wallets
- tagged situational modifiers
- task resolution

``StatChallenge`` now supplies the authored concept of paying a cost, attempting
a check, receiving an outcome quality, and mapping that quality to consequences
or payout. This note preserves its design rationale and the remaining archive
ideas without reviving the older scratch challenge scaffolding.


Three Distinct Contracts
------------------------

The archive experiments combine three concerns that should remain distinct:

1. **Measured values and authored vocabulary.** A continuous float supports
   fractional progress while a discrete tier supplies author-facing words.
   ``Stat`` retains ``fv``/``qv`` and tier-based equality. However, the live
   ``Quality`` scale is generic: ``good`` works, but ``easy`` and ``hard`` do not.
   The domain-specific ``Ability``, ``Difficulty``, ``Result``, and other scales
   in ``scratch/mechanics/progression/stats/stat_measures/measures.py`` are still
   useful prior art. Preserve typed naming/projection over one measurement
   representation, not a second numeric model or a global bag of enum aliases.

2. **Domain and modifier resolution.** ``HasStats.compute_competency`` combines
   a skill with its governing intrinsic. ``inspect_resolution`` adds scoped
   modifiers and computes competency minus difficulty. The current Probit
   handler evaluates ``Phi(delta / 3)``: equal values give 50% success, a
   six-float-point deficit gives about 2.28%, and a six-point advantage gives
   about 97.72%. One tier between representative values is three float points,
   so a half-tier tool bonus is 1.5, not 0.5. The archive's 0..1, 0..20, tier,
   and standard-deviation forms are alternative representations, not quantities
   to mix without conversion. Four-band outcome sampling currently uses a fixed
   probability margin, not additional normal-distribution bands; at equal
   ability/difficulty it gives 35% disaster, 15% failure, 15% success, and 35%
   major success. That calibration is a design choice to review, not missing
   probability machinery.

3. **Story check lifecycle.** ``HasStatChallenge`` resolves in UPDATE, publishes
   pass/fail facts to the namespace, emits JOURNAL content, and allows ordinary
   POSTREQS edges to route onward. It is the one-step counterpart of a game
   block, but delegates its mathematics to ``resolve_challenge`` rather than
   implementing another kernel. ``HasTraining`` reuses the same resolver.

Two concrete qualifications to the integrated baseline:

- Unpinned challenge and training rolls reach module-global ``random.random``
  through ``sample_outcome``. The story wrappers do not pass the frame's seeded
  ``ctx.get_random()`` sample. Regent's prince and dragon checks pin their rolls,
  so that demo does not prove replay of an ordinary stochastic check. A bounded
  follow-up should use the existing explicit ``roll`` argument at the UPDATE
  boundary and verify replay from identical graph state, not add an RNG service.
- Stats are currently Pydantic values within ``HasStats.stats``. They are
  readable through ``player.<stat>`` and challenge results contribute namespace
  facts, but a skill is not itself a scoped speaker or action contributor.
  For the "skills as inner voices" direction, keep the numeric value where it
  is owned and let an ordinary story concept read it and contribute through
  namespace/dispatch/JOURNAL. This belongs with #255, #336, and #340, not a new
  stat/check system or a requirement that every scalar become a graph node.


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


Legacy Harvest Ledger
---------------------

The files under ``scratch/mechanics/progression/legacy`` are implementation
archaeology, but they are not ready for wholesale deletion.  The table below
separates ideas already represented by the live package from ideas that still
need an explicit disposition.

.. list-table:: Legacy progression ideas
   :header-rows: 1
   :widths: 34 12 54

   * - Archive idea
     - State
     - Live seam or remaining question
   * - Continuous values with narrative quality tiers; equality by tier,
       ordering by value
     - Landed
     - ``Stat``, handlers, and projection
   * - Linear, logarithmic, and normal/probit measurement curves
     - Landed
     - ``handlers`` preserves the useful curve separation
   * - Domain-specific names over a shared measured value
     - Partial
     - Generic ``Quality`` landed; ``Ability``/``Difficulty``/``Result``
       vocabulary and domain-specific projections remain in scratch
   * - Intrinsic-governed skill/domain competency
     - Landed
     - ``StatDef.governed_by`` and ``HasStats.compute_competency``
   * - Unified cost, difficulty, outcome, and payout flow
     - Landed
     - ``StatChallenge``, ``ChallengeResult``, and resolver
   * - Opposed checks plus domain, cost-currency, and reward-currency remapping
     - Landed
     - ``resolve_challenge`` and ``SituationalEffect``
   * - Actor, equipment, and context as effect/tag donors
     - Landed
     - Explicit effect/tag donors replace dynamic badge injection
   * - Outcome-weighted growth that also nudges the governing intrinsic
     - Partial
     - Challenge growth and governor gain landed; inactivity decay and
       restorative loss did not
   * - Currencies governed or capped by a related stat, with stat-dependent
       recovery
     - Unported
     - ``StatDef.currency_name`` associates a name only; wallet capacity and
       recovery policy remain undefined
   * - Threshold qualities automatically donating effects (the useful part of
       dynamic badges)
     - Partial
     - Conditional donors are expressible already (Regent uses mood/inventory).
       A reusable quality-threshold catalog is not established; first prove a
       simple stat predicate through the existing donor seam
   * - Task history as an owned sequence of complete resolution receipts
     - Partial
     - One ``ChallengeResult`` is explicit; durable history ownership and replay
       policy remain undefined
   * - All-of tag applicability for compound circumstances
     - Unported
     - Archive effects used subset matching; live effects use intersection
       matching. Add an explicit mode only for a real authored example
   * - Per-currency absolute and relative delta maps
     - Deferred
     - Live scalar modifiers and remaps are easier to inspect. Revisit only when
       a concrete challenge needs asymmetric currency modification
   * - Random sampling of a continuous value when an author supplies only a
       quality tier
     - Deferred
     - If retained, sampling belongs at an explicit materialization boundary,
       not inside ``Stat`` construction
   * - Qualitative wealth, standing, reputation, and access gates
     - Landed
     - ``StatChallenge.requirements``/``StatRequirement`` provide minimum and
       maximum stat gates. #208 concerns campaign persistence/reset policy,
       not the existence of ordinary stat gates
   * - Inverse relationship axes such as fear/trust and hate/love
     - Rehome
     - Useful interaction precedent, but it belongs to relationship/control
       state, not generic progression

An idea does not have to be implemented before its prototype can be retired.
It does need a durable statement of the useful semantics, a source pointer, and
an explicit destination or decision.

.. note::

   **The harvest below has been carried out and the archive retired.** Its
   results live in two files that are *not* indexed by devref, because
   ``scratch/`` is outside the source patterns:

   - ``scratch/mechanics/progression/HARVEST.md`` — the semantics that are
     **not** in this package, batch by batch, each with a destination
   - ``scratch/mechanics/progression/AUDIT.md`` — the concept-to-location table
     for what did land

   Consult ``HARVEST.md`` before designing anything in the list below. It is
   written for targeted lookup rather than sequential reading: a problem like
   "this effect should require *both* tags", "criticals fire too often",
   "practising should raise the governing attribute", "this task should get
   harder each attempt", or "authors want ``very good`` in a condition string"
   each maps to one batch.

   Four sources were retained rather than retired, all for badge work (#421):
   the terse effect grammar in ``README.md``, the nested badge-condition spike,
   the badge tier-occlusion API, and the effect activation lifecycle.

Bounded Retirement Sequence
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Preserve the authored scale examples from ``stats/stat_measures/measures.py``
   and the conversion/roll alternatives in ``stats/simple_stats.py`` first.
   Record which units, tier boundaries, and outcome grading are intentional.
   These files contain more than superseded class names.
2. Capture the remaining governor/currency/relationship rules in
   ``legacy/progression-pre25/character.py`` and the threshold-effect intent in
   ``skilled.py``/``q_prop.py``. Route passive change to #207, campaign policy
   only to #208, and relationship or voiced-skill policy to its story consumer.
   Do not promote the generated-class/property machinery.
3. Compare ``legacy/measured_value.py`` and its tests with live ``Stat`` and
   handler tests. Retire duplicate arithmetic scaffolding only after recording
   the differing tier boundaries and optional within-tier random sampling.
   A matching class name or passing live suite is not proof of semantic parity.
4. Compare ``challenge_block/task.py``, ``challenge_block/challenge_block.py``,
   and ``challenge_block/activity_script_models.py`` with ``story_blocks.py``.
   These are the first narrow deletion candidates after preserving their schema
   discrimination and wrapper-ownership ideas. Check references before deletion.
5. Review ``legacy/task.py``, ``legacy/delta_applier.py``, and
   ``challenge_block/task-2.py`` separately: capture all-of tag matching,
   per-key modifier algebra, and result-history intent before retiring them.
   Their delta algebras disagree: one adds relative changes around identity
   zero; the other multiplies scale factors around identity one. Do not merge
   their examples into an implied common contract.

Each deletion batch should state the exact files, the surviving idea destination,
the behavior already covered by live tests, and any deliberately deferred idea.
No runtime feature work or GitHub issue mutation is implied by this audit.

This contract was honored: ``HARVEST.md`` records all four fields for each of
the five batches.


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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goal:
    Promote outcome quality from a raw enum into a reusable authored scale.

Implement:

- explicit payout mapping by outcome band
- support for partial or zero payout on failure
- optional non-currency aftermath, e.g. tags, flags, or simple state deltas

This is the point where "modest reward," "good reward," and "excellent
reward" become real authored concepts.

Phase 3: Badge and equipment modifiers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
