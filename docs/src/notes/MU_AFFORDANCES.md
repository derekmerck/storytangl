# Facets: Mu-Affordances and Mu-Dependencies

**Document Version:** 0.3
**Status:** DESIGN NOTE - vocabulary and implementation direction
**Prior art:** issue `#113`, issue `#141`, `engine/src/tangl/story/concepts/role.py`
(phase-1 grants), `engine/src/tangl/mechanics/sandbox/visibility.py` (restrictions),
`engine/src/tangl/prose/mu_block.py`, `scratch/mechanics/badge/badge.py`
**Relevant layers:** `tangl.core`, `tangl.vm`, `tangl.story.concepts`,
`tangl.mechanics.sandbox`, `tangl.prose`, `tangl.journal`

---

## Problem Statement

StoryTangl has a recurring need: a concept that is *active in the current scope*
wants to influence a downstream task — prose, choices, navigation, a stat
challenge — **without** being an independent graph node and without the
downstream task knowing the concept exists.

Examples that look unrelated but are the same shape:

- a role grants the bound actor a `title` and a short name for prose
- a held sword grants `+1` on combat stat challenges to its holder
- a lantern grants `light`; its absence restricts movement to "it's too dark"
- Stormbringer, once drawn, whispers into the journal **and** suppresses the
  "put it away" choice until it has been used
- a Disco-Elysium-style *voice* occasionally contributes a line or suppresses a
  choice according to its influence and relevance

These all want to: be authored on a carrier concept, ride the currently active
binding/scope, be evaluated against current state, be projected into the right
pipeline, and disappear cleanly when no longer relevant — **as derived state,
never as mutated provider state.**

This note calls that unit a **Facet**.

---

## Core Insight: the Facet

A **Facet** is an *offered, concept-bound micro-entity with no graph identity*.
It is published into the scoped namespace once, and a downstream task **adopts**
it if the task wants it — given the facet's activation condition, the current
caller, and current state.

It has **context identity**, not **graph identity**:

- it is meaningful only relative to a carrier, subject, caller, or pipeline pass
- it may carry provenance (`source_id`, `subject_id`)
- it does **not** belong in the graph registry as an independent peer
- it can still carry conditions, payload, tags, and ordering metadata

This is the common thread between dynamic badges (`#113`), role-linked grants
(`#141`), sandbox visibility rules, and `MuBlock` discourse parsing.

### Publish once, pull to consume

A facet is *published* exactly once (the only "push" — collection into scope).
After that it is a passive entry on a discovery bus; tasks that care scan for it
and dereference. The role never knows the prose engine exists; the sword never
knows the combat resolver exists. The namespace entry is the rendezvous point,
and neither end is coupled to the other.

This is the same move the engine already makes with `on_gather_ns` +
`wants_caller_kind`, **flipped from type-driven to data-driven dispatch**: today
a handler self-selects on the *carrier's class*; a facet carries its relevance as
*data* (`when`, `applies_to`), so the consumer selects on the *facet's*
self-description. That is why a facet must be a self-describing value object, not
an opaque dict — relevance has to be decidable from the facet alone.

