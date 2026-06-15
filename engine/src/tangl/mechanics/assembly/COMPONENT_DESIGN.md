# Components as Facet Bundles

```{storytangl-topic}
:topics: assembly, open_link
:facets: overview, design
:relation: defines
:related: presence, credentials, sandbox
```

**Document Version:** 0.2
**Status:** DESIGN — the bridge spec that routes the assembly/component work
*through* the facet generalization (`MU_AFFORDANCES.md` v0.3) instead of beside it.
*v0.2: facet discriminator split into `channel` (relevance) + `facet_type`
(giver/changer/hider); trinary mapped onto the open-link duality.*
**Builds on:** `docs/src/notes/MU_AFFORDANCES.md` (the Facet model), this package's
`PRESENCE_ASSEMBLY_DESIGN.md` neighbour (the slotted instrument), and
`docs/src/design/planning/AFFORDANCE_MODEL.md` (the open-link duality this mirrors).
**Prior art:** `concepts/role.py` `RoleGrant` (#141, the degenerate affordance facet),
`mechanics/sandbox/visibility.py` `SandboxVisibilityRule` (the degenerate restriction),
`mechanics/assembly/base.py` `SlottedContainer`.

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

## Build order (and what is deliberately deferred)

1. **#287 merges** — `RoleGrant`, the clean degenerate facet, lands as-is.
2. **Generalize the facet data shape minimally** — a co-located `Facet` value object
   (discovery / provenance / activation only). **Not promoted to `tangl.core`.**
3. **Build the component mechanic** as the forcing second consumer (this doc).
4. **Next pass — retrofit** `RoleGrant` + `SandboxVisibilityRule` + the sandbox
   capability classes onto the same tooling. *Then* there are ≥3 consumers, which is
   the bar to (a) promote the primitive to core, (b) resolve the `Facet` name, and
   (c) decide sibling-vs-coordinate against the open-link primitive.

Deferring (3 calls that do **not** belong in this pass):
- **Core promotion** — premature until the retrofit proves the shape across consumers.
- **The `Facet` name** — sandbox already spends "Facet" on typed capability classes
  (`LightSourceFacet`, …) across ~13 files. This pass keeps the generalized term
  **internal**; the *authoring surface* is `component` / `grant` / `requirement`, so
  nothing user-facing collides and the sandbox classes are untouched. Reconcile when
  they actually meet, in the retrofit pass.
- **Sibling vs coordinate** — is a facet a new type, or the open-link `Requirement`
  with a `context-identity` (no graph identity) coordinate? Building components
  concretely *shows* the shape; decide with evidence, not speculatively.

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
> tombstoning question. Model it as a `changer` whose payload is a sequence operation,
> but keep its ordering/determinism rules explicit — it is the corner of `changer` that
> needs care.

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

## The three positions components force (the point of choosing them)

Components confront the hard parts immediately — a feature, not a cost. This spec must
take a position on each; they are the substance of the implementation:

1. **Restriction conflict resolution.** Two components' `*_restriction` facets on one
   slot/choice. Selector-targeted vetoes do **not** OR like `SandboxVisibilityRule`'s
   three fixed booleans. Proposed default: a veto is sufficient (most-restrictive
   wins) unless a higher-`influence` grant explicitly lifts it; record the deciding
   facet in the tombstone. Settle here.
2. **Per-subject merge.** The holder-scoped accumulation ("what does Bill currently
   contribute?", "what modifies *this* challenge?", "what restricts *this* choice?")
   is the principled primitive; phase-1's scope-wide `grants`/`grant_tags` view stays
   as a compatibility projection over it.
3. **Tombstones.** A restriction outcome is `hidden | blocked | replaced |
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

## Worked demo

The Stormbringer matrix above is the end-to-end demo: one carrier whose facets span
`giver`/`hider` across `nav` and `choice`, a `changer` on `ns`/`challenge`, per-subject
merge (the holder accumulates), tombstoned restrictions, and stateful activation — with
no imperative script in the scenes where the beats fire. A smaller first cut is a
lantern (a `nav` `giver` of `light`, withdrawn at `ChargeFacet → 0`) plus a sword in a
slotted inventory, which already exercises giver + hider + per-subject merge without the
full feed loop.

## Acceptance

- A `Facet` value object with `channel` + `facet_type` (giver/changer/hider) string
  discriminators + `when`/`applies_to`/payload/provenance, co-located (not core).
- A `Component` = concept + `facets` bundle, assignable into a `SlottedContainer`;
  slotting publishes facets, unslotting withdraws them.
- One gather + handler pair for each of: `channel="ns"` giver (reuse #141's path),
  `channel="choice"` hider (the forced new restriction path), and one non-ns giver or
  changer (`nav` or `challenge`).
- The three positions (conflict / per-subject / tombstone) implemented and tested.
- The worked demo passing end-to-end.
- `#194/#195/#196` satisfied through this model, with their issues updated to point here.
- Name, core promotion, and sibling-vs-coordinate explicitly left to the retrofit pass.
