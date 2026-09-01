# Game Mechanics Design

```{storytangl-topic}
:topics: games
:facets: overview, design
:relation: defines
:related: credentials, progression, transaction, journal
```

**Status:** CURRENT REFERENCE + ACTIVE FAMILY EXPANSION  
**Scope:** the `tangl.mechanics.games` family, its Layer 3 VM integration, and the
future game shapes still worth preserving as design intent  
**Canonical runtime surface:** `Game`, `GameHandler`, `HasGame`, package handlers,
and `create_game_block()`

---

## Core Idea

Game mechanics in StoryTangl are best understood as **re-entrant interactive
blocks**.

A game block repeatedly re-enters a recognizable continuation point, provisions
move choices from current game state, resolves one round, emits journal output,
and only exits to the wider story frontier when a terminal condition is reached.

That is why the current design fits naturally inside the VM rather than beside
it:

- moves are generated as traversable choices
- round resolution is a normal UPDATE-phase concern
- round narration is a normal JOURNAL-phase concern
- victory/defeat/draw are ordinary predicate-friendly namespace facts

This note supersedes the older migration-era scratch notes. The core framework
is no longer speculative; what remains here is the stable model plus the future
family directions that still look worth keeping.

---

## Stable Runtime Contract

The current games package revolves around a small, stable contract:

- **`Game`** holds state, score/history, and lightweight serialization-friendly data
- **`GameHandler`** is the rule object that sets up a game, offers moves, receives
  moves, resolves rounds, and evaluates terminal state
- **optional handler hooks** like `get_move_label()`, `build_round_notes()`, and
  `get_journal_fragments(game, ctx=...)` let concrete games project richer
  choices and narration through the live phase namespace without bypassing the
  shared VM handlers
- **`HasGame`** is the author-facing facade that attaches a game to a story node
- **package handlers** connect games to VM PLANNING, UPDATE, JOURNAL, and
  CONTEXT phases
- **`create_game_block()`** is the ergonomic story-layer factory for the common
  "challenge block with outcome exits" pattern

This split is important:

- rule logic lives in handlers
- mutable round state lives in the game object
- narrative routing lives in the story/VM integration surface

That separation is what keeps games from turning into opaque one-off scripts.

---

## Rounds Versus Story Turns

The key modeling distinction is:

- **story turn**: one traversal step through the wider narrative graph
- **game round**: one cycle inside a game block

Many rounds may occur while the cursor remains on one recognizable story block.
The runtime therefore needs to track both story progression and local game
progression without confusing them.

The current implementation already uses this distinction in practice:

- traversal history and step/turn helpers belong to the VM
- game round state belongs to the game family
- round outcomes are projected back outward through journal and namespace hooks

---

## Phase Mapping

Games fit into the existing VM pipeline rather than introducing a second hidden
subsystem.

| VM phase | Game role |
|---|---|
| **PLANNING** | provision the next frontier without accepting or initializing a pending game |
| **PREREQS** | redirect/interrupt before content; a redirected game remains pending |
| **UPDATE** | on accepted pending entry, run world preparation then pure setup; receive a selected move and refresh dynamic projections |
| **JOURNAL** | emit round recap and score/status fragments |
| **CONTEXT** | expose `game_won`, `game_lost`, `game_draw`, round facts, and similar flags |
| **POSTREQS** | allow authored victory/defeat/draw exits to route onward |

This is the durable design insight from the longer scratch document: games do
not need a parallel engine. They are a specialized VM participant with one
highly legible re-entry shape.

---

## The Accessory-Complexity Ladder

The organizing question for this family is not "what genre is this game?" but:

> **What does the game use to represent advantage, and how much history must it
> keep to do so?**

Answering that yields a **ladder of accessory complexity**. Each rung adds
exactly one representational commitment, and each commitment exists because the
rung below it could not express something. The rungs are cumulative: a board
game still has counts, a card game still has strategy.

