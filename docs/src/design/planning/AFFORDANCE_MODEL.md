# Open Links: Requirement-Bearing Edges and the Planning Matrix

*(formerly "The Affordance Model" — affordance is one direction of the primitive
defined here, not the whole of it; see the naming note at the end.)*

**Document Version:** 2.1
**Status:** CANONICAL — defines the **open link** as StoryTangl's planning
primitive and frames `Dependency`, `Affordance`, and `Fanout` against it via a
feature matrix. Several domain layers (menu fanout, sandbox interactions,
scheduled events) are *coordinates* in this matrix; some have drifted into
bespoke vocabularies and are noted as convergence debt rather than separate
concepts. The `OpenLink` base object near the end is a **mental model, not an
immediate refactor** — do not build it yet.
**Relevant layers:** `tangl.core` (Selector/Edge), `tangl.vm.provision`,
`tangl.story.episode`, `tangl.mechanics.sandbox`

See also:
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
        if dep.bound_provider:
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
`REQUIREMENT_EDGES.md` is more accurate. Filename retained for now to keep issue
#255 / CodeRabbit references stable; rename is a pending decision.

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
  near-term consolidation.
