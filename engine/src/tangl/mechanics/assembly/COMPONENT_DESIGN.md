# Components as Facet Bundles

```{storytangl-topic}
:topics: assembly, open_link
:facets: overview, design
:relation: defines
:related: presence, credentials, sandbox
```

**Document Version:** 1.0
**Status:** DESIGN — the bridge spec that routes the assembly/component work
*through* the facet generalization (`MU_AFFORDANCES.md` v0.3) instead of beside it.
*v0.2: facet discriminator split into `channel` (relevance) + `facet_type`
(giver/changer/hider); trinary mapped onto the open-link duality. v0.3: evaluation
order via a produces/consumes DAG (topo-sort), sharing its acyclicity check with the
#286 coverage analysis; the recursive light↔dark case. v0.4: conflict resolution reuses the open-link arbitration (scope distance → specificity → influence → hash) with genuine same-scope ties as a compile error — not a 2nd dispatch system. v0.5: convergence — the general mechanism does commutative-fold + scope-tiebreak + compile-flag and stops; non-commutative semantics are delegated to a specialized channel manager (OutfitManager coverage masks = the prototype); CSS-like !important arbitration is backburnered. This also resolves the positional-transform corner (a specialized journal-compose fold, not a generic changer). v0.6: division-of-labour framing — donated concepts (graph identity) vs context-bound facets (context identity) is one axis of the open-link primitive, author's-prerogative which side a capability sits on; this RESOLVES sibling-vs-coordinate (coordinate, not a rival type). Facets are a vocabulary convention, not a mechanism — handlers consume via shared gather or bespoke manager; the work is always the existing handler's. v0.7: staged implementation plan with the abstract shape-board acceptance demo (slot keying + connector polarity, giver description donation, additive/multiplicative/subtractive changer folds + target, discrete/continuous budgets) — the four stages each real consumer reskins. v0.8: adopt the v3.2 Associating/Connection bilateral-association substrate (admission/mutual-consent + on-associate/on-disassociate hooks) as the slotting mechanism — the facet model is the *what*, association is the *when/whether*; the N-party transaction generalization (trades, shops-as-assembly) is the same primitive, deferred. v0.9 (PR #288 review): anchor the facet gather/fold to the existing dispatch (PhaseCtx, on_gather_ns, BehaviorRegistry.chain_execute_all) — no new pipeline; scope the compile-time collision flag to the new per-subject fold (RoleGrant's grants/grant_tags merge unchanged).*
**Builds on:** `docs/src/notes/MU_AFFORDANCES.md` (the Facet model), this package's
`PRESENCE_ASSEMBLY_DESIGN.md` neighbour (the slotted instrument), and
`docs/src/design/planning/AFFORDANCE_MODEL.md` (the open-link duality this mirrors).
**Prior art:** `concepts/role.py` `RoleGrant` (#141, the degenerate affordance facet),
`mechanics/sandbox/visibility.py` `SandboxVisibilityRule` (the degenerate restriction),
`mechanics/assembly/base.py` `SlottedContainer`.

---

## Implementation Status: Owner-Bound Managers

The assembly layer now has two storage identities that share the same slot,
validation, budget, and facet-discovery APIs:

- `SlottedContainer[CT]` is the direct in-memory instrument used by demos, tests, and
  non-graph consumers. It stores component objects in its slots.
- `ComponentManager[CT]` is the owner-bound graph-aware specialization. It is embedded
  on a full graph member, persists with that owner, stores slot membership as component
  UUIDs, and dereferences those UUIDs through the owner's registry. Its `owner` pointer
  and transient construction cache are not constructor-form data.

This is the intended middle between "full graph member" and "plain Pydantic blob":
components remain full graph members when they need graph identity; embedded managers
serialize by value but hold graph members by reference.

`OutfitManager` is the first concrete manager on this path. A `HasOutfit` actor now
round-trips through `Graph.unstructure()` / `Graph.structure()` with outfit assignments
preserved as restored wearable graph members, not inline duplicates.

The neutral vehicle example is the second proof consumer. `Vehicle` embeds a
`VehicleLoadout`, while chassis, powerplant, suspension, and tire parts are
`VehicleComponent` graph tokens over `VehicleComponentType` singleton definitions.
The example exercises named single-occupancy slots, replacement-on-assign, required
slot validation, total price/weight validation, and a simple weight-to-powerplant
constraint without importing CarWars-specific semantics into the generic layer.

Follow-up retrofit targets remain open: credential packets, domain vehicle managers
such as CarWars adapters, robot assemblies, and any world-specific full-graph outfit
manager such as a future `SharedOutfit` / `FashionShowActor` demo.

---

## Why components are the forcing consumer

`RoleGrant` (affordance / ns only) and `SandboxVisibilityRule` (restriction / choices
only) are each *one pole on one channel* — edge cases. A **component** (a slotted
outfit/vehicle/credential-packet/automaton part, a sword, a lantern) exercises the
whole model at once:

- it **imposes restrictions** (slot compatibility = a `hider`), **offers grants** (a
  `giver`: light, a permit), **and modifies** (a `changer`: `+combat`, a title) — all
  three behaviours, **both open-link poles, on one carrier**;
- a slotted holder **accumulates** grants from many components — forcing **per-subject
  merge**, not phase-1's scope-wide convenience view;
- two components contending for a slot force **restriction conflict resolution** and
  **tombstones** (hidden / blocked / replaced), not a boolean.

So building the generalization *through* components stress-tests the shape that
RoleGrant and SandboxVisibility only sample. It is also the unification the
`PRESENCE_ASSEMBLY_DESIGN.md` brief asked for: the "common instrument" (slots +
budgets + occupancy + grants) is exactly a `SlottedContainer` of facet-bundles.

## Division of labour: donated concepts vs context-bound facets

There are two ways a scoped source contributes capability — a **sharp functional line and
a blurry semantic one**, as with most StoryTangl distinctions:

- A **graph-level open-link** (`Dependency` / `Affordance`) donates an entire **concept**
  that joins the namespace as a graph entity — a role donates an `Actor`, a setting a
  `Location`. Full graph identity; a first-class namespace participant.
- A **facet** donates a behaviour **signal** *through* its holder/parent concept —
  entity-like but **not a graph item** — conditionally giving / hiding / changing a
  specific behaviour when an active handler chooses to gather it. Context identity, no
  graph registration.

The line is **functionally sharp** (graph entity vs context-bound value) but
**semantically blurry**: the same capability can be expressed either way. `light` could
be a fully-realized concept; a `role`/`setting` could be implemented as a grant. Which
side a capability sits on is the **author's prerogative** — where they balance capability
resolution between full concepts and context-bound signals.

This **resolves the sibling-vs-coordinate question**: a facet is the *context-identity
coordinate* of the open-link primitive (graph-identity ↔ context-identity is the axis),
**not a rival ontology** — implemented as a lightweight value object only because
context-bound things don't need graph machinery. The retrofit pass therefore promotes a
*coordinate of the open-link family*, never a second primitive; there may be no new core
*type* at all, just a projection mode.

And facets are, at bottom, a **vocabulary convention** — a shared shorthand for "a scoped
source is signalling that an optional feature is available," so handlers need not each
reinvent the gather. A handler MAY honour the convention via the shared gather (cheap
default) **or** roll a bespoke manager when its fold is non-trivial (`OutfitManager`
coverage masks). Both are legitimate; the convention is a convenience, not a mandate.
This is the final reason it is **not a second dispatch system**: a facet is a *named data
shape*, and the work is always the existing handler's.

## Build order (and what is deliberately deferred)

1. **#287 merges** — `RoleGrant`, the clean degenerate facet, lands as-is.
2. **Generalize the facet data shape minimally** — a co-located `Facet` value object
   (discovery / provenance / activation only). **Not promoted to `tangl.core`.**
3. **Build the component mechanic** as the forcing second consumer (this doc).
4. **Next pass — retrofit** `RoleGrant` + `SandboxVisibilityRule` + the sandbox
   capability classes onto the same tooling. *Then* there are ≥3 consumers, which is
   the bar to (a) promote the primitive to core (as an open-link projection mode, per
   *Division of labour*), and (b) resolve the `Facet` name.

Deferring (2 calls that do **not** belong in this pass):
- **Core promotion** — premature until the retrofit proves the shape across consumers;
  and per *Division of labour* it is a coordinate/projection of the open-link primitive,
  so promotion likely adds a projection mode, not a new core type.
- **The `Facet` name** — sandbox already spends "Facet" on typed capability classes
  (`LightSourceFacet`, …) across ~13 files. This pass keeps the generalized term
  **internal**; the *authoring surface* is `component` / `grant` / `requirement`, so
  nothing user-facing collides and the sandbox classes are untouched. Reconcile when
  they actually meet, in the retrofit pass.

*Resolved (no longer deferred):* **sibling vs coordinate** — a facet is the
context-identity *coordinate* of the open-link primitive, not a rival type (see
*Division of labour*).

## Two string discriminators: `channel` (relevance) + `facet_type` (behaviour)

A facet's "type" is **data, not a Python subclass** — `fragment_type`-style strings,
never `class NavigationFacet(Facet)` + `isinstance`. There are **two** discriminators,
because they answer different questions:

```text
Facet  — scoped contribution candidate; no graph identity; carried by a concept
  channel     : str   — relevance selector: WHEN/WHERE it applies, i.e. which pipeline
                        may adopt it.    ns | choice | nav | prose | challenge | ...
  facet_type  : giver | changer | hider — BEHAVIOUR class; same encoding, different
                        consumption:  giver = add a contribution, changer = modify an
                        existing one, hider = remove / suppress / replace one
  when        : Predicate over the gathered ns     (activation; reuses core runtime_op)
  applies_to  : Selector for the concept / choice / target it acts on
  payload     : the offered value, the modifier, or the suppression (+replacement)
  influence   : weight for precedence / stacking / passive-check
  provenance  : source_id, subject_id   (context identity, not graph identity)
```

- **`channel`** is "just a selector for when it applies" — a choice handler gathers
  `channel="choice"`, an ns handler gathers `channel="ns"`. The relevance axis.
- **`facet_type`** is the behaviour axis. The three are *encoded the same way* (one
  value object) but *consumed differently*: a gather collects a channel's facets and the
  handler dispatches the fold by `facet_type` — **giver** appends/unions, **changer**
  applies a modifier (decorate a title, `+1` a check), **hider** tombstones (suppress /
  block / replace, with provenance). This is exactly why they are two fields and not one
  `"choice_grant"` string: a consumer wants *"this channel, all three behaviours"* and
  folds each behaviour differently.

Both stay strings (not subclasses): keeps the primitive small (a tag can't grow methods
— PR-review rule #3), is the data-driven-not-type-driven dispatch the v0.3 doc argued
for, and matches the `fragment_type` precedent. One `Facet`, many `(channel,
facet_type)` coordinates; channels and behaviours grow without a class explosion.

`RoleGrant` is the degenerate case: `RoleGrant ≡ Facet(channel="ns", facet_type="giver")`.

### How the trinary sits on the open-link duality

The two axes are orthogonal and it pays off here: `facet_type` maps onto the
`AFFORDANCE_MODEL.md` duality **plus its one exception** —

- **giver ≈ affordance** — offers a contribution ("here is more");
- **hider ≈ dependency** — imposes a restriction the consumer didn't author ("you may
  not, unless"). A restriction is a dependency contributed from an indirect source.
- **changer = the non-dual one** — the v0.3 "Transform escape hatch", now first-class
  because it is encoded the same way. The graph-level open-link has no analog (edges
  don't *modify values*).

So two of the three behaviours *are* the open-link primitive at context-identity scale;
only `changer` is genuinely new. That is the sharper answer to the sibling-vs-coordinate
question the retrofit pass must settle.

> **`changer` vs the positional transform.** `changer` cleanly covers *value* modifiers
> (decorate a title, `+1` a stat) — commutative-ish folds. The sharp edge is the
> *positional* bag transform from #192 (split journal fragment 1 → 1+4, insert 2,3),
> which operates on the assembled *sequence*, is non-commutative, and shares #192's
> tombstoning question. Per the conflict-resolution convergence (position 2), it is a
> **specialized-manager** case — the journal-compose consumer owns that non-commutative
> sequence fold; the general layer only discovers and activates it. So `changer`'s
> generic fold stays commutative (value modifiers); the positional rewrite is not a
> generic `changer` fold at all.

### Worked matrix — Stormbringer

The whole Elric loop is a list of facets on one carrier, with no imperative script in
the scenes where the beats fire:

| channel | facet_type | when | applies_to | payload |
|---|---|---|---|---|
| nav | giver | `drawn` | self / scene | `light` affordance (the blade glows) |
| choice | hider | `drawn and not fed` | `tag:peaceful` | suppress peaceful-tagged choices |
| choice | giver | `sheathed` | self | offer `draw_sword` |
| choice | giver | `drawn` | self | offer `sheathe_sword` (itself `tag:peaceful`) |
| choice | giver | `drawn and not fed and <restricted nearby>` | self | offer `feed_self` / `feed_other` |

The trap is **emergent**: the `sheathe_sword` offer is itself `tag:peaceful`, so the
`hider` suppresses it — you **cannot sheathe until you feed**. `feed_*` is a plain
`giver` whose *action effect* sets `fed=true`; that flips the `hider`'s `when` false,
lifting the restriction until the next draw resets `fed`. There is **no "un-hider"
primitive** — the restriction lapses because its activation predicate lapses, which is
exactly the derived-not-mutated invariant. (A `changer` appears in the fuller bundle:
the `ns` title decorate *Bill … and His Hungry Blade*; `+combat` would be a `challenge`
`changer`.)

## Evaluation order: the produces/consumes DAG

Facets are **recursive**: a light source (oil lamp / flashlight / Stormbringer) is a
`giver` of `lit`; `dark` is a default `hider` that suppresses navigation `when not lit`;
so a giver's output gates a hider. Three ordering layers, only one of which needs a sort:

1. **Authored state** (`drawn`, `fed`, `has_oil`) — read directly by `when`, changed by
   action effects *between* passes. No intra-pass ordering; it is just current state.
2. **Within-channel fold order** — `giver → changer → hider` within one channel pass.
   You cannot suppress the `sheathe` offer before a giver has offered it; hiders filter
   what givers/changers materialized.
3. **Cross-facet data dependency** — a `light` giver produces derived `lit`; the `dark`
   hider consumes it in `when = not lit`. Light must fold before dark in the *same* pass.
   This is the topological layer.

**The dependency edges are implicit — derive, don't author them.** Facets condition on
published properties/tags, not on named other-facets (the generalization of the old
badge-state topo-sort: badges named other badges; facets name *tags*). Each facet
**produces** the tags/properties its payload publishes and **consumes** the tags its
`when`/`applies_to` read. Build that produces→consumes graph, **topological-sort** it,
and fold forward; within one topo level apply layer-2 order (giver → changer → hider).

**One analysis, two payoffs.** The produces/consumes graph is the *same* structure as
the #286 coverage check: "conditions on `require_light` but nothing produces `light`"
(a dead/unsolvable condition) and "`light → dark → light`" (no valid topo-order, a
cycle) are both read off it. So acyclicity/solvability is a **compile-time
`WorldCompiler` check**, beside the dangling-ref checks — not a runtime concern. Cycles
are an author error for now; defer any runtime fixpoint iteration unless genuine
feedback loops are ever wanted.

**Interleaving with VM phases.** Facets relevant to a phase **settle to a fixpoint
before that phase's handler consumes them** — `lit` is folded into the derived ns before
nav provisioning reads the frontier, so you never "leave provision with all nav
restricted." Because facets are **derived, never mutated**, forward-only fold in
topo-order is automatically **replay-deterministic** (same graph, same order, every
replay) — no extra machinery needed for fabula-invariance.

> Contract: **produces/consumes DAG → topo-sort → fold each level giver→changer→hider →
> settle before the consuming phase.** Acyclicity checked at compile time, reusing the
> coverage analysis (#286).

## Component = concept + facet bundle

A **Component** is a concept (or a token over a component type) that carries
`facets: list[Facet]`, optional typed capability/state, and is assigned into a
`SlottedContainer` slot.

- **Slot compatibility / requirement** = a `hider` facet (on a slot/admission channel)
  the component imposes on its slot or holder (this is #194 slot-dependency validation).
- **Capability grant** (light, +combat, a title, a permit) = a `giver` facet
  (a credential-packet's permit, a robot part's capability, a lantern's light); a
  modifier like `+combat` is a `changer`.
- **Conditional enablement** = a facet `when` predicate (#195).
- **Default loadout** = component materialization on opt-in (#196).
- **Slotting publishes** the component's facets into the holder's scope (publish-once);
  unslotting withdraws them — derived, never mutated onto the holder.

So the cancelled "assembly-core" chip (#194/#195/#196) is **rebuilt as the component
mechanic through the facet lens**, not as a parallel slots-with-their-own-vocabulary
system. The four PRESENCE_ASSEMBLY drivers are the acceptance consumers: slotted
outfit, slotted vehicle (CarWars), credentials packet, robot/automaton (permits by
component purpose + conditional challenge effects).

## Consumer model: phase-handler gathers, opt-in

Each phase handler that wants to honour facets registers a **gather** that sifts the
in-scope namespace for facets in its `channel` — the choice projector gathers
`channel="choice"` (givers, changers, and hiders alike); the ns handler gathers
`channel="ns"`; a challenge resolver gathers `channel="challenge"`. The gather collects,
filters by `channel` + `when` + `applies_to`, and hands the survivors to the handler,
which **dispatches the fold by `facet_type`** (giver → append/union, changer → apply
modifier, hider → tombstone) and owns the specific combination rule.

- **Opt-in by construction** — a world author opts into a mechanic by publishing the
  facets. No facets of a discriminator → that gather finds nothing → zero cost. A
  world with no `choice_restriction` facets simply never pays for choice restriction.
- **Not a second dispatch system** (PR-review #1) — facets are *data* consumed by the
  *existing* phase handlers (ns gather, choice projection, provisioning, journal
  render). The shared abstraction is discovery + provenance + activation, never a
  universal `apply()`.
- **Anchored to the existing dispatch infrastructure** — the gather is an
  `@on_gather_ns`-style hook running under `PhaseCtx`, and the fold dispatches through
  `BehaviorRegistry.chain_execute_all` over the ordinary `on_*` / `do_*` pattern
  (`core/behavior.py`). There is **no new pipeline**: a facet gather registers on the
  same registry as every other handler. Naming it explicitly here is the guardrail
  against drifting into a parallel dispatcher.

## The four positions components force (the point of choosing them)

Components confront the hard parts immediately — a feature, not a cost. This spec must
take a position on each; they are the substance of the implementation:

1. **Evaluation order** (the recursion). The produces/consumes DAG + topo-sort + the
   giver→changer→hider fold + settle-before-phase, from the *Evaluation order* section
   above. This is the load-bearing one — light-lifts-dark and offer-then-hide both
   depend on it — and its acyclicity check is shared with #286.
2. **Conflict resolution — commutative-fold-or-flag; delegate non-commutative semantics
   to a specialized manager.** The general mechanism deliberately does *not* try to
   resolve arbitrary collisions — that road rebuilds the 2nd dispatch system PR-review #1
   forbids. It does three things and stops:
   - **Commutative folds are the bread and butter** — tags union, modifiers sum, light
     boolean-OR, vetoes most-restrictive-wins. Order-independent ⇒ no conflict. A
     `giver`/`changer` that respects its channel's commutative fold never collides.
   - **Scope distance is the cheap default tiebreak** where a natural ordering exists —
     `RoleGrant` already does "nearer-scope overrides." Free, structural, replay-stable.
   - **A genuine non-commutative / non-associative collision is an authoring error,
     flagged at compile time** off the produces/consumes graph (position 1 / #286):
     "`sword.color` set by `blue_grant` and `green_grant`, same scope, incompatible,
     overlapping `when` — disambiguate." The engine **guarantees determinism but never
     invents semantics** — it never silently picks blue over green.

   *Scope:* this compile-time flag applies only to the **new per-subject facet fold**.
   Phase-1 `RoleGrant`'s existing scope-wide `grants` / `grant_tags` view keeps its
   current deterministic merge (nearer-scope overrides, then `priority`) **unchanged** —
   those overlaps are resolved, not flagged.

   **Non-commutative *semantics* belong to a specialized channel manager, not the general
   fold.** Outfit inner-layer visibility is computed by `OutfitManager` through coverage
   masks — an order-sensitive, domain-specific fold that *consumes* the relevant facets
   rather than being resolved by the generic mechanism. That is the prototype: the
   general layer discovers + activates + commutatively-folds + flags; a registered
   manager owns any non-commutative fold for its channel. ("Share discovery, not the
   fold" at its endpoint — the general layer never owns a non-commutative fold.)

   **Deferred (backburner):** CSS-like specificity / `!important` overrides — a global
   "curse turns sword blue `!important`" beating a local "magic sword is red," mirroring
   the template-specificity work. It slots cleanly into the arbitration order after scope
   distance when wanted, with no architecture change to add later. Not now: settle the
   simple commutative parts first.
3. **Per-subject merge.** The holder-scoped accumulation ("what does Bill currently
   contribute?", "what modifies *this* challenge?", "what restricts *this* choice?")
   is the principled primitive; phase-1's scope-wide `grants`/`grant_tags` view stays
   as a compatibility projection over it.
4. **Tombstones.** A restriction outcome is `hidden | blocked | replaced |
   diagnostic`, not a boolean — provenance-bearing (which facet, what replacement),
   replay-stable, reversible when `when` lapses. `SandboxProjectionState` is the
   existing prototype.

## Invariants (carried from both #287 reviews)

- **Derived, never mutated.** Project from active topology + context; never write a
  grant/restriction back onto provider or holder. Keeps rebinding, equipment changes,
  light/darkness, titles, badges replayable.
- **`when` is replay-deterministic.** Any activation reading influence/rolly state
  resolves identically on every replay (fabula-invariance / replay-as-reskin).
- **Coverage is a world/compile concern.** "Conditions on a tag nothing presents" is a
  dead condition — a `WorldCompiler` diagnostic beside the dangling-ref checks. This is
  another concrete validator for the authoring-validation umbrella (#286), not core.

## Association: the slotting substrate (v3.2 prior art), and the transaction it generalizes

Slotting a component is a **bilateral association**, and v3.2 already built the mechanism
worth adopting — `scratch/legacy/core/core-32/graph_handlers/associating.py` +
`connection.py`:

- **`Associating`** — `on_can_associate` / `on_can_disassociate` (admission/approval
  pipelines) + `on_associate` / `on_disassociate` (side-effect hooks). `can_associate_with`
  runs the admission pipeline on **both** parties with inverse relationships (mutual
  consent: the holder approves the component *and* the component approves the host);
  `associate_with` = validate → mutual-consent preflight → fire `on_associate` on both.
  **Preflight → atomic → postflight, bilaterally.**
- **`Connection(gender, shape)`** — `connection_gender` (must be opposite) +
  `connection_shape` (must match), checked by `_check_is_compatible` on `on_can_associate`,
  plus `_check_is_not_in_use`. This **is** the shape-board Stage-1 keying: a star *plug*
  (one gender) seats only in a star *socket* (the complement) of the same shape, when free.

The facet model says *what* is donated; the association model says *when* and *whether*:
- **Slot keying / admission `hider`s (#194)** = `on_can_associate` handlers
  (`_check_is_compatible` for shape + connector polarity; budget / color / availability
  register alongside).
- **"Slotting publishes facets" / unslotting withdraws** = the `on_associate` /
  `on_disassociate` hooks — donation *on associate*, withdrawal *on disassociate*.
- **Eviction** ("remove the existing thing in that slot") = an `on_associate` pre-step.

Build Stage 1 on this — adopt the v3.2 `Associating`/`Connection` shape rather than
reinventing slot admission. (`OutfitManager`'s add/remove dispatch hooks *are* this.)

### The transaction generalization (deferred — note, don't build)

The same **preflight → atomic → postflight** shape is *every* transaction: buying,
selling, trading concepts/assets. A trade is an association where both parties donate
(goods ↔ payment) under mutual admission — so a **shop becomes a functional definition
over a type of assembly** (preflight: buyer can pay, seller agrees, item available →
atomic exchange → postflight: inventories settle), not bespoke code injected into shops,
owners, and inventories. That is the natural endpoint and **more than this pass needs**:
adopt the bilateral association substrate now (slotting requires it anyway); defer the
N-party / goods-for-goods infrastructure and shops-as-assembly until the basic component
shape is proven. When it comes it is the *same* primitive generalized, not a parallel
system — because slotting was built on association from the start.

## Implementation plan & the shape-board acceptance demo

An **abstract** demo isolates the mechanism from domain semantics while exercising exactly
what outfits / vehicles / robots / game-boards will need. A **shape board** has star,
circle, and square slots; star/circle/square **plugs** seat only in their matching
socket, each donating to the board's description and folding a number when seated. Each
of the real consumers is a variant of this: outfits add a Stage-2 coverage manager,
vehicles lean on Stage-4 budgets, robots use Stage-1 keying + Stage-3 capability folds,
game-boards use the Stage-3 target.

> *Terminology guard:* the board's **connector polarity** (plug vs socket / male vs
> female) is a *slot-compatibility* attribute, distinct from `facet_type`'s behaviour
> axis (giver/changer/hider). Two different "polarities"; keep them separate in code.

Staged so each step is a working slice with the board as the growing test:

**Stage 1 — slot-keyed assignment (the skeleton).** `Facet` value object; `Component` =
concept + facets; `SlottedContainer` assignment. **Keying:** a slot admits a component
by a compatibility key (shape) *and* connector polarity (a star *plug* seats in a star
*socket*; two sockets don't mate) — modelled on the v3.2 `Connection` admission (`on_can_associate` / `_check_is_compatible`:
opposite connector polarity, matching shape, not-in-use). This is #194 made concrete. *Test:* star plug seats in the star socket; rejected from the circle socket;
two star sockets don't mate.

**Stage 2 — `giver` description donation.** A seated component donates a `prose`/`ns`
`giver` describing its slot-state; the board folds them (commutative, ordered) into
*"A board with a filled star-shaped slot and empty circular and square slots."* *Test:*
description tracks fill state as components seat/unseat — derived, never mutated.

**Stage 3 — `changer` numeric folds + a target check.** `challenge`/value `changer`s
with different commutative folds: **star = additive (`+`), circle = multiplicative
(`×`), square = subtractive (`−`)**. Per-subject accumulation: the board accumulates its
seated components' changers; a validator checks "hit exactly *N* with the right three
shapes." *Test:* `{star +3, circle ×2, square −1}` computes the expected value
deterministically; the target validator passes/fails; replay-stable. (This is where
fold-order matters — the produces/consumes topo-order + commutativity keep it
well-defined; a non-commutative mix would be a Stage-3 compile flag.)

**Stage 4 — budgets (discrete & continuous).** `BudgetTracker` (`assembly/budget.py`): a
slot/board has capacity; seating consumes it (discrete count, or continuous
weight/power); over-budget seating is rejected by an admission `hider`. *Test:* a
3-slot discrete board and a continuous weight budget both gate seating.

Small steps, clean idea each time: every consumer (outfit / vehicle / robot / board) is
these four stages with a domain skin, not a new mechanism.

## Acceptance

- A `Facet` value object (`channel` + `facet_type` strings + `when`/`applies_to`/payload/
  provenance), co-located (not core); `Component` = concept + `facets`, assignable into a
  `SlottedContainer` (slotting publishes facets, unslotting withdraws them).
- One gather + handler pair for each of `channel="ns"` giver (reuse #141), `channel="choice"`
  hider (the forced restriction path), and one non-ns giver/changer.
- The produces/consumes DAG + topo-sort, with the light↔dark case passing and a
  `WorldCompiler` acyclicity/coverage check (shared with #286) flagging a cyclic fixture.
- The four forced positions (evaluation order / conflict / per-subject / tombstone) tested.
- **The shape-board demo passing through all four stages** (keying+polarity, description,
  additive/multiplicative/subtractive folds + target, discrete+continuous budgets).
- `#194/#195/#196` satisfied through this model; their issues updated to point here.
- Name, core promotion, and sibling-vs-coordinate left to the retrofit pass.