| Rung | Advantage is carried by | Accessory added | History the kernel must keep | Engine substrate |
|---|---|---|---|---|
| **strategy** | the move itself | none | none, or one opponent tell | move type + dominance relation |
| **token** | *how much* you hold | count (fungible) | scalar or multiset totals | `CountableAsset` + `AssetWallet` |
| **named token / card** | *which ones* you hold | identity (rank, suit, face-down) | ordered multiset, exhaustible source, private holdings | `Token[AssetType]` + `ComponentManager` |
| **board** | *where they are* | position | occupancy map; legality becomes topological | token `instance_var` position + a topology |
| **incremental** | *what they will produce* | time (rate, escalation) | monotone accumulation plus a cost curve | tokens/wallet + production spec + escalating cost |

The ladder is a better organizing tool than a flat genre list because it
explains membership rather than asserting it:

- **Aggregate-force contests sit between token and card.** `bag_rps` and
  `siege_rps` compose a commitment out of counts, but no individual unit has
  identity — which is exactly why casualty priority and "adaptive" joker units
  stayed unresolved design questions rather than implementation details.
- **Corridor is a card game with identity projected away.** `CorridorGame`
  draws from an ordered `source_sequence` of integers. Its shared-threshold
  pressure is card pressure; it simply declines to model which card. The
  deferred `MndCard` work in `CORRIDOR_CONTEST_DESIGN.md` is the decision to
  climb back up one rung.
- **Dual-meter pressure needs no tokens.** The scratch `complex_rps` sketch —
  competing "defiance" and "heat" meters filled at rates set by an RPS matchup —
  reads like a new kernel but is a corridor/two-heap contest over shared
  scalars. It is a strategy-rung variant with two thresholds, not a new rung and
  not a new mechanism.
- **Credentials is a picking loop over named tokens.** Per-document
  inspection, packet-level consistency, then disposition under changing
  context. See `CREDENTIALS_LOOP_DESIGN.md` and
  `docs/src/notes/CREDENTIALS_INTERACTION.md`.
- **Composite loops are not a rung.** An outer incremental shell with inner
  contest spikes is a *combination* of rungs, not a new one. See
  `COMPOSITE_GAME_LOOPS_DESIGN.md`.

### Fungibility Is the Load-Bearing Transition

The jump from **token** to **named token** is the only rung change that alters
which engine primitive a kernel should reach for, and the platform already
models exactly that split:

- fungible counts are `CountableAsset` definitions tracked in an `AssetWallet`
- discrete, identity-bearing items are `Token[AssetType]` graph nodes: a frozen
  singleton definition (`token_from`) plus mutable node-local state on fields
  marked `instance_var=True`
- `AssetTransactionManager` already covers both paths — `transfer_countable()`
  for wallet counts and `give_asset()` for discrete tokens
- `HasAssets` already holds both — a `wallet` and an `assets` map

Game tokens are therefore **an extension of the existing asset/token surface,
not a parallel type**. That is what buys instancing and the transaction
machinery for free, and it is what makes the upper rungs tractable: a chess
piece and a playing card both want a frozen definition (a knight moves like a
knight; the 7♠ is a seven of spades) with mutable per-instance state (this
knight is on e4 and has castled; this card is face-down in the discard).
Position at the board rung is an ordinary `instance_var`, not a new mechanism.

That pattern is already load-bearing in three places — `PhraseBadge` in
`repertoire.py`, `CredentialComponentToken`, and `VehicleComponentToken` — so
the upper rungs are not speculative. What remains is that the older kernels
predate it: `NimGame.heap_size` is a bare `int`, `AggregateForceGame` reserves
and `IncrementalGame` resources are bare `dict[str, int]`, and blackjack carries
a private `PlayingCard` model. Reconciling those is a second-consumer task, not
a prerequisite for the ladder.

### Orthogonal Axes

These vary independently of the rung and must not be confused with it:

- **Move verb** — commit-from-reserve, *select-from-field* (picking), or
  allocate-over-time. **Picking is a verb, not a rung.** That is why
  `PickingGame`, `KimGame`, and `CredentialsGame` operate at different rungs
  while sharing an inspect/reveal/decide shape.
