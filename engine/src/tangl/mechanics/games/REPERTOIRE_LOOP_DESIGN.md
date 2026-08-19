# Repertoire Loop Design

```{storytangl-topic}
:topics: games
:facets: design
:relation: documents
:related: token, singleton, assembly, transaction, credentials, widget
```

**Status:** DESIGN — nothing landed. Revised after review of PR #380: the
keyed prompt/answer model was replaced by a shared phrase catalog with a
directed dominance relation, and the proposed engine seam was withdrawn.
**Scope:** a call-response dominance kernel in `tangl.mechanics.games`, the
add-only repertoire that supplies its moves, and the acquisition shell around
both
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
ordinary PREREQS-snapshot / aftermath-writeback boundary that
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
RepertoireManager(ComponentManager[PhraseBadge])   owner-bound, add-only
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

Its domain-facing API exposes **`award()` only**, even though `ComponentManager`
supports removal internally. Membership is durable, awards are idempotent,
duplicates are disallowed, and ordinary play never consumes a badge.

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
pairs** — positive and negative. Catalog load normalizes them into one directed
index so runtime resolution is a lookup.

Criteria are ordinary `Selector`s. `has_tags`, `is_instance`, and attribute
comparisons already work; this introduces no new predicate language.

### Resolution rules

Three rules, and they matter more than they look:

1. **Default is miss.** An undeclared pairing fails. Matches must be positively
   declared. Without this, coverage analysis is meaningless and unrelated tags
   accidentally succeed.

2. **Precedence is declared, for now.** Each declaration carries an explicit
   rank, and **a badge-local override outranks its catalog declaration** for the
   same reason `DispatchLayer.LOCAL` sorts last — the local layer exists to
   observe and override the global one. At equal rank, negative beats positive.

   This is a first-implementation choice, not a settled principle. The engine
   already has a richer model for exactly this problem, and it is the obvious
   thing to borrow if declared ranks prove too blunt: `offer_sort_key()` in
   `vm/provision/matching.py` resolves competing provisioning offers with a
   deterministic tuple blending declared tiers, computed distance
   (`scope_distance`, `distance_from_caller`), and a computed
   `score_selector_specificity` whose own docstring calls it "CSS-like."

   So the open question is whether dominance contradictions are best resolved by
   *rules* or by *closest / most-likely match with rules as distance measures*.
   Rules-only is fine to start. If the answer turns out to be distance, the shape
   to copy already exists.

3. **Equal-rank contradiction is surfaced, not silently resolved.** Declaring
   from both ends is what makes the catalog extensible; it is also what makes
   contradiction possible.

### Diagnostics are an authoring aid, not a gate

A tag-derived many-to-many relation is a rule system, and two authors adding
tags independently will produce matches neither intended. A catalog-load pass
should report:

- calls with zero valid responses in the world catalog (unwinnable)
- badges with zero coverage (dead weight)
- equal-rank contradictions (ambiguous)

But **preflight cannot be authoritative here**, and the design must not lean on
it. Nothing stops a world from programmatically injecting a badge that was never
in the catalog, or tombstoning a catalog member mid-story. Either can introduce
a fresh contradiction, or trivialize an existing resolution, after load has
already run.

Two consequences the runtime must actually honor:

- **Resolution tolerates unknown badges.** This is where *default is miss* earns
  its keep: an injected badge with no declared relations simply loses, which is
  the safe failure. Injection can never accidentally manufacture a win.
- **The relation index tolerates dangling references.** A tombstoned member
  degrades to "no declared relation" rather than raising.

So this is a diagnostic surface in the spirit of #286 / #205 — worth having, and
never a correctness guarantee.

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
  → world PREREQS handler snapshots playable badge ids
    → CallResponseGame holds that bounded set
      → pure GameHandler provisions moves from it
