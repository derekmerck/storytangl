# Repertoire Loop Design

```{storytangl-topic}
:topics: games
:facets: design
:relation: documents
:related: token, singleton, assembly, transaction, credentials, widget
```

**Status:** L1 build-order step 1 landed: the pure fixed-list
``CallResponseGame`` proves role capability, directed matching, initiative,
structured evidence, and CLI output. L2 step 2a landed the world-independent
``PhraseType`` / ``PhraseBadge`` / ``RepertoireManager`` ownership foundation.
L2 step 2b1 landed the pure bounded dominance contribution fold; step 2b2
landed the accepted-entry repertoire snapshot proof. The acquisition shell
remains design work. Revised after review of PR #380: the
keyed prompt/answer model was replaced by a shared phrase catalog with a
directed dominance relation, and the proposed engine seam was withdrawn.
**Scope:** a call-response dominance kernel in `tangl.mechanics.games`, the
owner-bound repertoire that supplies its moves, and the acquisition shell
around both
**Prior art:** *Monkey Island* insult swordfighting; "one red paperclip" trade-up
arbitrage. In-package: `SiegeRpsGame` (initiative), `RpsGame` (directed
dominance), `AggregateForceGame` (bounded reserve as game state),
`worlds/colony_loop` (shell/spike snapshot and aftermath)
**Governing context:** `COMPOSITE_GAME_LOOPS_DESIGN.md` (shell + spikes),
`CREDENTIALS_LOOP_DESIGN.md` (world-tunable texture),
`MECHANICS_FAMILIES.md` (resolution grammars)

---

## Why This Note Exists

Insult swordfighting reads as a bespoke minigame. Pulled apart it is three
separable concerns plus one small kernel the package lacks. Building it as a
unit yields a mechanic that can only ever be repartee.

An earlier draft cut it wrong in one specific way, and the correction is the
most important thing in this note. That draft modeled prompts and responses as
two disjoint card classes matched on a shared key. That is a quiz. What the
interaction actually wants is **one catalog of phrases, each usable as call or
response depending on initiative, related to other phrases by a directed
dominance graph**. The difference is not cosmetic — it is what makes catalog
extension monotonic and the Sword Master structural rather than special-cased.

---

## The Cut

```text
L3  world veneer        catalog content, text, tone, stakes      (authoring)
L2  acquisition shell   how repertoire grows and prizes trade    (mechanics)
L1  call-response       how one exchange resolves                (kernel)
────────────────────────────────────────────────────────────────
P   presentation        CLI floor -> richer media                (orthogonal)
```

L1 and L2 are orthogonal. A contest is playable against a fixed phrase set with
no economy; an acquisition economy works with any spike. They meet through the
ordinary accepted-entry UPDATE preparation / aftermath-writeback boundary that
`worlds/colony_loop` already demonstrates — **not** through new protocols. Only
a world composes them, the way credentials composes inspection, evidence,
mediation, and disposition into one encounter.

Presentation is not a layer in this stack. It is an axis every layer projects
onto, and the CLI floor is where correctness is decided.

---

## L1 · The call-response dominance kernel

### The exchange

```text
leader deploys phrase A as call
responder deploys phrase B as response
catalog relation resolves B against A
score and initiative change
both actually-deployed phrases become exposure records
```

This is not "look up the correct answer." It is a small catalog-driven sibling
of RPS: RPS supplies directed dominance, `SiegeRpsGame` supplies asymmetric
initiative, the repertoire supplies actor-specific move availability, and the
catalog supplies an extensible many-to-many dominance graph. It earns its own
kernel because RPS assumes simultaneous moves from a fixed universal set, while
this is ordered, role-sensitive, and repertoire-bound.

### One catalog, role capability, and the definition/badge split

A phrase is a move. Whether it acts as call or response depends on initiative
and its declared roles — not on membership in a permanent "prompt" or "answer"
class. A phrase learned as a response can later be deployed as a call.

The persistence shape is the existing token pattern, exactly as wearables use
it (`Wearable = Token._create_wrapper_cls(WearableType, "Wearable")`):

```text
PhraseType(Singleton)          immutable catalog truth: text, roles, tags, relations
PhraseBadge = Token[PhraseType]  graph-owned earned instance, delegates + overrides
RepertoireManager(ComponentManager[PhraseBadge])   owner-bound collection
```