- **Player relationship** — solo, competitive, cooperative, multiple. Every
  kernel today sits at two seats; see "Beyond Two Sides" for what the rest
  of that axis would require.
- **Information** — open, hidden, or telegraphed by an opponent tell.
- **State dependency** — whether cumulative history changes future legality
  (state-dependent) or each round stands alone (state-independent).

A kernel is specified by naming its rung plus a position on each axis. Most
"new game" requests turn out to be a new point in that space rather than a new
mechanism.

### Rungs as a Selection Surface

Making the ontology explicit and enumerable has a payoff beyond classification:
**game-type selection can itself become a story mechanic.**

The precedent is the Game in the *Blue Adept* / Apprentice Adept novels, cited
here for its mechanism rather than as a recommendation: a contest's form is
chosen from a grid of categories, with each side secretly picking one axis. A
physically weak but clever competitor then plays the *selection* step as hard as
the contest itself — steering away from physical challenges, and steering even
nominally random ones toward anything with a strategic component.

The ladder plus the orthogonal axes above *is* such a grid. A story that lets a
character negotiate, bluff about, or manipulate which kernel a confrontation
resolves through gets a genuine mechanic out of the taxonomy rather than a
filing scheme. That is speculative, but it is the strongest argument for keeping
the rungs enumerable and world-legible instead of implicit in each kernel.

### Ladder Audit of Current Kernels

| Kernel | Rung | Notes |
|---|---|---|
| `TrivialGame`, `RpsGame` / `RpslsGame` | strategy | dominance relation only |
| `CallResponseGame` + `repertoire` | strategy | actor-bound move sets over a `Token` catalog; see `REPERTOIRE_LOOP_DESIGN.md` |
| `NimGame` | token | one heap; multi-heap remains an open extension |
| `AggregateForceGame`, `BagRpsGame`, `SiegeRpsGame` | token → card boundary | composition without unit identity |
| `PickingGame`, `KimGame` | verb over token/named | picking axis, rung varies by host |
| `CredentialsGame` | named token | stacked picking composition |
| `BlackjackGame` | named token | honest rung; cards are private to the module rather than shared |
| `CorridorGame` | card, scalarized | identity deliberately projected away |
| `TrackGame` | board | cyclic index, assignable rolls, exact-landing finish, eviction, redirection squares; no-choice race boards are its degenerate configuration |
| `IncrementalGame` | incremental | geometric build-cost escalation (`BuildSpec.cost_growth`) and non-bankable `ephemeral_resources` give it the accelerate-then-wall pacing the rung requires; per-player discount/productivity/efficiency multipliers remain unbuilt |

One gap follows directly from the audit rather than from taste, and one rung
has just been filled.

#### The board rung, and why it is a race with choice

`TrackGame` fills this rung. Within it, board games split cleanly by whether the
player chooses anything — the move-verb axis reappearing at the position rung
rather than a new rung of its own:

- **Race boards without choice.** A single track, a random advance, and special
  spaces that jump position forward or back. Chutes and ladders is the type
  specimen, and its **redirection squares** — not its lack of choice — are the
  characteristic mechanic: bonus/malus spaces are indirection pointers on an
  index, landing on one displacing the token forward up a ladder or back down a
  chute. No canonical layout is baked in; historical and commercial boards
  disagree, so the map is authored world data rather than engine truth.
  Because the player never chooses, the whole game is **deterministic given the
  roll sequence** — the same property blackjack has once the dealer follows a
  fixed house policy. That makes these useful as topology and presentation
  proofs, but they are replays rather than contests, and a kernel should be
  honest about that rather than dressing a forced sequence as a decision.
- **Race boards with choice.** The minimal interesting form keeps the track but
  adds a second axis of state: a **cyclic index**, several tokens per player in
  play at once, and a roll the player **assigns to any one of their own tokens**.
  Two further rules supply nearly all the tension:
  - a token only finishes by landing **exactly** on the final index, so
    overshooting wastes the move
  - if a token lands where another already sits, the **earlier occupant is
    evicted** back to the pile

  Choosing which token to advance — press a leader, rescue a straggler, or take
  a capture — is real strategy over pure position, with no counts, identity, or
  economy involved.