```

`worlds/colony_loop` demonstrates the complete pattern, both directions:
`prepare_colony_contest` runs `@on_prereqs(..., priority=Priority.FIRST)` and
writes `caller.game.player_opening_reserve` before setup; the aftermath blocks
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
then spends it. Badges are not spent.

The two channels are **different catalogs distinguished by type**, not two roles
within one catalog:

- **Competence** — phrase badges. Durable, normally non-consumable. Granted by
  *exposure*: any phrase actually deployed against you may become yours, per
  world policy. A badge can gate an offer without being consumed. A world that
  treats some technique as expendable is running a variant rule.
- **Prizes** — their own catalog of spendable, tradable tokens. Granted by
  *winning*. These participate in the trading and unlock shell through
  `tangl.mechanics.transaction`, whose design doc already enumerates Held Token
  and Catalog Provision source modes.

A phrase is one kind of badge-like token; a prize can be anything — a token from
another catalog, a variable flag, a newly minted concept. Modeling prizes as
spendable tokens with their own catalog is the simplest first cut and keeps the
transaction rails doing what they already do.

```text
lose → learn something
learned phrase → enables a better challenge
win → receive a unique prize
prize → unlock or trade for another opportunity
```

Grind losses, not wins.

### The reward policy is a hookable shell-level handler

Acquisition is **not** kernel behavior. It belongs to the plot/shell layer as an
ordinary dispatch-registered aftermath handler, and it is expected to change
without touching the contest flow.

The first implementation should be whatever is easiest — most likely "award the
phrase that beat you." What matters is that swapping the policy never reaches
into the kernel. Worlds should be able to express things well outside that
default:

- winning makes you *forget* something
- losing teaches only the winning retort
- losing teaches the winning retort plus every retort ranked below your best

Those are illustrations of the range, not proposals. Their only real requirement
is on the evidence: the round record has to be rich enough that a policy nobody
has written yet can still be computed from it. That is the practical argument
for the field set below — richer than the default policy needs, deliberately.

### Exposure is recorded, never inferred

The round record must identify what was actually presented:

- prompt phrase id
- response phrase id actually deployed
- whether it matched
- any explicitly revealed correct response
- initiative before and after

`RoundRecord.notes` carries this; JOURNAL renders it; the shell-level aftermath
handler applies progression idempotently, guarded the way
`apply_colony_victory_aftermath` guards with `caller.locals`.

Two things this rules out, both deliberately:

Two things this rules out, both deliberately:

- **Do not infer exposure from win/loss.** An outcome-keyed record cannot
  express red-paperclip acquisition at all, since the whole point is that losing
  teaches. This is a schema commitment, not an interface style — it survives the
  decision below to defer protocols.
- **Do not derive progression by rereading rendered journal prose.** An unspoken
  correct answer must not become learned merely because the engine knew it.
  Disclosure stays honest when acquisition reads structured evidence of what was
  actually said.

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

Extension is monotonic in both directions: a later expansion can add a response
effective against old calls without editing the old catalog.

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

1. Pure `CallResponseGame` with a fixed phrase set: role capability, directed
   matching, initiative, structured round notes, ordinary CLI journal output.
2. `PhraseType` / `PhraseBadge` / owner-bound `RepertoireManager`; a world
   PREREQS handler snapshots selected badge ids into the contest.
3. Shell-level aftermath handler reads exposure records and idempotently awards
   badges; the policy is swappable without touching steps 1-2.
4. Winning an opponent grants a prize token from its own catalog, or a durable
   world consequence.
5. Plot-level opponents and locations gate on repertoire and prize holdings.
6. Sword Master analogue: unfamiliar call text mapped to already-earned badges.
7. Richer expressions and presentation, only after the CLI vertical is complete.

Steps 1 and 2 are independently testable, which is the check that L1 and L2 are
really orthogonal.

---

## Open questions

1. **Contradiction resolution: rules or distance?** Declared ranks are the
   first cut. Whether contradictions are better resolved as closest/most-likely
   match — with the rules themselves acting as distance measures, in the shape of
   `offer_sort_key()` — is genuinely open and should be decided by a real catalog
   rather than in advance.
2. **Does an aftermath grant every witnessed phrase, or only the one that beat
   you?** A world policy, not a kernel decision. The first world should pick the
   cheapest thing that works.

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
