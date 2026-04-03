# Corridor Contest Design

**Status:** DRAFT FAMILY NOTE  
**Scope:** a generalized "22" / shared-threshold contest pattern for
`tangl.mechanics.games`  
**Motivating scratch references:** `scratch/mechanics/games/card_games/twentytwo.py`,
`scratch/mechanics/games/card_games/twentytwo_game.py`, and the older
subpackage ontology under `scratch/mechanics/games`

---

## Why This Note Exists

The scratch `twentytwo` spike points at a useful family shape that is larger
than blackjack but smaller than a full board or tactics game.

The core idea is not "21 with another number." It is a **shared-threshold
contest**:

- each participant has one or more personal scores
- there is one public target, ceiling, or corridor boundary
- players alternate moves that shift their own position, the opponent's
  position, or both
- victory comes from creating a favorable bracket relation before overextending

This is interesting because it sits exactly where the original game taxonomy
was trying to go: lift a simple ordered-token solitaire pattern into a contested
and then multi-dimensional form.

---

## Taxonomy Placement

The older scratch tree already implied a progression by increasing structural
complexity rather than by arbitrary genre labels:

- **simple games**: only moves and maybe shallow history, such as RPS
- **token games**: fungible counts and shrinking or growing reserves, such as Nim
- **board games**: tokens plus positional field state
- **card games**: ordered, non-fungible draws with hidden and revealed state
- **perception / picking games**: target versus distractor identification
- **incremental games**: longer-running resource evolution

The other important axes were orthogonal:

- **solo / solitaire** versus **contest**
- **memory only** versus richer **state**
- **fungible tokens** versus **named tokens** versus **ordered tokens**

Seen through that lens:

- `RPS` is a simple contest with move history and almost no field state
- `Nim` is a contested fungible-token game
- `bag_rps` is a contested aggregate-force token game where composition and
  amount both matter
- `Blackjack` is a solitaire ordered-token game with hidden state
- `TwentyTwo` is best understood as a **contested ordered-token corridor game**

That makes it a natural "next lift" after blackjack rather than an odd side
branch.

---

## Core Pattern

The family shape can be described without mentioning cards at all.

### Shared Threshold

There is a public value, or small set of public values, that defines the
pressure boundary for the contest.

Examples:

- a single target score
- a safe upper bound
- a lower and upper corridor
- one threshold per named influence track

### Personal Position

Each participant holds one or more personal scores relative to that boundary.

Examples:

- one scalar score each
- two named tracks such as `traction` and `exposure`
- several influence tracks sharing one public tolerance ceiling

### Alternating Pressure

Moves are taken in alternating rounds, and each move changes the geometry of the
contest:

- advance yourself toward the threshold
- force the opponent upward
- widen or narrow the remaining safe corridor
- lock in a stance such as `stand`, `press`, `hedge`, or `force reveal`

### Bracket / Pinch Outcome

The distinctive outcome is not merely "reach N first."

The interesting result is that one player places the opponent into a bad band
between a personal score and a public threshold, or otherwise leaves the
opponent with only losing continuations.

That is the design insight worth preserving from `22`.

---

## Relationship To Existing Kernels

This family can be understood as a composition of ideas already present in the
live package.

### From Blackjack

- ordered draws
- hidden and revealed state
- push-your-luck decisions like `hit` and `stand`
- deterministic house or opponent policy after commitment

### From Nim

- shrinking safe space
- state-dependent legal moves
- forced-win or forced-loss lines
- pressure created by the geometry of remaining moves

### From Aggregate-Force RPS

- choosing both *what kind* of force to commit and *how much* to commit
- mixed compositions that resolve differently from one-token atomic throws
- reserves that matter because overcommitting now weakens later rounds

The old `bag_rps` spike is the clearest example here: RPS stops being a single
symbol reveal and becomes a contest of pooled type and magnitude.

### From Picking / Verification