`TrackGame` implements the second form, and the first falls out of it: set
`tokens_per_side=1` and every round offers exactly one move, at which point the
race is fully determined by its roll sequence. Redirection squares are a
separate, orthogonal `redirects` map, so they are available to contested races
too — a chute is considerably more interesting when a rival is waiting to take
the square you were flung off of. That degeneracy is pinned by test
rather than asserted here. A richer target such as elefant hunt can now build on
the kernel instead of inventing one.

#### The incremental rung's upgrade and prestige layers are still flat

Escalation and spoilage have landed, but the two layers that carry the genre's
actual decisions have not:

- **Upgrades.** The scratch spike's per-player discount, productivity, and
  efficiency multipliers — the purchases that bend the escalating cost curve
  back down.
- **Prestige.** Reset-with-carryover loops, where a run is deliberately
  abandoned in exchange for a persistent multiplier on the next one.

Both are still on the table. Their interest is not the arithmetic but the
recurring decision they create: **spend to advance now, or spend to advance
faster later.** An incremental kernel without that tension is a waiting
simulator; with it, every cycle poses the same legible question at a different
scale. Prestige is the same question with the run itself as the stake.

Two reference points bound the design space:

- **Realm Grinder** shows how far nested prestige loops can be pushed — and the
  failure mode, since the interesting decisions become effectively unplayable
  without external documentation open alongside the game. Depth is cheap;
  legibility is not.
- **A Dark Room** shows the more attractive shape for this engine: the rule
  surface itself expands as the player progresses, and interaction is richer
  than advancing one counter — *click this token to upgrade that token so that
  clicking that token advances faster*. That indirection between what you act on
  and what improves is what distinguishes an incremental **game** from a clicker.

The legibility problem is the one StoryTangl is unusually well placed to
address: journal and namespace projection can narrate a curve and its upgrades
in prose instead of hiding them behind unexplained numbers. Any upgrade or
prestige work should treat that as a requirement, not a garnish. Both layers
still want a named consumer before implementation.

---

## The Opponent Seam and Authored Outcomes

Every kernel in this family asks for an opponent move through one narrow seam
and does not care where the answer comes from. `GameHandler` pre-selects a move
via `opponent_strategy` before the player commits, and may overwrite it via
`opponent_revision_strategy` once the player has chosen.

Because the seam only asks for a move, the source is free: a policy from the
strategy bank, an optimal or deliberately incompetent play, a forced outcome, a
strategy bank owned by some other node, or eventually another cursor on the
graph playing the other side. None of that is visible to the kernel.

The two phases exist for narrative reasons, and are worth naming as such:

- **Pre-selection is a tell.** Because the opponent's intended move is known
  before the player acts, a world can telegraph it — *"they will jump you if
  they can"* versus *"he looks like he has no idea what he is doing"* — turning
  the opponent's competence into readable characterization.
- **Revision is a ret-con.** After the player commits, the opponent's move (and,
  where a kernel allows it, the roll behind it) may be rewritten so the round
  lands where the story needs it: *"you thought you were playing defensively,
  but they rolled exactly what they needed"* versus *"instead of winning, he put
  a token right where you can take it."*

### Verisimilitude, Not Veracity

It is tempting to read revision as cheating grafted onto an honest simulation.
That gets the priority backwards.

**Fairness is a side effect of applying a default ruleset consistently — it is
not the purpose of having rules.** The ruleset exists to launder tension,
failure, and reward through mechanics the player finds plausible. What the
player needs is the *feeling* of a fair contest and a consequence they can trace
back to legible causes. A game under no narrative pressure happens to play fair,
but that is incidental rather than the objective.

