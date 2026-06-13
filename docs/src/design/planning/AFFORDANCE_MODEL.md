# Open Links: Requirement-Bearing Edges and the Planning Matrix

*(formerly "The Affordance Model" — affordance is one direction of the primitive
defined here, not the whole of it; see the naming note at the end.)*

**Document Version:** 2.2
**Status:** CANONICAL — defines the **open link** as StoryTangl's planning
primitive and frames `Dependency`, `Affordance`, and `Fanout` against it via a
feature matrix. v2.2 fills in the #255 audit table (issues #255/#268). Several domain layers (menu fanout, sandbox interactions,
scheduled events) are *coordinates* in this matrix; some have drifted into
bespoke vocabularies and are noted as convergence debt rather than separate
concepts. The `OpenLink` base object near the end is a **mental model, not an
immediate refactor** — do not build it yet.
**Relevant layers:** `tangl.core` (Selector/Edge), `tangl.vm.provision`,
`tangl.story.episode`, `tangl.mechanics.sandbox`

See also:
[glossary.md](../glossary.md) ("Open Links and Projection") for the shared
vocabulary table these terms anchor,
[PROVISIONING.md](PROVISIONING.md) for how open endpoints are bound,
[HUB_FANOUT.md](../story/HUB_FANOUT.md) and
[SANDBOX_FANOUT_DESIGN.md](../../notes/SANDBOX_FANOUT_DESIGN.md) for the
link generators,
[INTERACTION_VOCABULARY.md](../story/INTERACTION_VOCABULARY.md) for the
client-facing rendering of projected links, and
[MU_AFFORDANCES.md](../../notes/MU_AFFORDANCES.md) for relationship-bound
microconcepts that ride on bound providers.

---

## Compact doctrine

> Dependencies pull from the cursor. Affordances offer from scoped or
> provisionable concepts. Fanouts generate many receiver-owned open links.
> Planning attaches cheap existing affordances first, then satisfies remaining
> dependencies through materialized or latent provisioners, ranks candidates by
> scope distance and materialization cost, and only then projects bound
> traversable links into choices. **Availability and suppression are use-time
> filters, not binding.**

The rest of this document expands that paragraph.

---

## Thesis

StoryTangl's planning model is built on **requirement-bearing open links**. A
relationship may be represented *before both of its endpoints are known*. A
`Dependency` and an `Affordance` are the same object with opposite fixed
endpoints; `Fanout` is a cardinality/rule-generation mode that produces many such
links. Planning **binds** open endpoints using scoped providers and provisioners,
then **projection** turns bound relationships into choices, namespace facts,
journal fragments, effects, modifiers, or redirects.

The operational discipline: **dynamic interactive opportunities should not spawn
new parallel channels.** They lower into the existing pipeline — scoped provider
contribution → requirement matching → binding (one) or fanout generation (many) →
phase-specific projection into ordinary outputs.

The founding motivation, kept in view: a choose-your-own-adventure is an
imperative, hand-threaded recipe, but it can be re-expressed **functionally as a
field of affordances** — provider-fixed open links the world publishes, bound
against whoever fits. The functional form is easier to validate for
**reachability and finishability**, because those are properties of which open
endpoints can ever bind, not of which choices an author happened to write. Think
of this as *pandoc for interactive fiction*: one intermediate representation that
authoring forms compile into and analyses run against.

---

## What an edge is here (read this before "fixing" anything)

In a completed mathematical graph an edge is usually modeled as an ordered pair:

```text
Edge = pair<Node, Node>
```

StoryTangl's runtime graph does **not** use that model. An edge is a first-class
graph entity representing a relationship, with endpoint *references* that may be
unresolved during planning. An **open link** is therefore not an invalid or
half-broken edge. It is a relationship object carrying a `Requirement` for a
missing endpoint:

```text
Open link = fixed endpoint + Requirement(open endpoint) + policy/predicates/provenance
```

Provisioning binds that endpoint or reports failure. This is intentional:
StoryTangl represents **self-assembling narrative structure**, not only finished
topology. The graph is a partially folded object whose relationship sites carry
shape constraints; planning is the folding/binding process.

The protein / self-assembling-jigsaw intuition is exact:

```text
A Dependency is a binding site on the requester.
An Affordance is a binding site on the provider.
A Requirement describes the shape that can bind there.
Provisioning performs the binding.
```

> **Implementation warning.** Do not "normalize" open links into only fully-bound
> graph edges. Open links *are* the planning surface. They are intentionally graph
> entities with one unresolved endpoint. Replacing them with ad-hoc side tables,
> nullable special cases, or fully-bound placeholder nodes hides the requirement
> from the provisioner and breaks the self-assembling graph model. The open
> endpoint is not a bug to route around; it is the basic unit of work in the
> provisioner.

---

## Direction: same object, opposite fixed endpoints

`Dependency` and `Affordance` are directional duals — the duality is about
**which endpoint is fixed**, not "push vs pull" (that only describes the
cursor-centric plumbing; candidates are gathered at the cursor either way):

```text
Dependency:
    fixed endpoint = requester/source, usually cursor
    open endpoint  = provider satisfying the requirement
    "this node needs something shaped like X"           (addressed)

Affordance:
    fixed endpoint = provider/concept
    open endpoint  = compatible requester/source/context
    "this concept can participate in something shaped like Y"  (broadcast)
```

