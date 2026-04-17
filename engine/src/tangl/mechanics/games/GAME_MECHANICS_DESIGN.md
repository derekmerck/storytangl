# Game Mechanics Design

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
  `get_journal_fragments()` let concrete games project richer choices and narration
  without bypassing the shared VM handlers
- **`HasGame`** is the author-facing facade that attaches a game to a story node
- **package handlers** connect games to VM PREREQS, PLANNING, UPDATE, JOURNAL,
  and CONTEXT phases
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
| **PREREQS** | one-time setup on first entry when needed |
| **PLANNING** | provision currently available move choices |
| **UPDATE** | receive the chosen move and resolve one round |
| **JOURNAL** | emit round recap and score/status fragments |
| **CONTEXT** | expose `game_won`, `game_lost`, `game_draw`, round facts, and similar flags |
| **POSTREQS** | allow authored victory/defeat/draw exits to route onward |

This is the durable design insight from the longer scratch document: games do
not need a parallel engine. They are a specialized VM participant with one
highly legible re-entry shape.

---

## Taxonomy Worth Keeping

The useful taxonomy from the apocryphal design doc is still worth preserving,
even though only part of it is implemented today.

### Player Relationship

- **solo**: player versus environment or house
- **competitive**: player versus opponent
- **cooperative**: players together versus environment
- **multiple**: more than two participants or mixed incentives

### State Model

- **simple**: no persistent equipment or field state
- **token**: fungible markers or counts
- **picking**: targets versus distractors or validation patterns
- **card**: ordered unique markers with rank/suit-like semantics
- **board**: positional token state
- **incremental**: resource evolution over repeated rounds

### State Dependency

- **state-independent** rounds such as classic RPS
- **state-dependent** games where cumulative history matters

This taxonomy is more useful than a deep inheritance tree. It gives the family
a vocabulary for future expansion without forcing premature abstraction.

It is also meant to be **compositional**. The goal is not to produce an
exhaustive list of named genres, but to identify a small number of reusable
interaction kernels and then describe more complex games as lifts, variants, or
combinations of those kernels.

In spirit, this follows the same intuition as some game-theoretic and
computational taxonomies: richer interactions are often easier to reason about
when reduced to combinations of simpler forms rather than treated as wholly new
species.

One additional family note is worth calling out explicitly: the old scratch
`twentytwo` spike pointed toward a **shared-threshold corridor contest** that
lifts blackjack-like push-your-luck into a contested ordered-token form. See
`CORRIDOR_CONTEST_DESIGN.md` for that progression and why it probably wants a
generic corridor kernel before any fully multi-axis implementation.

The same scratch tree also contained an important lift in the other direction:
`bag_rps` treated classic RPS as an **aggregate-force token contest** where each
player chose both *what kind* of force to commit and *how much* of it to commit
from a reserve. That is a useful reference for the jump from atomic move games
to mixed-composition contests.

And at the next tier up, some authored systems are not one kernel at all but
explicit **composite loops**: an outer incremental or strategic shell with
inner contest spikes whose outcomes feed back into progression. See
`COMPOSITE_GAME_LOOPS_DESIGN.md` for that family shape.

Credentials deserves special mention here. It is best understood as a **stacked
picking-game composition**: per-document inspection, packet-level consistency
checking, then final disposition under changing context. See
`CREDENTIALS_LOOP_DESIGN.md` for the live-facing summary and
`docs/src/notes/CREDENTIALS_INTERACTION.md` for the longer background note.

---

## What Is Implemented Today

The current package already proves the family shape:

- simple competitive games are real, not hypothetical
- solo card pressure works through blackjack
- token depletion works through nim
- light picking and inspection loops work through Kim's Game and credentials
- self-loop move provisioning works in the VM
- journaling and predicate exposure work end to end
- dynamic game actions are rebuilt per planning pass rather than accumulating
- outcome exits route cleanly through authored story blocks

Concrete reference members now include:

- **RPS / RPSLS** for simple competitive rounds
- **Blackjack** for hidden information, author-biased dealing, and house-policy play
- **Nim** for shrinking shared state and state-dependent legal move generation
- **Kim's Game** for inspect/reveal/guess picking loops
- **Credentials** for inspect/reveal/disposition loops that can later host richer
  nested structures

The authored `rps_tavern` and `blackjack_parlour` bundles keep the family tied to
real story traversal rather than isolated core tests.

---

## Future Shapes Still Worth Preserving

The longer design note contained several future directions that still seem
valuable, even though they are not commitments:

- **larger token games** such as marker-exchange contests beyond one-heap Nim
- **richer picking/verification games** such as multi-stage credential checks
- **larger card games** with fuller deck, discard, or betting structures
- **incremental games** where generators or resources evolve over rounds
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
- multiplayer support as a prerequisite for expanding the family

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
