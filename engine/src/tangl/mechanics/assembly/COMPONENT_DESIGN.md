# Components as Facet Bundles

```{storytangl-topic}
:topics: assembly, open_link
:facets: overview, design
:relation: defines
:related: presence, credentials, sandbox
```

**Document Version:** 0.1
**Status:** DESIGN — the bridge spec that routes the assembly/component work
*through* the facet generalization (`MU_AFFORDANCES.md` v0.3) instead of beside it.
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

- it **imposes requirements** (slot compatibility = a restriction it carries) **and
  offers grants** (capability: light, +combat, a title) — **both poles on one carrier**;
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

## The facet is a string discriminator, not a subclass

A facet's "type" is a **discriminator string**, exactly like `fragment_type` on
`BaseFragment` — **not** a Python subclass.

```text
# NOT this:
class NavigationFacet(Facet): ...   ;  isinstance(x, NavigationFacet)

# this:
Facet(facet="nav_grant", ...)       ;  facet.facet == "nav_grant"
```

```text
Facet  — scoped contribution candidate; no graph identity; carried by a concept
  facet      : discriminator string, convention "{channel}_{polarity}"
               e.g. ns_grant | choice_grant | choice_restriction | nav_grant
                  | challenge_grant | prose_grant | ...
  when       : Predicate over the gathered ns   (activation; reuses core runtime_op)
  applies_to : Selector for the caller/subject/target it acts on
  payload    : grant data, or restriction (suppress + optional replacement)
  influence  : weight for precedence / stacking / passive-check
  provenance : source_id, subject_id  (context identity, not graph identity)
```

Why a string and not a subclass:
- **Keeps the primitive small** — a tag cannot grow methods, so a facet stays a value
  (discovery / provenance / activation), never a mini-handler. (PR-review rule #3.)
- **Data-driven, not type-driven dispatch** — the v0.3 "flip": the facet self-describes
  its relevance as data, so a consumer selects on the *facet's* value, never on the
  carrier's class. One `Facet`, many discriminators; channels grow without a subclass
  explosion.
- **Precedent** — this is how `fragment_type` already works.

`RoleGrant` is the degenerate case: `RoleGrant ≡ Facet(facet="ns_grant")`.

**One open call:** single `facet` string vs separate `channel` + `effect(polarity)`
fields. The `{channel}_{polarity}` convention lets a handler match a channel-prefix or
a small set, which covers "this channel, either polarity." Start single (smallest
thing that works); split into two fields only if independent cross-channel/cross-
polarity querying becomes common.

## Component = concept + facet bundle

A **Component** is a concept (or a token over a component type) that carries
`facets: list[Facet]`, optional typed capability/state, and is assigned into a
`SlottedContainer` slot.

- **Slot compatibility / requirement** = a `*_restriction` facet the component imposes
  on its slot or holder (this is #194 slot-dependency validation).
- **Capability grant** (light, +combat, a title, a permit) = a `*_grant` facet
  (a credential-packet's permit, a robot part's capability, a lantern's light).
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
in-scope namespace for facets whose discriminator is phase-relevant — e.g. the choice
projector gathers `choice_grant` + `choice_restriction`; the ns handler gathers
`ns_grant`; a challenge resolver gathers `challenge_grant`. The gather collects,
filters by discriminator + `when` + `applies_to`, and hands the survivors to the
handler; **the handler owns the fold** (override / decorate / stack / union / gate).

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

A Stormbringer-style component (or, smaller, a lantern + sword in a slotted inventory):
a single component carrying `nav_grant`(light), `challenge_grant`(+combat),
`ns_grant`(title, decorate fold), `choice_grant`(add: cut_self),
`choice_restriction`(suppress tag:commerce when `drawn and not fed`) — exercising both
poles, per-subject merge (the holder accumulates), tombstoned restrictions, and
stateful activation, end-to-end, with no imperative script in the scenes where the
beats fire.

## Acceptance

- A `Facet` value object with a `facet` string discriminator + `when`/`applies_to`/
  payload/provenance, co-located (not core).
- A `Component` = concept + `facets` bundle, assignable into a `SlottedContainer`;
  slotting publishes facets, unslotting withdraws them.
- One gather + handler pair for each of: `ns_grant` (reuse #141's path),
  `choice_restriction` (the forced new one), and one non-ns `*_grant`
  (challenge or nav).
- The three positions (conflict / per-subject / tombstone) implemented and tested.
- The worked demo passing end-to-end.
- `#194/#195/#196` satisfied through this model, with their issues updated to point here.
- Name, core promotion, and sibling-vs-coordinate explicitly left to the retrofit pass.