So the product is **verisimilitude, not veracity**. Authored bias is ordinary
storytelling, and the design consequence is only that it should be *explicit*:
biases live in named, registered strategies rather than buried in kernel
internals, so a world's thumb on the scale stays legible to its author and
reviewable in tests. `BlackjackGame.deal_bias` and the track kernel's
`track_force_capture` are the same idea at different rungs.

This is also why the family keeps rule logic in handlers and mutable state in
game objects. A kernel whose outcomes can be steered from outside only stays
trustworthy if the steering happens at declared seams.

### Tension as a Computable Property

Authored bias does not have to be tuned by feel. Where a configuration removes
player choice, the path is fully determined by the random draws, the kernel
becomes an ordinary Markov chain, and the dramatic shape it produces can be
solved for rather than guessed at.

The no-choice track race is the clean case, and `track_analysis.py` does exactly
this: it solves `E[p] = 1 + mean(E[next(p, roll)])` over board positions to get
expected rolls to finish, compares that against the same board stripped of its
redirects, and reports a cumulative finish distribution whose tail exposes a
punishing endgame. Published analyses of commercial chute-and-ladder boards
supply useful starting heuristics — roughly balanced ladder and chute counts,
modifiers on about a fifth of squares, long ladders early and long chutes late —
though those are one publisher's engineering choices rather than laws, so
nothing enforces them.

What matters for this family is the general move: **a layout is a distribution
over story shapes, and the distribution is measurable.** The analysis names the
shapes it finds — a bare `footrace`, a `balanced` board, a `chaotic` one, and
the *heartbreak board* whose long late chutes fling leaders back and stretch the
tail until the race may never end. Naming them lets a world ask for a dramatic
shape and check that it got one.

Two limits are worth stating. The analysis models a single token racing alone;
eviction and roll assignment make a contested race non-Markovian in that state
space, so the tool tunes a layout rather than scoring live play. And a
measurable tension curve is still not a fair one — it is the same authored thumb
on the scale as a revision strategy, merely legible enough to aim.

---

## Beyond Two Sides

Every kernel in this family currently assumes exactly two seats. That is a real
limit rather than an incidental one, and it is worth naming precisely, because
the folk games these kernels descend from are mostly *parlor* games for four to
six players. The cyclic-track race is the clearest case: its commercial and
homemade ancestors seat six around a wheel, and much of what makes them worth
playing only exists above two.

### What breaks structurally

These are engine facts, not design opinions:

- `Game.score` is a two-key dict of `player` and `opponent`
- `RoundResult` and `GameResult` are first-person binary — there is no
  vocabulary for *placement*, for "someone else won", or for still being in a
  race that another seat has already left
- the opponent seam is **singular**: one `opponent_strategy`, one
  `opponent_revision_strategy`, one `opponent_next_move`. N seats need that
  seam indexed by seat
- turn order is implicit in the shape of a two-party round rather than explicit
  state that a kernel advances and a journal can narrate

None of that requires a new rung or a second pipeline. It is a widening of the
existing contract, and it touches every kernel — credentials, repertoire, and
the aggregate-force family are binary for the same reason the track race is.

### What changes dynamically

The more interesting half is that adding seats is not just arithmetic; it
changes what the game *is*:

- **Placement versus elimination.** Is finishing second of six a win, a loss, or
  a rank? The binary result vocabulary cannot currently say.
- **Kingmaking.** A seat that can no longer win can still decide who does. That
  is a genuine strategic act with no representation in a two-party scoring model.
- **Leader targeting.** Tables spontaneously gang up on whoever is ahead —
  producing socially what the *heartbreak board* produces structurally. Two
  routes to the same rubber-banding, and a world can choose which does the work.
- **Negotiated termination.** Long multiplayer races generate their own exit
  pressure: the table litigating an early end to a contest nobody can finish.
  A social stop condition of that kind has no current shape, and it is arguably
  the most narratively interesting item in this list.
- **Seat order.** Going first is an advantage that has to be balanced or
  narrated once there are more than two seats.

### Why it matters here