`Token` gives exactly the semantics wanted: reads delegate to the frozen
singleton, while fields marked `json_schema_extra={"instance_var": True}`
materialize as mutable token-local fields. So relation declarations live on the
catalog definition by default — every earned badge stays synchronized and no
badge copies a large relation table — while a specific badge can carry a local
override. A badge minted as "beats rock" can later gain "and scissors" as state
unique to that instance.

`RepertoireManager` is a `ComponentManager`, not a bare `SlottedContainer`:
persistent, UUID-assigned, rebound through the owner's registry, matching
`OutfitManager`, `WardrobeManager`, `CredentialPacketManager`, and
`VehicleLoadout`. One large `known_phrases` slot.

The mechanic exposes ordinary `ComponentManager` ownership changes, so badges can
be transferred, wagered, or confiscated by explicit transaction. The **reference
world** layers an award-only facade over that: awards are idempotent, duplicates
are disallowed, and its play never removes a badge. That is a world policy, not a
property of the mechanic — see "Mechanic capability versus demo policy" below.

### The dominance relation

Relationships may be declared from either end, over ids or tags, positively or
negatively:

```yaml
id: dairy_farmer
text: "You fight like a dairy farmer!"
roles: [call, response]
tags: [rustic, competence_attack]

as_call:
  accepts_responses: { tags: [rustic_reversal] }
  rejects_responses: { tags: [generic_denial] }
as_response:
  counters_calls: { tags: [farm_insult] }
  fails_against:  { ids: [sword_master_refinement] }
```

Four declaration sites fold into **two relations over ordered (call, response)
pairs** — positive and negative. Criteria are ordinary `Selector`s; `has_tags`,
`is_instance`, and attribute comparisons already work, so this introduces no new
predicate language.

### The composed dominance schedule

The catalog index is a **base layer, not final authority**. The authoritative
artifact for one contest is a settled schedule composed at the boundary:

```text
base catalog relations
+ imported catalog extensions
+ world rules
+ scenario rules
+ badge-local contributions
────────────────────────────────
concrete DominanceSchedule
        ↓ accepted-entry UPDATE snapshot
CallResponseGame
```

A contribution is uniform regardless of source:

```yaml
call_selector:     { has_tags: [insult] }
response_selector: { has_identifier: beaujolais }
result: match
layer: LOCAL
source_id: beaujolais
```

One shape covers phrase-definition relations, imported catalog extensions,
scenario-wide rule changes, a badge-local mutation, a debugging token that beats
everything, and an environmental modifier that disables a phrase family. A world
can import a base catalog and compose a new schedule over it without editing the
original.

This resolves what looked like a contradiction between a precompiled index and
mutable badges: the index is an optimization of the base layer, and per-contest
truth is the composed snapshot.

**Composition is the existing contribution idiom, not new machinery.** Gathering
layered contributions and folding them into a settled artifact is what
`chain_execute_all` over `BehaviorRegistry` does, and `contribute_ns`,
`contribute_roles`, `contribute_settings`, and
`contribute_sandbox_inventory_helpers` are all instances of the pattern. A
`prepare_game(ctx)` contribution at accepted-entry UPDATE is one more.

**Scope the schedule to the participating badges.** Compose over the player's
snapshot × the opponent's snapshot, not the whole catalog. A cross-product over
a 200-phrase catalog is 40,000 entries; over two eight-badge repertoires it is
sixty-four. So the game holds something genuinely small:

```python
dominance: dict[tuple[PhraseId, PhraseId], MatchResult]
```

Two ordered accepted-entry UPDATE steps: snapshot participating badge ids, then
compose the schedule over just those pairs.

**`MatchResult` carries its contributing `source_id`.** Cheap, and it makes both
diagnostics and narration able to say *why* — "matched by: beaujolais" — rather
than only *whether*.

**The settled snapshot is what makes replay exact.** The engine is
event-sourced, and a playthrough must be reproducible from a snapshot plus the
choice log. If dominance were resolved by inspecting live world state during
each round, replay would depend on world state at every step. Composing once at
Accepted-entry preparation pins it for the whole contest, so the exchange replays deterministically
no matter what the world does afterward. This is the strongest argument for the
boundary — stronger than handler purity. The schedule is persisted as game state
so that replay does not depend on recomposing it; see below.

**And it is projectable.** A sixty-four-entry matrix scoped to this contest is
something `story_info` can actually render: what you hold, what it answers, what
answered you. Monkey Island players kept notes on paper. Making the schedule an
inspectable artifact is what turns an opaque quiz into a legible puzzle, and it
costs nothing extra because the snapshot already exists.