In code both are `Edge + HasRequirement[PT]` with the same `set_provider` /
`set_successor` machinery, so one resolver matches both. They are **duals at the
matching surface, not synonyms in implementation** — they differ in **obligation
and failure semantics**:

- A **hard `Dependency` is consumer-side pressure.** If its open (provider)
  endpoint cannot bind, the frontier blocks and provisioning is driven to *make* a
  provider exist. The need is an obligation.
- An **`Affordance` is provider-side availability.** If its open (context)
  endpoint finds no taker, nothing is offered and nothing fails. The offer is
  optional.

So you cannot freely swap one for the other and keep behavior. Where obligation is
genuinely symmetric, an edge can be authored in whichever stance reads naturally
(`X needs Y` / `Y affords X`) and both lower to the same matching — but
obligation/failure stays an explicit property of the link.

### Mapping to the current VM linkage (do not reverse the wiring)

"Fixed endpoint" above is a statement about **ownership/origination** — which side
the open link conceptually belongs to and offers from — *not* a prescription for
the graph's `predecessor`/`successor` slots. The current provisioner deliberately
keeps both forms cursor-centric:

> Contract (`Resolver._iter_local_affordance_providers`): the frontier/source is
> the affordance **`predecessor`**, and the pushed provider/resource is the
> affordance **`successor`**. Fanout creates `Affordance(predecessor_id=source.uid)`
> then `set_provider(provider)`.