The facet is a **handle, not the payload**. It carries references (carrier,
subject); a consumer dereferences for deep detail (the subject's full media
library, the modifier's rules). Scope never bloats even when the source detail is
large.

---

## The Affordance / Dependency Symmetry

A facet has a **polarity**:

- A **mu-affordance** is a facet that *offers a grant* — additive. "Here is
  more." (title, light, `+1`, a whispered line, an extra choice.)
- A **mu-dependency** is a facet that *imposes a restriction* — it injects a
  requirement/condition onto the consumer's task. "You may not, unless…"
  (darkness suppresses movement; Stormbringer suppresses `peaceful` choices;
  `require-light` choices are gated until a `light` grant is active.)

This is the **same shape with opposite polarity** — the micro-layer mirror of the
graph-level duality where an `Affordance` *offers* a provider and a `Dependency`
*requires* one (same edge shape, opposite fixed endpoint). A restriction is
simply a dependency the consumer didn't author for itself, contributed from an
indirect source.

> Naming consequence: "mu-affordance" names only the grant pole. The umbrella is
> the **Facet**; the two poles are mu-affordance (grant) and mu-dependency
> (restriction). This note keeps its filename for continuity but is about both.

### The non-dual escape hatch: Transform

A third operation does **not** fit the duality and should not be forced into it:
a **structural transform** of an assembled contribution bag — e.g. a dialog
enrichment that splits journal fragment 1 into 1 + 4 and inserts 2, 3 between
them. That is a positional, non-commutative rewrite, not a value with a fold.
It rides the *same carrier and activation skeleton* as a facet, but its payload
is an operation, not a declarative grant/restriction. Keep it rare and explicit;
do not pretend it is "grant `title: boss`."

---

## Anatomy of a Facet

```text
Facet  — microconcept value object, no graph identity, carried by a concept
  channel    : which pipeline may adopt it — ns | prose | choices | navigation | challenge …
  effect     : affordance (grant) | dependency (restriction)   [ transform = escape hatch ]
  when       : Predicate over the gathered ns  (activation; selectors + Expr, no hard links)
  applies_to : selector for the caller / subject / target it acts on
  payload    : grant data, or restriction (suppress + optional replacement)
  influence  : weight for precedence / stacking
```

- `when` reuses the existing core `Predicate` (`tangl.core.runtime_op`), already
  used by `SandboxVisibilityRule.when`.
- A concept carries `facets: list[Facet]`.
- A **generic per-channel adapter** collects in-scope facets and a task *adopts*
  one when `when` holds ∧ its `channel` matches the pipeline ∧ `applies_to`
  matches the caller. There is **one adapter per channel**, not per-concept code —
  that is what keeps a multi-pipeline concept (Stormbringer) encapsulated in one
  authored entity instead of scattered across the graph.

Phase-1 `RoleGrant` is the degenerate case:
`RoleGrant ≡ Facet(channel=ns, effect=affordance)`.

### Combine semantics are per-consumer

The adapter collects and filters; **the consumer chooses the fold**. Do not
hardcode one rule:

- a *name / title* grant may **override** (a role sets your one title) or
  **decorate** (a drawn sword appends "…and His Hungry Blade" as an ordered
  suffix) — same channel, opposite fold, which is exactly why the fold is the
  consumer's call, not the facet's
- a *+1 combat* grant **stacks** additively (two buffs = +2)
- *tags* **union**
- a *restriction* **gates / replaces**, and should **tombstone** rather than
  delete — record which facet suppressed what (and any replacement), so the
  operation is auditable, replay-stable, and reversible when its `when` lapses

`SandboxProjectionState` already is a tombstone: it records `active_rules` plus a
replacement `journal_text` instead of mutating the bag.

---

## Conditioning Vocabulary and Pre-Flight Coverage

Facets condition on — and target — **tags and published properties**, never hard
links. The vocabulary is the author's: `commerce`, `sheathe`, `peaceful`,
`require_light`, `is_friendly`, and so on are world-level conventions, not engine
types. A choice the NPC author tagged `commerce` is what lets a *different* concept
in your inventory (Stormbringer) suppress it; the coupling is by shared tag, not by
reference.

Core's job is only to **gesture at the shape**: ship a minimal default inventory of
published node properties so authors have a starter kit and a worked pattern — e.g.
sandbox nodes publish `is_dark`, `is_lit`, `is_friendly` into ns, adoptable
directly as `if here.is_dark(): grues.approach()`. Authors extend the vocabulary
freely; the engine does not police it.

It can, however, **check coverage**. Because targeting is by tag, a `when` /
`applies_to` that references a tag nothing ever *produces or presents* is a dead
condition — a logic flaw or a redundancy. A **pre-flight coverage check** can flag
"this restriction conditions on `require_light`, but no concept in this world grants
`light`," exactly as the compiler already flags dangling actor/location references
(`_collect_provider_ref_issues`, `ISSUE_DANGLING_*`). This is a **world /
compile-time concern, not a core one**: core ships the starter vocabulary and the
diagnostic hook; the `WorldCompiler` owns the actual coverage check and any deeper
solvability analysis.

---

## Reference Implementations

The two poles already exist in the codebase; the work is to name the shared
shape and lift them onto it.

### Affordance pole — phase-1 role grants (built, issue `#141`)

`RoleGrant` (`engine/src/tangl/story/concepts/role.py`) is an authored grant
carried on a `Role` binding. While the provider is resolved, `contribute_roles`
projects it as a derived `ns`-channel overlay: `{label}_{key}` scalars,
`{label}_tags`, a per-binding `role_grants` accessor, and merged
`grants`/`grant_tags` views. Precedence: nearer-scope binding overrides/clears;
across labels the merged map resolves a shared key by `priority`. Authorable via
the role `grants:` key.

### Dependency pole — sandbox visibility (built)

`SandboxVisibilityRule` (`engine/src/tangl/mechanics/sandbox/visibility.py`) is a
restriction facet in all but name: a `when` list of predicates over ns, a set of
suppressions, a replacement `journal_text`, OR-folded into a
`SandboxProjectionState` that records provenance. It already chose the right
modelling: **light is the positive grant** (`LightSourceFacet`,
`sandbox_has_lit_light_source()` in ns); **darkness is the default restriction
that fires when no light grant is active** — not a negative grant. Today its
suppression target is three fixed categories; the generalization is to make the
target a **selector** (`choices tagged peaceful`) instead.

### Both poles on one concept — the Stormbringer loop (worked example)

A single inventory concept carries a bundle of facets plus a little state, and the
whole episodic puzzle *emerges* from their interaction — with no imperative script
wired into the scenes where the beats happen to occur:

```text
Stormbringer  (state: drawn, fed)
  Facet(navigation, affordance, when="drawn",             payload=light)         # a magic sword glows
  Facet(prose,      affordance, when="drawn",             payload=whisper_line)  # it murmurs
  Facet(ns,         affordance, when="drawn",             payload=name_suffix:" and His Hungry Blade", fold=decorate)
  Facet(choices,    affordance, when="drawn and not fed", payload=add:cut_self)  # offers a bloodletting
  Facet(choices,    dependency, when="drawn and not fed", applies_to=tag:commerce, suppress)
  Facet(choices,    dependency, when="drawn and not fed", applies_to=tag:sheathe,  suppress)
  # actions feed it:  attack/kill -> fed=true   |   cut_self -> fed=true (costs hp)
```

Run the lamp dry (`ChargeFacet -> 0`; its `light` affordance withdraws, so the
darkness dependency suppresses movement) and you are *forced* to draw the sword
for its `light`. At the merchant, the `not fed` hunger gate splits into the Elric
tragedy:

- **kill the merchant** — feeds the sword on the NPC, stay drawn, walk on (no oil,
  a corpse); or
- **cut yourself** — feed it at your own cost, which lifts the gate so you may
  sheathe, trade, buy oil, relight the lamp, and proceed unbloodied.

Both resolve the same `when="not fed"` gate; the **consequences live on the
actions, not the facets**. There is always an out (so no hard lock — the general
hazard is *coverage*, below). And the payoff is **portability**: none of this is
wired into "the cave scene" or "the battlefield scene." The behavior travels with
the concept — drop Stormbringer into a labyrinth or a nighttime battlefield and
the same few functional descriptions reproduce the entire loop. A scattered
imperative if/else across every phase where a beat *might* fire collapses into a
handful of declarative facets that go where the concept goes.

The smallest facet in the bundle is the oldest: `name_suffix` is **phase-1's title
grant**, now bound to the *holder* and gated on `drawn` — *Bill the Adventurer*
becomes *Bill the Adventurer and His Hungry Blade* while the blade is out and
reverts the instant it goes away. Same mechanism as `grant title: boss`, but with a
**decorate** fold instead of override; were you also the boss it would compose to an
ordered *Boss Bill … and His Hungry Blade*. One worked demo now exercises every
channel and both poles, and reuses the first thing built.

A Disco-style **voice** is the same skeleton, with `influence` graduating from a
tie-breaker into a **passive-check weight**: activation generalizes from "binding
present" to **bound ∧ relevant (`when`) ∧ influence-check-passes**.
"Always-available" voices are just high-scope bindings, the trick `Player` uses.

---

## Existing Prior Art

### MuBlock (discourse parsing)

`MuBlock` (`engine/src/tangl/prose/mu_block.py`) is a render-oriented
microconcept: smaller than a block, never in the graph, promoted to a fragment
via `to_fragment()`. It is the clearest proof StoryTangl already benefits from
managed non-entity intermediates, and a candidate to share a base with facets
later (Phase 4).

### Dynamic badges (`#113`)

The old badge system (`scratch/mechanics/badge/badge.py`) is the "ur facet": it
already had *both poles* (grant tags / hide-supersede), topological ordering, and
projection into both condition context and render output. Its weakness was
plumbing, not concept — explicit node mutation and global rescans instead of
derived projection.

---

## Design Rules

1. **Derived beats stored.** If a property can be computed from current topology
   and context, project it; never mutate provider/holder state.
2. **Prefer a positive affordance + gate over a negative dependency.** Model the
   capability (`light`) and let the restriction be "default when the capability is
   absent." Reserve active restrictions for genuinely subtractive intent with no
   positive form (Stormbringer's "peaceful unavailable until it swings").
3. **Share discovery, not the fold.** One per-channel adapter does collection +
   `when`/`applies_to` filtering; only the *fold* is bespoke. Otherwise the
   duplication you avoided reappears at the consumption layer.
4. **Tombstone restrictions.** Suppress with provenance + optional replacement;
   do not destructively delete from the bag.
5. **`when` must be replay-deterministic.** Any activation that reads rolly /
   influence state must resolve identically on every replay of the same trace, or
   it breaks fabula-invariance and replay-as-reskin.
6. **Context is part of the contract.** Facets are meaningful only relative to
   their binding/caller; that is what distinguishes them from free-floating data.
7. **Promote only when necessary.** Durable identity, inventory presence, or
   independent mutable state → a real Entity/Token. Otherwise stay a facet.
8. **Story semantics live above the generic layer.** The core layer knows
   channels, polarity, activation, folding; story code knows titles, uniforms,
   badge text, whispers, and "too dark to see."

---

## Naming Reconciliation

The sandbox already spends **"Facet"** on *typed capability components*
(`LightSourceFacet.illuminates()`, `ChargeFacet.consume()`) — behavioral policy
objects, not grant/restriction entries. These are a different layer. Preferred
resolution: the core micro-affordance entry takes the word **Facet**; capability
objects *emit* facets (a lit `LightSourceFacet` emits the `light` grant). Rename
the sandbox capability classes (`…Capability` / `…Policy`) **when the sandbox
migrates onto the core model**, not before — but choose the distinction
deliberately rather than colliding.

---

## Phased Strategy

### Phase 1 — affordance grants on bindings (DONE, `#141`)

`RoleGrant` + `ns`-channel projection from active role bindings. The degenerate
facet; the first conformance consumer.

### Phase 2 — promote `Facet` to a shared primitive

Introduce the `Facet` value object (core-neutral data + `Predicate`) and refactor
phase-1 role grants to be its first `effect=affordance, channel=ns` consumer. No
new behavior; the rail under what already works.

### Phase 3 — the dependency pole as a shared restriction channel

Generalize `SandboxVisibilityRule` into `effect=dependency` facets whose
`applies_to` is a selector over choices/affordances, consumed by the planning /
navigation pipeline. Settle restriction **conflict resolution** here (selector
vetoes don't OR like booleans).

### Phase 4 — more channels and influence

`prose`/`journal` grants; influence-weighted voice activation (passive checks,
deterministic); the Transform escape hatch for journal-compose restructuring;
evaluate a shared base with `MuBlock`.

### Out of scope (stays separate, may share vocabulary later)

A universal heavy/light task dispatch split; replacing existing VM phase wiring;
global reactive rule engines; persistent snapshotting of derived facet state.

---

## Load-Bearing Decisions (settle before core code)

- **`effect` / `channel` enums.** Is `transform` a third `effect`, or its own
  carried-operation type? (Leaning: its own type — it is not a fold.)
- **Restriction conflict resolution.** Two restrictions on one choice — veto
  wins? priority? The sandbox OR's booleans; selector-targeted vetoes need a
  defined policy.
- **Replay determinism** of influence/rolly `when` predicates.
- **`applies_to` selector shape** — what a facet is allowed to target.
- **Placement.** `Facet` value object in `tangl.core`; channel adapters where each
  pipeline lives (VM / story / journal). Do not pull pipeline knowledge into core.
- **Coverage / solvability is world-level, not core.** The pre-flight check that
  every conditioned tag is presentable somewhere (see *Conditioning Vocabulary*)
  lives in `WorldCompiler` diagnostics, beside the dangling-ref checks. Core ships
  only the starter vocabulary and the hook — not the analysis.

---

## Open Questions

- Should bound subject views be proxy objects, plain mappings, or lightweight
  accessors? (Phase 1 chose plain mappings.)
- Per-subject vs scope-wide merge of grants. Phase 1 merges scope-wide as a
  convenience; the principled primitive is per-subject (the holder accumulates),
  which the combat/voice cases will force.
- How much code should `MuBlock` and facets actually share, versus terminology?

---

## Near-Term Outcome

A single way to represent **managed, entity-like things with less identity than
Entities** — concept-bound, condition-gated, channel-routed, polarity-aware
(grant or restriction), folded with provenance — so StoryTangl can bind temporary
properties and constraints to providers/holders through relationships, carry them
through the VM without graph registration, and keep rendered fragments as the
final output vocabulary. Phase 1 is the worked example; the Facet is the
generalization.