### The schedule is persisted as game state, not cached

The composed schedule is written onto `CallResponseGame` during accepted-entry UPDATE and lives
there for the contest:

```text
accepted-entry UPDATE preparation:
  snapshot participating badge ids
  gather and fold contributions
  persist concrete DominanceSchedule on CallResponseGame
  optionally record schedule_hash + composer version for diagnostics

resolution:
  pure handler reads the persisted schedule
```

This needs no new machinery. `Game` is an `Entity`, so it is ordinary graph
state on the constructor-form persistence path, and `Ledger` already snapshots
and checkpoints (`checkpoint_cadence`, `save_snapshot`, `make_checkpoint`).
`AggregateForceGame.player_opening_reserve` is the same move already made —
a snapshot persisted as game state.

**A hash alone is not enough, and this is the deciding argument.** A stored hash
*detects* that recomposition diverged; it cannot *reproduce* the original
contest. If a world updates its catalog, imports a revised base, or the composer
changes between sessions, every saved contest becomes flagged-but-unreplayable.
Persisting the concrete schedule means the exchange replays exactly regardless of
later drift.

It is also the smaller design. An external cache needs a lifecycle — keying,
invalidation, eviction — that nothing else in the contest requires, and the pure
handler gains a dependency it otherwise does not have. Caching can wait until
measurements justify it.

The obvious objection is serialization cost, and it does not bite: the schedule
is written once during accepted-entry UPDATE preparation and never mutated, so it is diff-stable across
checkpoints, and a contest-scoped schedule is tens of entries rather than a
catalog cross-product.

Note this does **not** mean writing a schedule into the journal per exchange.
That would duplicate a largely static artifact many times over. Persisting it
once as game state is a different and much smaller thing.

**The hash survives as a diagnostic.** Recording `schedule_hash` plus
`tangl.info.__version__` (already surfaced through `SystemInfo`) still tells you
that a world's rules drifted since a contest was played, and separates "the
engine changed" from "composition is nondeterministic." It is simply no longer
the reproduction mechanism.

`HasContent` is the primitive if that hash is wanted: a
`DominanceSchedule(HasContent)` implements `get_hashable_content()` and inherits
`content_hash()`. **Hash the composed output, not the contribution inputs.** #307
establishes that durable hashing needs canonical stable serialization, because
`set` and `frozenset` do not serialize deterministically across
`PYTHONHASHSEED` — and contributions are exactly that shape, since their
selectors carry `has_tags` and tags are sets. The composed schedule is a flat
mapping from ordered `(call_id, response_id)` pairs to an outcome and a source
id; hashing it in sorted key order is deterministic by construction. Since the
hash is diagnostic rather than load-bearing, this is a convenience rather than a
dependency either way.

### Resolution rules

1. **Default is miss.** An undeclared pairing fails. Matches must be positively
   declared. Without this, coverage analysis is meaningless and unrelated tags
   accidentally succeed.

2. **Layer ordering is `DispatchLayer`, not a new rank enum.** The contribution
   sources above already map onto the existing cascade — GLOBAL, SYSTEM,
   APPLICATION, AUTHOR, USER, LOCAL — whose own comment explains that "local
   sorts _later_ in execution priority so it can observe and aggregate globals."
   A badge-local contribution therefore outranks its catalog declaration for the
   documented structural reason, not as a special case, and `Priority` orders
   within a layer. At equal layer and priority, negative beats positive.

   Whether that is ultimately enough is open. `offer_sort_key()` in
   `vm/provision/matching.py` resolves competing provisioning offers with a
   deterministic tuple blending declared tiers, computed distance
   (`scope_distance`, `distance_from_caller`), and a `score_selector_specificity`
   its own docstring calls "CSS-like." If declared layers prove too blunt, that
   is the shape to copy. Start with layers and deterministic negative precedence;
   let a real catalog say whether more is warranted.

3. **Equal-layer contradiction is diagnosed, then deterministically resolved.**
   Declaring from both ends is what makes the catalog extensible; it is also what
   makes contradiction possible. Both halves matter: the conflict is reported so
   an author can see it, *and* negative precedence settles it so the contest has
   executable semantics. Diagnosing without resolving would leave the kernel
   without an answer at runtime.

### Three failure modes, only one of which is a miss

Composition and resolution must distinguish these. Collapsing them weakens a
real invariant:

```text
valid phrase, no declared relation  → miss
phrase unknown to this world catalog → unavailable or miss, by explicit policy
missing token or Singleton referent  → integrity error; fail loudly
```

`Token` construction requires its referent to exist, and `ComponentManager`
raises `KeyError("Component ... is not available through the owner registry")`
when an assignment cannot be resolved. Those invariants stay. Arbitrary code can
always violate them, but that is not a reason to weaken them, and a valid
extension API should preserve catalog and reference integrity.

The schedule boundary makes this easier rather than harder: a dynamically added
token with no matching contribution simply produces no schedule entries and
misses, while a broken reference fails at snapshot time — before the contest
starts, not mid-exchange.

### Diagnostics are an authoring aid, not a gate

A tag-derived many-to-many relation is a rule system, and two authors adding
tags independently will produce matches neither intended. A catalog-load pass
should report unwinnable calls, dead-weight badges, and ambiguous pairs.

But **preflight cannot be authoritative**, and the design must not lean on it.
Worlds legitimately inject tokens and contribute rules after load. Composition
is where correctness actually lands, and the composed schedule is the thing
worth inspecting — which, being contest-scoped and small, it can be. Load-time
diagnostics stay useful in the spirit of #286 / #205, without pretending to be a
guarantee.

### Initiative, and the no-legal-move floor

Initiative follows the siege convention exactly: state on the `Game` subclass,
set in `on_setup`, flipped in `resolve_round`, recorded through
`build_round_notes`, presented through `get_move_label` ("Attack with" /
"Answer with"). **Not** a new field on `RoundRecord`.

Role capability plus alternating initiative admits a deadlock: a repertoire of
only response-capable badges cannot lead. The floor is a **catalog item, not a
kernel special case** — a starter phrase that is always available and reliably
loses. That is also the honest starting state: you begin with a couple of losers.

### The opponent's repertoire is the difficulty knob

An opponent is authored as a badge set, not as a strategy parameter.
`AggregateForceGame.opponent_opening_reserve` already precedents opponent state
as a bounded snapshot on the game, and `opponent_strategies` is a named registry
whose functions receive the game, so "which of my badges answers this call"
plugs straight in.

This makes teaching structural: **an opponent can only teach what it holds.** No
separate teaching table, and no risk of an opponent granting a phrase it never
demonstrated.

---

## Why there is no engine seam

An earlier draft claimed `get_provisioned_moves(game)` needed to accept `ctx`,
because playable phrases live on an assembly attached to the actor rather than
on the game. That was wrong, and withdrawing it is the better result.

`GameHandler` is a stateless, graph-independent rules engine, and move legality
is kernel logic. The shell/spike boundary already answers this:

```text
actor repertoire
  → world ``prepare_game(ctx)`` snapshots playable badge ids
    → CallResponseGame holds that bounded set
      → pure GameHandler provisions moves from it
```

`worlds/colony_loop` demonstrates the complete pattern, both directions:
`ColonyContestBlock.prepare_game()` writes
`caller.game.player_opening_reserve` immediately before setup; the aftermath blocks
read the contest game, write back to the shell, and guard re-entry with
`caller.locals["aftermath_applied"]`. Bounded-set-as-game-state is likewise the
family idiom, not a workaround — see `AggregateForceGame.player_reserve`.

`provision_presentation(game, *, ctx)` is not precedent for widening. It is
deliberately an integration hook; move legality is not.

No new phase, fragment type, graph primitive, or protocol.

---

## L2 · The acquisition shell

### Two reward channels, separated by catalog type

An earlier draft collapsed these, saying the player learns a badge by losing and
then spends it.

The two channels are **different catalogs distinguished by type**, not two roles
within one catalog:

- **Competence** — phrase badges. Granted by *exposure*: any phrase actually
  deployed against you may become yours, per world policy.
- **Prizes** — their own catalog of spendable, tradable tokens. Granted by
  *winning*. These participate in the trading and unlock shell through
  `tangl.mechanics.transaction`, whose design doc already enumerates Held Token
  and Catalog Provision source modes.

A phrase is one kind of badge-like token; a prize can be anything — a token from
another catalog, a variable flag, a newly minted concept. Modeling prizes as
spendable tokens with their own catalog is the simplest first cut for the
reference world. It is a good default, not a prohibition on phrase badges ever
being wagers or trade goods.

```text
lose → learn something
learned phrase → enables a better challenge
win → receive a unique prize
prize → unlock or trade for another opportunity
```