Pluralizing the opponent seam is where this family meets the rest of the
platform. Once seats are indexed rather than assumed, each seat may
independently be a registered policy, an authored character with its own
strategy bank, or a live cursor on the graph — and the kernel still only asks
each one for a move. That is the same question multi-lane execution asks (see
issue #346 and the `multi_lane` devref topic), approached from the mechanics
side instead of the traversal side.

### Seats as Characters

The reason to index seats is not mainly to support more players. It is that a
seat bound to a persistent character turns **strategy into a characterization
surface**, and a recurring opponent who reliably plays a certain way is more
legible than any amount of description.

Consider a recurring salon or parlor setting where a player alternates between
scripted scenes, random events, and community games, with standing and
relationships carried between them. The same faces return to different tables.
What makes them recognizable is not appearance but policy:

- the fatalist who reads a long game as unwinnable and starts hunting for
  someone to hand the win to, just to end it — kingmaking as temperament
- the nemesis who spends moves knocking a particular seat back even at cost to
  their own position
- the admirer who declines an available capture against you, or who plays to be
  seen supporting you and wants the support returned
- the one who always presses their leader and never rescues a straggler

That is sharper differentiation than a cosmetic trait, because the player infers
it from consequences they felt rather than from a description they read.

Three design consequences follow:

- **A strategy bank is character-owned, not game-owned.** It should attach to a
  persistent actor the way `RepertoireManager` attaches earned phrases to an
  owner, rather than being configuration on a game instance that happens to be
  running.
- **Dispositions must sit above any one kernel's move type.** For the same
  character to feel like themselves across a track race, a card game, and a
  credential check, the durable thing cannot be "assign the roll to token 2". It
  has to be a bias — *target the leader*, *seek an early end*, *protect this
  person*, *avoid risk* — that each kernel interprets in its own move
  vocabulary. Kernel-specific strategy functions then become the local
  translation of a portable disposition.
- **Suboptimal play is a feature.** `track_hapless` is already the argmin of the
  same scorer that drives `track_optimal`; incompetence, spite, and generosity
  are all just differently-weighted objectives over the same candidate set.

The pre-selection tell is what makes any of this readable. Because a seat's
intended move is known before the player commits, the narration can telegraph
disposition — and being able to anticipate someone is precisely the experience
of knowing them.

This is aspirational and awaits a consumer. It is recorded here because it is
the strongest argument for pluralizing the opponent seam properly rather than
bolting a second player onto one kernel.

### Scope

Treat this as a named gap awaiting a consumer rather than a commitment. But when
a consumer arrives, it should widen the shared contract once for the whole
family instead of growing a private N-player path inside one kernel.

---

## What Is Implemented Today

The current package already proves the family shape:

- simple competitive games are real, not hypothetical
- solo card pressure works through blackjack
- token depletion works through nim
- light picking and inspection loops work through Kim's Game and credentials
- positional contests work through the cyclic-track race
- self-loop move provisioning works in the VM
- journaling and predicate exposure work end to end
- dynamic game actions are rebuilt after their relevant UPDATE mutation rather
  than accumulating; stable authored actions remain ordinary gated edges
- outcome exits route cleanly through authored story blocks

Concrete reference members now include:

- **RPS / RPSLS** for simple competitive rounds
- **Blackjack** for hidden information, author-biased dealing, and house-policy play
- **Nim** for shrinking shared state and state-dependent legal move generation
- **Kim's Game** for inspect/reveal/guess picking loops
- **Credentials** for inspect/reveal/disposition loops that can later host richer
  nested structures
- **Track** for cyclic-position races with assignable rolls, exact-landing
  finishes, eviction, and chute/ladder redirection squares

The authored `rps_tavern` and `blackjack_parlour` bundles keep the family tied to
real story traversal rather than isolated core tests.

---

## Future Shapes Still Worth Preserving

The longer design note contained several future directions that still seem
valuable, even though they are not commitments:

- **larger token games** such as marker-exchange contests beyond one-heap Nim
- **richer picking/verification games** such as multi-stage credential checks
- **larger card games** with fuller deck, discard, or betting structures
- **richer board topologies** beyond one cyclic track — branching routes, safe
  squares, or multiple linked tracks — now that `TrackGame` establishes position
  as ordinary token state, with elefant hunt as the target consumer
- **incremental upgrades and prestige** — cost-bending multipliers and
  reset-with-carryover loops layered over the landed escalation curve, whose
  point is the recurring advance-now-or-advance-faster-later decision
- **aggregate-force or winding-RPS battles** where the interesting part is the
  composition of a hand or force rather than one atomic throw

That last category is worth being explicit about. The scratch `bag_rps` idea was:

- each player has a bag of assorted R/P/S tokens
- a move commits both a dominant flavor and an amount of force
- mixed forces can cancel into ties in ways that one-token RPS cannot

Examples from that pattern:

- two `rock` can tie one `paper`
- `paper + scissors` can tie one `rock`
- `paper + scissors` can still lose to two `rock`

That is a meaningful family lift: classic RPS becomes a token-allocation and
composition contest rather than a single-symbol comparison.

The same family also admits an **asymmetric challenge-response** form, sketched
in scratch `siege_rps`:

- an attacker declares posture and force
- a defender must meet or beat that commitment with a combination from reserve
- matching can preserve initiative for the attacker
- beating can flip initiative to the defender
- the real objective is reserve depletion and positional exhaustion over time

That gives the aggregate-force family at least two distinct archetypes:

- **simultaneous pooled comparison** such as `bag_rps`
- **asymmetric pressure ladder** such as `siege_rps`

Useful balance knobs in that second form include reserve depth, reserve width,
initiative advantage, reinforcement cost, and posture-dependent payout.

A third archetype sits alongside those two: a **call-response dominance** form,
where each side deploys a phrase from its own accumulated repertoire and a
catalog-declared directed relation decides whether the response answers the
call. It takes directed dominance from `RpsGame` and asymmetric initiative from
`SiegeRpsGame`, but differs from both in that the move set is actor-bound rather
than universal, roles are initiative-sensitive, and the dominance graph is an
extensible many-to-many catalog relation rather than a fixed cycle. Its pressure
comes from an orthogonal acquisition shell rather than from the grammar itself.
See `REPERTOIRE_LOOP_DESIGN.md`.

These are worth keeping because they stress different aspects of the family:

- richer runtime state
- more complex move generation
- stronger crossover with progression, assets, and provisioning
- more elaborate journal projection

None of them require changing the core contract first. They mostly require
implementing new kernels and handlers against the existing family surface.

---

## Integration With Other Mechanic Families

Games are not an island. The most promising crossover points are:

- **progression**: stats, situational modifiers, and task-style resolution can
  affect move outcomes or difficulty
- **assembly / assets**: equipment, decks, or token pools can become game setup inputs
- **presence / media**: opponent tells, revealed cards, or board state can project
  into prose or media surfaces

The important design constraint is that these remain explicit integrations.
Game handlers should ask for the inputs they need; they should not quietly
smuggle writeback or progression logic into opaque side effects.

This matters even more for composite shell-and-spike loops. Those should be
built as explicit combinations of simpler kernels rather than as monolithic
special cases.

---

## Non-Goals

This design does not imply:

- a separate mini-engine outside the VM
- a mandatory deep subtype hierarchy for every game shape
- hidden continuous simulation
- real-time or twitch mechanics support
- multiplayer support as a prerequisite for expanding the family (it remains a
  named gap rather than a blocker; see "Beyond Two Sides")

Those may become relevant later, but they are not needed to justify the current
family architecture.

---

## Review Questions

When extending `tangl.mechanics.games`, the best review questions are:

1. Does the new game keep rule logic in the handler and state in the game object?
2. Does it fit the re-entrant block model cleanly?
3. Does it expose player-facing consequences through journal and namespace rather
   than private internals?
4. Does it compose explicitly with progression, assets, or provisioning instead
   of bypassing those systems?
5. Is the new shape genuinely a new family member, or is it just a one-off world script?

If those answers stay clear, the family can grow without losing the elegance of
the current reference implementation.