So in code **both** `Dependency` and `Affordance` wire `predecessor = frontier`,
`successor = provider`; they resolve at the cursor either way. The difference the
current `Affordance` encodes is *EXISTING-bias and push semantics* (a preferred,
already-available local provider), not a reversed edge. The conceptual
"provider-fixed" framing describes who *owns/offers* the link (e.g. "the sword
affords DrawSword"); it does **not** mean an implementer should swap the graph
endpoints. Converging #255 should preserve the `predecessor=frontier /
successor=provider` linkage and the existing provisioner semantics — the matrix
below is about classifying ownership, direction, and provider state, not about
rewiring topology.

---

## The planning matrix

This is the ontology. Every confusing case has a home as a row of coordinates,
so no new classes are needed:

| Axis | Values | Meaning |
|---|---|---|
| **Origin** | explicit / implicit | Authored static link vs rule-generated link |
| **Direction** | dependency / affordance | Fixed source requests provider vs fixed provider offers to source |
| **Provider state** | existing / latent | Materialized scoped entity vs template/token/provisionable offer |
| **Target kind** | concept / episode | Bound link resolves to a semantic provider vs a traversable node/action |
| **Use state** | available / unavailable | Binding may exist, but predicates can still block use |
| **Cardinality** | one / many | Single best binding vs fanout/all admissible bindings |
| **Arbitration** | scope distance / cost / specificity / priority | Ranking when multiple candidates satisfy the requirement |

### Origin (explicit/implicit ≈ static/dynamic)

```text
Static dependency:   this scene needs Actor(role="villain")
Static affordance:   sword affords DrawSword to compatible combat contexts
Dynamic dependency:  a menu rule generates one dependency per visible destination
Dynamic affordance:  every carried item with usable_here(ctx) generates an
                     affordance link to the cursor
Fanout:              a dynamic rule generates many open links, then binds/projects
                     each admissible target
```

So **`Fanout` is not a third peer** to dependency/affordance. It is a
*cardinality / rule-generation mode over open links* — receiver-owned enumeration
(menu) or provider-owned offering (dynamic affordances).

---

## Provider state is the architectural hinge: existing vs latent

When planning meets an open link, the open endpoint can be satisfied by either an
already-present entity or a provisionable plan — and this applies **symmetrically**
to both directions:

```text
existing / materialized:
    entity already in graph / scope / namespace

latent / provisionable:
    template, token singleton, update-clone, or other provisioner offer
    can create or expose it
```

```text
Dependency latent:  scene needs a villain; the provisioner can materialize one.
Affordance latent:  a global restart command or scheduled-event template can offer
                    itself here without being physically attached to every node.
Episode latent:     a projected choice points to a destination that can be
                    JIT-provisioned if selected.
```

The episode-latent case is crucial for traversable choices: a choice can be
*available in the menu* even if its destination is not fully materialized yet, as
long as the plan to materialize it is valid and cheap/acceptable. A bound link
therefore holds either a present reference (`provider_id`) or a deferred plan
(`provider_plan` / `provision_offer`); when materialization commits is
implementation detail. (See [PROVISIONING.md](PROVISIONING.md); the staleness /
refresh handling for latent menu targets is deferred in
[HUB_FANOUT.md](../story/HUB_FANOUT.md).)

---

## Target kind and projection: concept vs episode

The bound endpoint's kind is a real cut, **orthogonal** to direction:

```text
concept-binding:
    fills a role, setting, asset slot, mood, guide, modifier source, etc.
    Affects namespace / journal / effects but is not itself traversed.

episode-binding:
    resolves to a traversable node or edge. Projects as an Action / choice.
```

```text
sword affords "draw me":   provider = sword concept; projected destination may be
                           a self-loop / action / effect, not necessarily an episode
north exit affords travel: provider = neighboring location/episode; projected as a
                           traversable Action
villain role dependency:   provider = actor concept; no Action necessarily
scheduled festival event:  provider = event concept or episode; may project Journal
                           only, an Action, a redirect, or an availability modifier
```

This corrects the earlier mistake of "projection is decided by provider type."
Projection is handler dispatch:

```text
projection = function(link kind, bound endpoint kind, phase, predicates, context)
```

The caller kind and phase are the actual dispatch keys (e.g.
`@on_provision(wants_caller_kind=...)`). So **"affordance" does not mean
"choice"** — an affordance is just a provider-fixed open link; traversability is an
independent property of the bound endpoint. Outputs are ordinary: `Action` edges,
fragments, namespace values, filters, modifiers, redirects. No `ChoiceAffordance`
/ `ContentAffordance` / `ModifierAffordance` subclasses are warranted unless a
concrete second implementation forces one.

---

## Availability is after binding

Keep two questions separate:

> **Binding** answers "can this relationship be formed?"
> **Availability** answers "can this bound relationship be used now?"

```text
A door may bind as an exit, yet be unavailable because locked.
A sword may bind as a combat affordance, yet be unavailable because peace-bonded,
    silenced, cursed, or the player refuses violence.
A guide may bind as an interjection source, yet be unavailable because an atomic
    sequence suppresses inner voices.
```

Consequently, **planning should preserve unavailable-but-known links** when the
client wants to show disabled options, and filter them when the client profile
wants only executable actions. Availability and admission are use-time filters
applied *after* binding and projection — never folded into binding.

(The durable authored rule persists regardless; what is ephemeral is the
*projected* contribution recomputed each provision phase. A scheduled event's
schedule gate is a projection-time binding predicate — "is the action emitted this
phase" — distinct from these use-time availability predicates.)

---

## The source need not be the cursor

The fixed source/context endpoint is *usually* `ctx.cursor`, but planning must not
hardcode "the cursor asks." Define a default source/context and allow non-cursor
sources in scope:

```text
cursor source:     current block needs actor/location/destination/action provider
container source:  scene/hub admits global commands or schedule interrupts
actor source:      NPC seeks a target or projects an affordance into the scene
asset source:      sword affords draw/use/hone/wield
guide source:      inner voice affords interjection or choice pressure
world source:      restart/save/help commands afford globally
```

### Worked example — the "start over" command

Restart is the clean discriminator. It is **not** a dependency of every node, and
**not** a fanout owned by every node. It is a **provider-owned latent affordance**:

```text
RestartCommand concept:
    fixed provider = RestartCommand
    open endpoint  = any source admitting global commands
    requirement    = source accepts global-command affordances
    provider state = latent (offers itself without being attached to every node)
    projection     = traversable / system Action
    availability   = not inside an atomic / no-interrupt sequence
```

Atomic sequences do not need to know how restart works. They only **decline a
class of affordances**. That is the elegance the model buys.

---

## Planning as binding open links

Affordances are gathered/attached **before** dependency satisfaction, but
projection comes **later**. The subtlety: *attach* does not mean *project* — it
means "register candidate open links available in this context," which dependency
resolution can then consume before invoking heavier provisioners.

```text
1. Gather scoped namespace.
2. Attach existing affordances from scoped/materialized concepts (candidates, not Actions).
3. Use those attached affordances as first-class candidate providers for dependencies.
4. Resolve remaining dependencies through normal provisioning.
5. Optionally search latent/provisionable affordance providers (policy-gated; do not flood menus).
6. Apply fanout rules / dynamic link generation.
7. Rank, bind, project — then evaluate availability.
```

This yields a principled cost hierarchy and ranking rule:

```text
cheapest:   already-bound static relationship
cheap:      existing scoped affordance matches dependency
moderate:   existing findable materialized provider
higher:     latent token/template provider
highest:    update-clone / generated episode / forced provision
```

> **Ranking rule:** prefer the closest already-materialized compatible affordance
> before provisioning a new provider — i.e. sort by scope distance, then
> materialization cost, then specificity, then policy/priority.

### Reference algorithm (illustrative, not a build target)

```python
def plan_frontier(ctx):
    cursor = ctx.cursor
    ns = ctx.get_ns(cursor)

    # 0. Explicit open links already attached to cursor/context.
    dependencies = list(open_dependencies_from(cursor, ns))
    fanout_rules = list(fanout_rules_from(cursor, ns))

    # 1. Provider-owned affordance links from scoped concepts.
    #    These do not project yet; they become candidate relationships.
    existing_affordances = []
    for concept in scoped_concepts(ns):
        existing_affordances.extend(
            affordance_links_offered_by(concept, source=cursor, ctx=ctx, ns=ns)
        )

    # 2. Attach/match affordances immediately compatible with cursor/context.
    attached_affordances = [
        aff for aff in existing_affordances
        if link_predicates_pass(aff, ctx, ns)
        and source_admits_affordance(cursor, aff, ctx, ns)
    ]

    # 3. Satisfy explicit dependencies, preferring already-attached affordances.
    for dep in dependencies:
        if dep.provider:
            validate_or_refresh(dep, ctx, ns)
            continue
        candidates = []
        candidates += affordances_satisfying(dep, attached_affordances)
        candidates += existing_materialized_providers(dep.requirement, ctx, ns)
        candidates += latent_provisionable_providers(dep.requirement, ctx, ns)
        bind_best(dep, rank(candidates,
                            by=["scope_distance", "materialization_cost", "specificity"]))

    # 4. Dynamic links from fanout rules (receiver-owned enumeration).
    for rule in fanout_rules:
        for req in generate_requirements(rule, cursor, ctx, ns):
            candidates = existing_materialized_providers(req, ctx, ns)
            candidates += latent_provisionable_providers(req, ctx, ns)
            bind_or_project_many(rule, req, rank(candidates))

    # 5. Latent/provisionable affordance providers, only if policy allows
    #    (more expensive; should not flood menus by default).
    for offer in latent_affordance_offers(cursor, ctx, ns):
        if source_admits_affordance(cursor, offer.affordance, ctx, ns):
            attach_or_project(offer)

    # 6. Project bound traversable links as Actions; conceptual links as ns/journal/effects.
    project_bound_links(ctx, ns)

    # 7. Use-time filters: availability and suppression/admission.
    apply_availability_and_admission_policy(ctx, ns)
```

---

## The conceptual base object (do NOT build yet)

The clean mental-model base is an `OpenLink`; this is *not* an immediate refactor.
The existing `Dependency`, `Affordance`, and `Fanout` may already cover enough
without a new base class. Recorded only to anchor the vocabulary:

```python
class OpenLink:
    fixed_endpoint_id: UUID
    open_requirement: Requirement
    direction: LinkDirection           # DEPENDENCY or AFFORDANCE
    explicitness: LinkExplicitness     # STATIC or DYNAMIC
    cardinality: Cardinality           # ONE or MANY
    provider_state_policy: ProviderStatePolicy  # EXISTING, LATENT, BOTH
    predicates: list[Predicate]
    availability: list[Predicate]
    projection_hint: ProjectionHint | None
```

---

## Convergence debt (legible, not yet paid)

Choice was implemented first-class, with `Dependency`/`Affordance` generalized
afterward. So some code carries machinery the open-link ontology would express as
a matrix coordinate:

- `Action` carries a bolted-on `destination` `Dependency` and preview path
  (`_destination_dependency`, `_preview_destination_viability` in
  `story/system_handlers.py`). Clean model: `Action ≅ Dependency[TraversableNode]`
  with a projection handler; a static choice is the existing-provider default.
- **MenuBlock** projects through real `Affordance` edges
  (`project_menu_affordances`), but **the sandbox** does not use `Affordance` /
  `Fanout` at all — it hand-builds `Action`s in ~10 bespoke `@on_provision`
  handlers with a parallel `source="sandbox_*"` vocabulary.
- Inside the sandbox, interaction-bearing handlers route through the shared
  `_project_sandbox_interaction`, while the built-in verb handlers (take/drop,
  open/close, switch on/off) hand-roll `Action(...)`. Two vocabularies, one shape.
- Scheduled events already flow through `_project_sandbox_interaction` (via
  `event.as_interaction()`), proving the unification is half-built — but the
  provider surface is split into `get_sandbox_events` with no interaction peer.

### Near-term direction and the audit-first guard

**Do not start by migrating sandbox/location interactions through namespace
only.** A location interaction might be (1) an explicit static dependency, (2) a
provider-owned affordance, (3) receiver-owned fanout, or (4) authoring sugar that
compiles into one of those. If an agent picks the wrong interpretation it will
tidy code while hardening the *wrong* ontology.

So the first concrete step for #255 is an **audit table**, before any code moves,
with one row per mechanism and these columns:

```text
Mechanism
Current code path
Fixed endpoint
Open endpoint / Requirement
Direction (dependency | affordance)
Explicitness (static | dynamic)
Provider state (existing | latent)
Destination kind (concept | episode)
Cardinality (one | many)
Availability predicates
Projection target
Current duplication / drift
Suggested convergence path
```

Only then converge opportunistically: route new and touched code through one
interaction-contribution/projector path (scheduled events, actor/mob, asset,
fixture, wait/default, concept-provider interactions all share gather → match →
project), unify the provider surface (a single interaction-donating protocol
rather than `get_sandbox_events` + a parallel `get_sandbox_interactions`), and
mark the remaining bespoke action builders as convergence debt — **not** a sweeping
refactor.

The framing question for any new mechanic:

> **"Which row of the planning matrix is this?"** — not "what new interaction /
> event / action mechanism do we need?"

### The audit table (filled)

One row per dynamic-projection mechanism, verified against the code as of
v2.2. Columns are the guard's list above verbatim, plus three implementation
columns the guard deliberately omitted (`Source concept`, `Cleanup owner`,
`Existing tags / hints`), and with `Availability predicates` split into
**admission/binding predicates** (projection-time — "is the edge emitted this
phase", e.g. a scheduled event's schedule gate) and **live availability
predicates** (use-time), per "Availability is after binding" above.

This is classification, not a refactor plan. One logical table, split into two
physical halves for readability; same rows, same order.

**Part 1 — planning-matrix coordinates**

| Mechanism | Current code path | Source concept | Fixed endpoint | Open endpoint / Requirement | Direction (dependency \| affordance) | Explicitness (static \| dynamic) | Provider state (existing \| latent) | Destination kind (concept \| episode) | Cardinality (one \| many) |
|---|---|---|---|---|---|---|---|---|---|
| `Action` destination dependency | `_destination_dependency` / `_preview_destination_viability` (`story/system_handlers.py`); created by `fabula/materializer.py` (`Dependency(label="destination")`); resolved at selection (`vm/runtime/ledger.py`) | Authored choice with unresolved successor ref | The `Action` edge (requester) | Traversable destination node; `hard_requirement=True`, ref/path-shaped | dependency | static | existing or latent (episode-latent; JIT-provision on selection) | episode | one |
| Menu fanout | `Fanout` wired by materializer (`_wire_menu_fanout_for_block`); `Resolver.resolve_fanout` → dynamic `Affordance` edges; `project_menu_affordances` (`story/system_handlers.py`) | `MenuBlock.menu_items` selector rule | Menu block (receiver) | Each node matching the fanout requirement (e.g. `has_tags`) | receiver-owned fanout (dependency-stance enumeration) | dynamic | existing (latent menu targets deferred; see HUB_FANOUT.md) | episode | many |
| Sandbox location exits / movement | `project_sandbox_location_links` (`mechanics/sandbox/handlers.py`) | `SandboxLocation.links` authoring data | Location (sponsor) | Neighboring location by ref (`_resolve_location_ref`); message exits self-loop | affordance | dynamic | existing (unresolvable refs skipped, never provisioned) | episode | many |
| Sandbox sponsored interactions (location / fixture / asset / mob) | `_project_sandbox_interaction` via `project_sandbox_location_interactions`, `_project_fixture_interactions`, `_project_asset_interactions`, mob loop in `project_sandbox_mob_actions` (same file) | `SandboxInteraction` authoring sugar on a scoped sponsor | Sponsoring concept (location / fixture / asset / mob) | Interaction target (`"current"` self-loop or resolved traversable ref) | affordance | dynamic | existing | episode | many |
| Sandbox built-in verbs (take/drop, open/close, switch, lock/unlock) | Hand-rolled `Action(...)` in `project_sandbox_asset_actions` (+ asset/container helpers, `_project_mob_asset_actions`), `project_sandbox_unlocks`, `project_sandbox_fixture_actions` | Trait/facet declarations (portable, switchable, container, lockable, openable) | Sponsoring asset / fixture / mob, via the location | None materially — self-loop on location; the verb is admitted by facet state | affordance | dynamic | existing | episode (self-loop; the work happens in effects) | many |
| Sandbox scheduled events | `_scheduled_event_contributions` → `project_sandbox_scheduled_events` → `event.as_interaction()` → `_project_sandbox_interaction`; provider seam `get_sandbox_events` (`_provider_scheduled_events`) | `ScheduledEvent` on scope / location / fixture / mob / asset (incl. carried), or provider-donated | Sponsoring concept (or donating provider) | Event target node; requirement = schedule + presence match | affordance | dynamic | existing sponsors; provider donations lean latent (event not graph-attached until projected) | episode | many |
| Sandbox wait / time | `project_sandbox_wait`; time advance via `advance_sandbox_time_on_action` + tick pipeline (same file) | Scope/location wait policy (`wait_enabled` / `wait_text` / `wait_turn_delta`) | Location (scope policy) | None — self-loop | affordance | dynamic | existing | episode (self-loop; time cost in payload) | one |
| Game self-loop moves | `_build_game_actions` via `provision_game_moves` (`mechanics/games/handlers.py`); re-projected after UPDATE in `process_game_move` | `HasGame` handler `get_provisioned_moves` | Game block (self) | None — self-loop per move; requirement = game READY | self-fanout (provider-fixed offer to itself) | dynamic | existing | episode (self-loop) | many |
| Adventure movement hazards | `_rewrite_movement_hazards` in `project_adventure_world_actions` (`worlds/adventure_sandbox_slice/…/domain.py`) | `AdventureMovementHazard` rule on location (world authority) | Location | Consumes an already-projected movement action, rewrites it to a self-loop | overlay on a projected affordance (blocked/diverted open edge) | dynamic | existing | episode (self-loop presented as attempted movement) | many |
| Adventure magic words | Anchor loop in `project_adventure_world_actions` (same file) | `AdventureMagicAnchor` — latent command sponsored by location | Location | Anchor target location | affordance | dynamic | existing (the offer is discovery-gated, not provisioned) | episode | many |
| Adventure treasure deposit / scoring | Deposit loop in `project_adventure_world_actions` + `apply_adventure_world_action` (UPDATE, same file) | Deposit-site flag × carried treasure-trait assets | Location (deposit site) | None — self-loop; transfer + accounting happen in UPDATE | affordance | dynamic | existing | episode (self-loop) | many |
| Incremental / cycle moves | `project_sandbox_incremental_game_moves` (+ UPDATE handler, tick observer) (`mechanics/sandbox/incremental.py`) | Hosted `HasGame[IncrementalGame]` under sandbox scope | Location (host discovered via scope) | None — self-loop per move; requirement = host READY, non-terminal | affordance (host offers moves through the location) | dynamic | existing | episode (self-loop) | many |
| Story-info / `InfoAffordance` — **ADJACENT, not a convergence candidate** | `service_info_dispatch` (`service/dispatch.py`) + `mechanics/sandbox/story_info.py`; routed via `/story/info` | Info channels advertised per envelope | Current cursor / ledger | n/a — query channel (kind + opaque query), no graph edge | affordance-like disclosure surface | dynamic | existing | concept (`ProjectedState` sections; never traversed) | many |

**Part 2 — lifecycle, ownership, and drift** (same rows)

| Mechanism | Admission/binding predicates (projection-time) | Live availability predicates (use-time) | Projection target | Cleanup owner | Existing tags / hints | Current duplication / drift | Suggested convergence path |
|---|---|---|---|---|---|---|---|
| `Action` destination dependency | None — durable authored edge; resolution is triggered by selection | Viability preview drives `available` + blockers (`missing_successor`, `missing_dependency`, guard) | The authored `Action` itself (availability annotation, not a new edge) | n/a — durable; satisfied in place, never regenerated | No tags; the `Dependency` is labeled `destination` | Choice predates the open-link model: `Action ≅ Dependency[TraversableNode]` with a bolted-on preview path | None now; the clean model is documented above |
| Menu fanout | Fanout requirement match at resolve; `auto_provision`; not `frozen_shape` | None added (standard `Action` availability) | Ordinary `Action` per bound provider | `_clear_dynamic_menu_actions` — menu `edges_out` + `{dynamic, fanout, menu}`; intermediate `Affordance`s cleared per-fanout via `fanout:<uid>` tag | Tags only `{dynamic, fanout, menu}`; no `ui_hints` provenance | Only consumer of real `Fanout` machinery; provenance-poor next to sandbox | Reference path; extend minimal attribution post-table (synthesis item D) |
| Sandbox location exits / movement | Link authored; target ref resolves; no manual duplicate edge; `auto_provision`; not frozen | `sandbox_fixture_open(through)` for through-exits | Ordinary movement `Action`; message exits as self-loops | `_clear_dynamic_sandbox_actions(action_kind="movement")` — location `edges_out` + `{dynamic, sandbox, movement}` | Tags `{dynamic, sandbox, movement}`; rich hints via `_sandbox_contribution_hints` (source=`sandbox_link`, contribution, scope, source_label, source_kind, direction, raw_direction, target, through) | The doc's convergence candidate, yet does **not** wear `fanout`; lifecycle provenance rides in `ui_hints` (a presentation channel) | Shared interaction-donor surface when touched; protect IF direction labels (projection difference) |
| Sandbox sponsored interactions (location / fixture / asset / mob) | Sponsor in scope and visible (darkness suppressions via projection state); target resolves; `once` ⇒ target not yet visited | `interaction.availability` predicates on the edge | Ordinary `Action`; `trigger_phase` from activation; `return_phase=PLANNING` when `return_to_location` | Per-kind `_clear_dynamic_sandbox_actions` (`location` / `fixture` / `asset` / `mob`) | `{dynamic, sandbox, interaction, interaction:<label>, <kind>}` + six-field hints (source, contribution, scope, source_label, source_kind, interaction) + target, possession, … | Parallel `source="sandbox_*"` vocabulary; no `Affordance`/`Fanout` use | Primary candidate for the single interaction-donating provider protocol |
| Sandbox built-in verbs (take/drop, open/close, switch, lock/unlock) | Facet/trait gates (portable, switchable, container, lockable, openable) + visibility/holder state | Helper predicates (`sandbox_fixture_can_unlock`, `sandbox_mob_can_receive_asset`, `sandbox_asset_container_can_receive`, …) | Self-loop `Action`s; mutation via effect exprs (`sandbox_take_asset`, `_s.unlock_fixture`, …) + `journal_text` | Per-kind `_clear_dynamic_sandbox_actions` (`asset`, `unlock`, `lock`, `fixture`, `mob`) | `{dynamic, sandbox, <kind>, <verb>…}` + full hints (verb, asset, target, key) | Two vocabularies in one module: sponsored interactions route through `_project_sandbox_interaction`, verbs hand-roll `Action(...)` | Characterize against `SandboxInteraction`; keep lowering into traits/facets; sandbox vocabulary stays out of VM/Core |
| Sandbox scheduled events | `event.matches(world_time, location, actors_present)` — the schedule gate **is** the projection-time binding predicate (see "Availability is after binding"); sponsor visibility gates the gather | Interaction availability from `as_interaction` (usually none) | Ordinary `Action` via `_project_sandbox_interaction` (contribution `event`) | `_clear_dynamic_sandbox_actions(action_kind="event")` | `{dynamic, sandbox, interaction, interaction:<label>, event}` + sponsor hints + event label | Provider surface split: `get_sandbox_events` has no interaction peer; discovery + gating + projection bundled | The doc's named near-term consolidation; split activation from projection in docs/tests first |
| Sandbox wait / time | `_nearest_wait_enabled` (location overrides scope); `auto_provision`; not frozen | None | One self-loop `Action`; `sandbox_time_cost` payload | `_clear_dynamic_sandbox_actions(action_kind="wait")` | `{dynamic, sandbox, wait}` + hints (source=`sandbox_wait`, source_kind=`scope`) | None beyond being one of the nine parallel clear callers | Fold into shared donor surface when touched |
| Game self-loop moves | `game.phase == READY` (inline setup during PLANNING); non-terminal for post-UPDATE re-projection | None | Self-loop `Action` per move; payload `{"move": …}`; typed `accepts` | `_clear_dynamic_game_actions` — cursor `edges_out` (`trigger_phase=None`) + `{dynamic, fanout, game}` | Tags only `{dynamic, fanout, game}`; **no** `ui_hints` | **Recorded, not fixed:** wears `fanout` without touching `Resolver.resolve_fanout` — the tag vocabulary lies; provenance-poor | Keep as self-fanout; minimal attribution post-table; do not route through provision fanout |
| Adventure movement hazards | Hazard rule applies (`carried_asset` gate); only matching-direction movement actions rewritten | None (hazard fires on selection) | Self-loop that presents as **attempted movement** (protected projection difference) | `_clear_adventure_actions` — `{dynamic, sandbox, adventure}`, a world-owned fourth discriminator family. **Overlap:** hazard tags also contain `{dynamic, sandbox, movement}`, so the engine movement clear matches too — benign only because both projectors re-run each PLANNING pass in priority order | `{dynamic, sandbox, adventure, movement, hazard}`; inherits movement hints + source_kind=`world_authority`, contribution=`movement_hazard`, `hazard_outcome` | The one live counter-example to exactly-one-family ownership: overlapping cleanup claims, unguarded by contract | Classify as movement overlay; world-local until a second world needs movement blockers/diverters |
| Adventure magic words | `requires_discovery` ⇒ word known (scope locals) | None | Command-like `Action` ("Say XYZZY") to the target location | `_clear_adventure_actions` (`{dynamic, sandbox, adventure}`) | `{dynamic, sandbox, adventure, magic_word}` + world-authority hints + word | World-rolled action builder (intentional world authority) | Latent command affordance; revisit when parser affordance bands need the same shape |
| Adventure treasure deposit / scoring | Deposit site ∧ treasure held ∧ not yet deposited | None | Self-loop deposit `Action`; UPDATE applies asset transfer + score in scope locals | `_clear_adventure_actions` (`{dynamic, sandbox, adventure}`) | `{dynamic, sandbox, adventure, deposit_treasure}` + world-authority hints + asset | Transaction + accounting bundled in world code (deliberate demo policy) | Leave as demo policy; data-drive "transfer ⇒ accounting effect" only if repeated |
| Incremental / cycle moves | Hosted game discovered via scope; READY ∧ non-terminal | None | Self-loop `Action` per move; zero-duration allocation vs end-cycle time cost; cycles resolve via tick observer | Own `_clear_incremental_actions` — `{dynamic, sandbox, incremental}` (a tenth sandbox-side kind with its own helper) | Tags + hand-built hints (source=`sandbox_incremental_game`, contribution=`resource_allocation`, source_label, source_kind=`game`, move, target) — bypasses `_sandbox_contribution_hints`, so no `scope` field | Fourth copy of the clear-helper stanza; near-duplicate hint vocabulary | Fold into per-kind clear + shared hints helper when touched |
| Story-info / `InfoAffordance` — **ADJACENT** | Handler registration; channels advertised per envelope | Advisory `InfoState` availability/dirty kinds (client cache hints, not authority) | `InfoAffordance` list + `ProjectedState` sections via `/story/info` | n/a — recomputed per request; no graph residue | Typed DTO fields (kind, label, shortcuts), not edge tags | None — deliberately separate surface: info disclosure authority ≠ choice mutation authority | **None** — adjacent projection surface, explicitly not a convergence candidate |

#### Cleanup ownership is a compound key (and where it bends)

Every projector family removes its own stale actions by the same convention:
scope to the source node's `edges_out`, then match a discriminator tag set.
The discriminators in play:

- `{dynamic, fanout, menu}` — `story/system_handlers.py`
- `{dynamic, fanout, game}` — `mechanics/games/handlers.py`
- `{dynamic, sandbox, <action_kind>}` — `mechanics/sandbox/handlers.py`, nine
  per-kind callers: `movement`, `asset`, `unlock`, `lock`, `fixture`, `mob`,
  `location`, `wait`, `event`
- `{dynamic, sandbox, incremental}` — `mechanics/sandbox/incremental.py`, own
  helper
- `{dynamic, sandbox, adventure}` — world-owned
  (`adventure_sandbox_slice/domain.py`), own helper; its hazard actions
  additionally wear `movement` and so match two families (see the hazard row)

The families intentionally share tags (every discriminator contains `dynamic`;
menu and game also share `fanout`), so the safety property is **not** set
disjointness — it is **mutual non-subsumption**: no family's discriminator is a
subset of another's, so no family's cleanup sweep automatically claims another
family's actions. Non-subsumed by construction, unguarded by contract — except
where noted. The pairwise non-subsumption of the engine-owned discriminators,
and the exactly-one-family property of generated actions (observed for every
engine-owned family), are pinned by an invariant test in
`engine/tests/mechanics/test_sandbox_architecture.py`; the table rows above are
the classification it executes.

#### Lifecycle metadata vs presentation hints in `ui_hints` (synthesis item D)

The "Existing tags / hints" column shows the sandbox families carry a rich field
set inside `ui_hints`. Those fields are not all the same *kind* of thing.
Classifying them against "who generated this edge / who owns its cleanup?"
(**lifecycle**) vs "how should a renderer display it?" (**presentation**):

| `ui_hints` field | Emitted by | Classification |
|---|---|---|
| `source` (`sandbox_fixture`, `sandbox_link`, …) | base (`_sandbox_contribution_hints`) | **Lifecycle** — names the projecting family; the cleanup-owner answer |
| `scope` | base | **Lifecycle** — which scope sponsors/owns the edge |
| `source_label` (`altar`, `guide`, …) | base (optional) | **Lifecycle** — which concept instance generated it (a renderer *may* echo it) |
| `interaction` / `verb` / `asset` / `key` / `target` / `through` / `mob` / `fixture` / `move` / `word` / `hazard_outcome` / `possession` | per-call extras | **Lifecycle** — identifies the source coordinate this edge was projected from |
| `contribution` (`movement`, `event`, `resource_allocation`, …) | base | **Conflated** — reads as the projection reason (lifecycle) yet Reviewer 3 marks it advisory display |
| `source_kind` (`fixture`, `mob`, `scope`, `world_authority`, …) | base (optional) | **Conflated** — advisory display per Reviewer 3, yet also encodes the sponsor's lifecycle kind |
| `direction` / `raw_direction` | link extras | **Presentation** — IF compass labels; a protected projection difference, display-only |

**The core tension:** the unambiguously-lifecycle fields `source` and `scope`
ride inside `ui_hints`, whose model docstring (`UIHints`,
`journal/intent.py`) declares it *"Advisory renderer hints for choices"* — a
**presentation channel**. Cleanup ownership is lifecycle and should not hide in a
presentation channel. Menu and game projectors, by contrast, historically
carried *no* `ui_hints` at all; their only attribution was the discriminator tag
set (the compound-key cleanup contract above).

**Minimal pass (item D, this iteration):** rather than build the proper
separation, the menu and game projectors gain the single unambiguously-lifecycle
token — `source` — in the **same `ui_hints` channel** sandbox already uses, so
all three families are equally cleanup-explainable
(`{"source": "menu_fanout"}`, `{"source": "game_self_loop"}`). One token,
additive, ignorable by existing consumers; tags are untouched, so the
compound-key contract and its exactly-one-family invariant are unaffected. The
characterization tests in `test_projection_characterization.py` pin the new
shape.

**Deferred convergence debt (do *not* build here):** proper separation would
thread a dedicated lifecycle/provenance channel through `Action` +
`ChoiceFragment` + the wire DTO, distinct from `UIHints`. That is the
"general provenance/receipt shape for phase outputs" promotion candidate already
named in `engine/src/tangl/mechanics/sandbox/SANDBOX_DESIGN.md`
("General Contribution Pattern"), gated on a second non-sandbox consumer — not
on this pass. The `source_kind` / `contribution` conflation and the game
`fanout`-tag drift are likewise *recorded, not fixed* here; each needs its own
approved migration that updates this table and the matching characterization
test together.

---

## Future Extensions (seams, not commitments)

- **Content / commentary affordances.** A provider-fixed open link whose bound
  endpoint contributes journal material without traversal (concept-binding).
- **Challenge-modifier affordances.** A provider that influences a dice/check;
  projection writes a modifier into the resolution context.
- **Inner-guide providers (Disco-style).** Omni-present, player-scoped concepts that
  attach as provider-fixed open links in the player's scope; handlers decide the
  contribution (journal fragments, choice pressure, challenge modifiers, forced
  interruptions). The shared namespace-provider gather (`_concept_providers`) is the
  natural home; today only scheduled events consume it.

---

## Naming note

First drafted as `AFFORDANCE_MODEL.md`. After the open-link correction,
"affordance" is only the provider-fixed *direction* of the primitive, so a name
like `OPEN_LINKS_AND_PLANNING.md` / `OPEN_EDGES_AND_PLANNING.md` /
`REQUIREMENT_EDGES.md` is more accurate. Filename retained for now to keep the
issue #255 / CodeRabbit references stable; rename is a pending decision.

---

## Done-state for this model

- The open requirement-bearing link is the planning primitive
  (`fixed endpoint + Requirement(open endpoint) + policy`); an open endpoint is the
  basic unit of work in the provisioner, not an illegal state to normalize away.
- `Dependency` and `Affordance` are one object with opposite fixed endpoints
  (addressed vs broadcast); duals at the matching surface but distinct in
  obligation/failure. `Fanout` is a cardinality/rule-generation mode, not a third form.
- The planning matrix (origin, direction, provider state, target kind, use state,
  cardinality, arbitration) gives every mechanism a coordinate.
- Provider state existing-vs-latent is the architectural hinge; bound links hold a
  reference or a provision plan; episode-latent enables choices to menu before their
  destination materializes.
- Projection = `function(link kind, bound endpoint kind, phase, predicates, context)`;
  concept-vs-episode is orthogonal to direction; affordance ≠ choice.
- Availability/suppression are use-time filters applied after binding and projection.
- Planning attaches cheap existing affordances first, satisfies dependencies, then
  ranks by scope distance / materialization cost / specificity / policy.
- Convergence is audit-first: classify mechanisms in the matrix before migrating
  code, then converge opportunistically; the sandbox provider surface is the
  near-term consolidation. The audit table is filled as of v2.2; cleanup
  discriminator non-subsumption and exactly-one-family ownership are pinned by
  an invariant test.