Grind losses, not wins.

### Mechanic capability versus demo policy

These are separate statements and the note keeps them apart:

```text
mechanic capability:
    badge ownership may change through explicit transactions

reference-world policy:
    learned phrases are awarded idempotently and retained permanently
```

`RepertoireManager` stays a full owner-bound `ComponentManager`, and transactions
can move its contents. The reference repartee world exposes an **award-only
facade** over it and never removes a badge — but that is the demo's policy, not a
limitation of the mechanic. Persistent graph identity and permanent retention are
different questions, and a badge with stable identity can equally be retained,
exhausted, consumed on use, stolen, wagered, transferred, confiscated, or
upgraded with further relation contributions.

### The reward policy is a hookable shell-level handler

Acquisition is **not** kernel behavior. It belongs to the plot/shell layer as an
ordinary dispatch-registered aftermath handler, and it is expected to change
without touching the contest flow.

The reference implementation should be the cheapest thing that works — most
likely "award the phrase that beat you," idempotently. What matters is that
swapping the policy never reaches into the kernel. Forgetting on a win, tiered
learning on a loss, theft, and consumption are all expressible as aftermath
policies using explicit transactions; none of them are demo behavior, and none of
them should be structurally excluded.

Their only real requirement is on the evidence: the round record has to be rich
enough that a policy nobody has written yet can still be computed from it. That
is the practical argument for the field set below — deliberately richer than the
reference policy needs.

### Exposure is recorded, never inferred

The round record identifies what was actually said:

```text
call_phrase_id
response_phrase_id
matched
match_source_id            # which contribution decided it
additional_exposed_phrase_ids
initiative_before
initiative_after
```

There is deliberately no "correct response" field. In a many-to-many dominance
graph several responses may answer a call and none is canonical; that phrasing
was residue from the discarded quiz model.

`RoundRecord.notes` carries this; JOURNAL renders it; the shell-level aftermath
handler applies progression idempotently, guarded the way
`apply_colony_victory_aftermath` guards with `caller.locals`.

Two things this rules out, both deliberately:

- **Do not infer exposure from win/loss.** An outcome-keyed record cannot
  express red-paperclip acquisition at all, since the whole point is that losing
  teaches. This is a schema commitment, not an interface style — it survives the
  decision below to defer protocols.
- **Do not derive progression by rereading rendered journal prose.** A phrase the
  engine knew about but nobody spoke must not become learned. Disclosure stays
  honest when acquisition reads structured evidence of what was actually said.

### No protocols yet

For the first slice, existing structures suffice: a bounded id list on the game,
and exposure in `RoundRecord.notes`. A fixed-list kernel test and a world
snapshot writing into the same list do not yet justify a `MoveSource` type, and
an aftermath handler consuming round notes does not justify a yield-sink type.
Extract protocols when a second implementation genuinely appears.

Parsimony here governs new *types*. The record's field set is the design
commitment and stays.

---

## L3 · World veneer

Repartee is one skin: a phrase catalog, a tone, opponents with their own
repertoires, and stakes. Like credentials, the whole texture is world-tunable,
and phrase catalogs are world-scoped, matching credentials' world-local catalog
isolation.

### Why the Sword Master works structurally

She does not override anything. Her catalog adds new **call** phrases whose
relation declarations point at response badges the player already holds:

```yaml
id: sword_master_oblique_insult
text: "I hope you have a boat ready for a quick escape."
roles: [call]
as_call:
  accepts_responses: { ids: [fights_like_cow] }
```

The player has never heard that call. The old badge applies anyway, because the
new catalog item declares the relationship. Nothing is patched at runtime, and a
learned badge never needs to know every future call that may recognize it.

*Base-catalog declarations* extend monotonically in both directions: a later
expansion can add a response effective against old calls, or a call answered by
old responses, without editing the existing catalog.

The composed schedule is deliberately **not** monotonic. Higher layers exist
precisely so a world or scenario can negate or override a relationship the base
catalog declares — that is what makes `beaujolais`, and disabling a phrase
family, expressible at all. Monotonicity is a property of additive catalog
authoring, not of composition.

### "Better" is not a number

A phrase may be better because it counters more call tags, works in both roles,
defeats a strategically common family, exposes one opponent's narrow
vulnerability, or is recognized as evidence of training. A weak phrase stays
useful as bait — play it as a call expecting the opponent to reveal a valuable
counter. Losing becomes exploration rather than failure, which only works if
losing is cheap; stakes are a world-tuning axis.