- a narrated emphasis on pressure rather than fairness
- projection of only the clues the player is supposed to see
- author control over visibility, affordances, and bias

So design-wise, corridor contests are not a foreign mechanic. They are a
multi-axis pressure kernel assembled from existing simpler families.

---

## Why `TwentyTwo` Was Hard To Finish In Scratch

The scratch implementation bundled together several independent ideas at once:

- blackjack-style draw/stand pacing
- a contested opponent rather than a house policy
- vector-valued cards
- scalar win and loss thresholds applied to vector scores
- public and private pressure semantics

That made it hard for the implementation to say what the game actually *was*.

The spike still shows the right instinct, but it over-lifts too early:

- `MndCard` models vector cards before the scalar corridor rules are nailed down
- some resolution paths collapse vector state back to `max(score)`
- the narrative goal is bracket pressure, but the code still mostly behaves like
  a generalized blackjack scorer

The lesson is not "drop the idea." The lesson is "separate the lifts."

---

## Recommended Live Implementation Path

### Step 1: Scalar Corridor Contest

First implement the simplest non-solitaire form:

- one shared target
- one scalar score per side
- alternating turns
- moves like `advance`, `press`, `hold`, or card-driven `hit` / `stand`
- deterministic opponent policy, or a small strategy registry

This proves the bracket geometry cleanly and keeps the journal legible.

### Step 2: Ordered-Token Skin

Then add cards or another ordered token source on top:

- deck order matters
- reveals can be partial
- authored bias can shape draw order
- player affordances can be framed as card pulls, bids, gambits, or social moves

This is where a real `TwentyTwoGame` name can make sense as a concrete skin.

### Step 3: Multi-Track Extension

Only after the scalar version feels readable should the family lift into
multiple named axes:

- multiple personal tracks
- one shared threshold or one corridor per track
- moves that affect more than one track at once
- authored rules that temporarily weight or lock tracks

At that stage the mechanic stops being "blackjack with vectors" and becomes a
general pressure-allocation contest.

---

## Recommended Runtime Shape

If the live package implements this family, it should probably use a concrete
generic kernel such as `CorridorGame`, `BracketGame`, or `PressureTrackGame`,
with `TwentyTwoGame` as a themed specialization rather than the abstract base.

Useful state fields for a first pass:

- `shared_target`
- `player_score`
- `opponent_score`
- `player_stood`
- `opponent_stood` or `opponent_policy`
- `move_source` or `card_deck`
- `visible_state`
- `round_detail`

Useful namespace projections:

- current scores
- remaining safe margin to target
- whether either side is committed
- whether the opponent is currently bracketed
- visible next-pressure hints when the author wants "tells"

Useful journal material:

- how the corridor narrowed or widened
- whether a move was cautious, aggressive, or desperate
- whether the player just trapped themselves or the opponent

---

## Narrative Usefulness

This family is especially promising for StoryTangl because it maps naturally to
scenes that are not literally card tables.

Examples:

- mutual political leverage under a public tolerance limit
- interrogation pressure where each probe raises both certainty and danger
- courtship, negotiation, or bluffing scenes with mutual exposure
- ritual or magical calibration where both sides edge toward a visible threshold
- social influence contests where named tracks stand in for favor, suspicion,
  momentum, or attention

The important property is that the player can feel the corridor tightening even
when the system is authored to favor a particular dramatic arc.

---

## Design Constraints For The Live Package

When this family is implemented for real:

1. Start scalar and readable; do not begin with vector cards.
2. Keep the kernel generic and let `TwentyTwo` be a skin or reference game.
3. Treat cards as one possible move source, not the family definition.
4. Project the corridor state aggressively through namespace and journal so the
   player understands the pressure geometry.
5. Keep author bias explicit in state, deck order, or opponent policy rather
   than in hidden exception logic.

If those constraints hold, corridor contests can become the next meaningful
complexity tier after `blackjack` and `nim`.