### #336 is an enhancement, not a blocker

Direct catalog-authored text is sufficient for the first world, and the Sword
Master needs only new phrase records, not scoped overrides. Named scoped
expressions become valuable for opponent-specific revoicing, alternate tone,
localization, and broader prose composition.

---

## P · Presentation axis

Credentials is the model: demonstrably complete in the CLI, intended to carry a
richer representation, with the CLI never a degraded fallback. Here the floor is
genuinely sufficient — the call line, a numbered list of deployable badges, the
score and initiative line.

| Surface | State |
|---|---|
| `AttributedFragment(who, how, media)` for exchange lines | shipped |
| `PieceFragment` for held badges | shipped engine-side; `PieceFragmentView.vue` renders a list |
| `zone` grouping for repertoire vs deployed | shipped; `ZoneFragmentView.vue` present |
| `PieceFragment.position` + `ZoneLayoutHints` geometry | specified §7.1/7.2, **not consumed** by the Vue views |
| `StagingHints.media_timing` | shipped in the engine, **never read** by `MediaFragmentView.vue` |
| Portrait/background generation | forges exist (comfy, stable, svg, tts, dicebear, composition) |
| Bundled art | none — zero raster assets in `worlds/` |

Whether the richer representation works yet is an open empirical question, and
it is deliberately off the critical path.

---

## Build order

1. **Landed:** Pure `CallResponseGame` over a fixed phrase set and a
   hand-written schedule: role capability, directed matching, initiative,
   structured round notes, ordinary CLI journal output.
2. **2a landed:** `PhraseType` / `PhraseBadge` / owner-bound
   `RepertoireManager` establish catalog truth and transferable badge
   ownership. **2b1 landed:** the pure composer folds bounded participants and
   layered `DominanceContribution` declarations into `DominanceMatch` values.
   **2b2 landed:** world-owned `prepare_game(ctx)` snapshots participating
   badge ids and invokes that composer for the accepted contest.
3. Shell-level aftermath handler reads exposure records and idempotently awards
   badges; the policy is swappable without touching steps 1-2.
4. Winning grants a prize token from its own catalog, or a durable world
   consequence.
5. Opponents and locations gate on repertoire and prize holdings.
6. Sword Master analogue: unfamiliar calls onto already-earned badges.
7. Richer expressions and presentation, only after the CLI vertical is complete.

Steps 1 and 2 must be independently testable — that is the check that L1 and L2
are really orthogonal.

### Two seam tests, built now

The reference world exercises only immutable catalog relations, retained player
badges, fixed opponent repertoires, award-on-loss, and prize-on-win. Two small
conformance tests keep the obvious variants from being boxed out without
building any of them:

- **Contribution override.** A world-local `beaujolais` contribution at
  `DispatchLayer.LOCAL` overrides an imported base schedule and answers every
  call tagged `insult`.
- **Ownership transfer.** A transaction moves a phrase badge between
  repertoires, and the next contest's snapshot reflects the new owner.

Neither is demo behavior. They exist to prove the seam is real.

## Open questions

1. **Is layer ordering enough?** `DispatchLayer` plus deterministic negative
   precedence is the first cut. Whether contradictions ultimately want
   closest/most-likely resolution — rules acting as distance measures, in the
   shape of `offer_sort_key()` — should be decided by a real catalog rather than
   in advance. Not worth holding anything for.
2. **Does an aftermath grant every witnessed phrase, or only the one that beat
   you?** A world policy, not a kernel decision. The reference world should pick
   the cheapest thing that works.

Deferred as potential second consumers rather than open design: sequence prompts
(Simon-says), and partial or near-miss scoring. Binary semantic matching is
enough for the proof, and both may justify a sibling or a generalization later.

---

## Non-goals

- A general dialogue or conversation system. This is a contest kernel that reads
  as dialogue.
- Multi-cursor or two-human play. That is #346, a runtime expansion.
- Hidden information. `visibility` does not exist on fragments today, and this
  loop does not need it.
- Treating credentials as an instance of this kernel. Credentials has
  inspection, evidence, mediation, rule evaluation, and disposition; it is not a
  prompt-to-response exchange. The real kinship is that both separate semantic
  state from presentation and compose catalogs, assemblies, transactions, and
  journal projection.
- Solving presentation. The CLI floor is the deliverable.
